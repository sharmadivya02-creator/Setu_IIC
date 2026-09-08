import io
import json
import logging
import re
from typing import Any

import httpx
from fastapi import HTTPException
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

# Only include models verified to exist on this Groq account
SUPPORTED_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "groq/compound",
]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract clean text from PDF bytes with edge case checks for scans and corruption."""
    if not file_bytes or len(file_bytes) < 10:
        raise HTTPException(400, "Uploaded PDF file is empty or corrupted.")

    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            raise HTTPException(400, "PDF file is password-protected. Please upload an unlocked PDF.")

        text_pages: list[str] = []
        for index, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_pages.append(page_text.strip())

        full_text = "\n\n".join(text_pages).strip()
    except PdfReadError as error:
        logger.warning(f"PdfReadError: {error}")
        raise HTTPException(400, "Unable to parse PDF file. The file appears to be corrupted or invalid.")
    except Exception as error:
        logger.error(f"Unexpected PDF parse error: {error}")
        raise HTTPException(400, f"Error reading PDF: {error}")

    if len(full_text) < 40:
        raise HTTPException(
            400,
            "Could not extract selectable text from this PDF. Please ensure your PDF has selectable text and is not an image scan.",
        )

    # Cap text length to prevent context overflow while keeping full 1-3 page resume content
    return full_text[:12000]


def extract_json_from_text(raw_text: str) -> dict[str, Any]:
    """Extract and parse JSON from raw LLM output, handling markdown code blocks and preamble text."""
    text = raw_text.strip()

    # 1. Direct JSON parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. Extract from ```json ... ``` code fence
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except Exception:
            pass

    # 3. Find outermost { and }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start : end + 1].strip()
        try:
            return json.loads(candidate)
        except Exception:
            pass

    raise ValueError(f"Could not parse valid JSON from AI response: {text[:200]}")


async def extract_skills_with_groq(resume_text: str, taxonomy_skills: list[dict[str, Any]]) -> dict[str, Any]:
    """Call Groq API with JSON schema enforcement and fallback recovery to parse skills mapped to Setu taxonomy."""
    if not GROQ_API_KEY:
        raise HTTPException(
            500,
            "GROQ_API_KEY is not configured on the server. Please check backend environment settings.",
        )

    # Provide taxonomy summary to the LLM (ID, Name, Category)
    skills_context = json.dumps(
        [{"id": s["id"], "name": s["name"], "category": s["category"]} for s in taxonomy_skills],
        separators=(",", ":"),
    )

    system_prompt = (
        "You are an expert technical recruiter and resume analyzer for Setu.\n"
        "Your task: Read the candidate's resume and identify which of the allowed taxonomy skills they possess.\n\n"
        "CRITICAL RULES:\n"
        "1. ONLY select skills that exist in the PROVIDED TAXONOMY list. Do NOT invent new skills.\n"
        "2. Rate each skill on a 1-5 scale based on real project depth or work experience:\n"
        "   - 1: Aware (basic mention, coursework)\n"
        "   - 2: Beginner (academic or hobby project)\n"
        "   - 3: Working (production app, full stack, internship, core strength)\n"
        "   - 4: Proficient (advanced architecture, distributed systems, deep expertise)\n"
        "   - 5: Expert (lead level, extensive production experience)\n"
        "3. Provide a brief 4-8 word evidence snippet from the resume for each detected skill.\n"
        "4. Output MUST be valid JSON with exactly two top-level keys: 'summary' (1-sentence candidate overview) and 'skills' (array of objects with 'skill_id', 'suggested_level', 'evidence').\n"
        "5. Output only JSON without markdown fences."
    )

    user_prompt = (
        f"TAXONOMY SKILLS:\n{skills_context}\n\n"
        f"CANDIDATE RESUME TEXT:\n{resume_text}\n\n"
        "Extract the skills and return JSON in format:\n"
        "{\n"
        '  "summary": "1-sentence profile synopsis",\n'
        '  "skills": [\n'
        '    {"skill_id": 12, "suggested_level": 3, "evidence": "Built REST API with FastAPI"}\n'
        "  ]\n"
        "}"
    )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # Order models prioritizing fast, reliable instruction-following models
    models_to_try: list[str] = []
    preferred_order = ["qwen/qwen3.8-27b", GROQ_MODEL, "openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound"]
    for m in preferred_order:
        if m in SUPPORTED_MODELS and m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for model_name in models_to_try:
        # First attempt: with json_object response format; if json_validate_failed, retry without it
        for use_json_mode in [True, False]:
            try:
                body: dict[str, Any] = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                }
                if use_json_mode:
                    body["response_format"] = {"type": "json_object"}

                async with httpx.AsyncClient(timeout=25.0) as client:
                    response = await client.post(GROQ_ENDPOINT, headers=headers, json=body)

                if response.status_code == 200:
                    payload = response.json()
                    content = payload["choices"][0]["message"]["content"]
                    parsed = extract_json_from_text(content)
                    return parsed
                elif response.status_code == 400 and "json_validate_failed" in response.text and use_json_mode:
                    # Groq's JSON validator aborted; retry this same model without strict response_format
                    logger.warning(f"Groq json_validate_failed on {model_name}, retrying without response_format...")
                    continue
                else:
                    last_error = f"Groq API error ({model_name}): {response.status_code} - {response.text}"
                    logger.warning(last_error)
                    break
            except Exception as error:
                last_error = f"Groq request error ({model_name}): {error}"
                logger.warning(last_error)
                break

    raise HTTPException(502, f"AI extraction service unavailable: {last_error}")
