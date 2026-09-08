import { useRef } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { useAuth, homeFor } from "../auth";

function Hero({ progress, reduced }) {
  const y = useTransform(progress, [0, 1], ["0%", reduced ? "0%" : "-18%"]);
  const scale = useTransform(progress, [0, 1], [1, reduced ? 1 : 0.92]);
  const opacity = useTransform(progress, [0, 0.7, 1], [1, 1, 0]);
  const mascotX = useTransform(progress, [0, 1], ["0%", reduced ? "0%" : "12%"]);
  const mascotRotate = useTransform(progress, [0, 1], [-4, reduced ? -4 : 6]);

  return (
    <motion.section style={{ opacity }} className="sticky top-0 flex h-screen items-center overflow-hidden bg-periwinkle text-cream">
      <div className="absolute -left-24 -top-24 h-96 w-96 rounded-full bg-violet/50 blur-3xl" />
      <div className="absolute -bottom-32 right-10 h-[28rem] w-[28rem] rounded-full bg-petal/40 blur-3xl" />
      <div className="relative mx-auto grid w-full max-w-7xl grid-cols-1 items-center gap-6 px-6 md:grid-cols-[1.2fr_1fr]">
        <motion.div style={{ y, scale }} className="will-change-transform">
          <div className="label text-cream/80">a bridge between classroom and market</div>
          <h1 className="font-display text-[22vw] leading-[0.85] md:text-[13rem]">Setu</h1>
          <p className="mt-4 max-w-md text-lg text-cream/90">
            Students see which skills the market pays for. Faculty see who is placement-ready. Companies find the students who actually match.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/login" className="btn bg-cream text-plum hover:bg-petal">
              Sign in
            </Link>
            <Link to="/register" className="btn border border-cream/60 text-cream hover:bg-cream/10">
              Create an account
            </Link>
          </div>
        </motion.div>
        <motion.img
          src="/mascot.webp"
          alt="Setu mascot, a cheerful student with arms in the air"
          style={{ x: mascotX, rotate: mascotRotate }}
          className="mx-auto h-[45vh] w-auto drop-shadow-2xl will-change-transform md:h-[78vh]"
          fetchpriority="high"
        />
      </div>
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 font-mono text-xs text-cream/70">scroll</div>
    </motion.section>
  );
}

function Intro({ progress, reduced }) {
  const scale = useTransform(progress, [0, 0.45, 1], [reduced ? 1 : 0.86, 1, 1]);
  const opacity = useTransform(progress, [0, 0.35, 0.85, 1], [0, 1, 1, 0]);
  const y = useTransform(progress, [0, 0.45], [reduced ? 0 : 80, 0]);

  const cards = [
    { title: "Students", text: "A structured skill profile, levels 1 to 5, matched against every live opening with the reason for every score.", color: "#7285C2" },
    { title: "Faculty", text: "Batch-level gap analytics. Docker is required by 48% of postings and held ready by 15% of your batch. Now you know what to teach.", color: "#95709F" },
    { title: "Recruiters", text: "Post required skills with minimum levels and get a ranked list of students who actually fit, with what each one is missing.", color: "#2F9599" },
  ];

  return (
    <motion.section style={{ opacity }} className="sticky top-0 flex h-screen items-center bg-cream">
      <motion.div style={{ scale, y }} className="mx-auto w-full max-w-6xl px-6 will-change-transform">
        <div className="label">the visibility gap</div>
        <h2 className="mt-2 font-display text-5xl md:text-7xl">
          Three groups, <span className="text-signal">one</span> blind spot.
        </h2>
        <p className="mt-4 max-w-2xl text-lg text-plum/80">
          Colleges teach, companies hire, students guess. Setu turns the same skill data three ways so each group finally sees what the others already know.
        </p>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {cards.map((card) => (
            <div key={card.title} className="card-mauve">
              <div className="font-display text-3xl" style={{ color: card.color }}>
                {card.title}
              </div>
              <p className="mt-2 text-sm text-plum/80">{card.text}</p>
            </div>
          ))}
        </div>
      </motion.div>
    </motion.section>
  );
}

function Reveal({ progress, reduced, ctaTo }) {
  const scale = useTransform(progress, [0, 0.6], [reduced ? 1 : 0.7, 1]);
  const opacity = useTransform(progress, [0, 0.3], [0, 1]);
  const rotateX = useTransform(progress, [0, 0.6], [reduced ? 0 : 18, 0]);

  return (
    <section className="sticky top-0 flex h-screen items-center bg-plum text-cream">
      <div className="mx-auto w-full max-w-6xl px-6" style={{ perspective: 1200 }}>
        <div className="mb-6 text-center">
          <div className="label text-petal">act three</div>
          <h2 className="font-display text-5xl md:text-6xl">The app begins.</h2>
        </div>
        <motion.div style={{ scale, opacity, rotateX }} className="rounded-card border border-petal/20 bg-cream p-4 text-plum shadow-2xl will-change-transform md:p-6">
          <div className="grid gap-4 md:grid-cols-[180px_1fr]">
            <div className="hidden rounded-2xl bg-petal/60 p-4 md:block">
              <div className="font-display text-2xl">Setu</div>
              <div className="mt-4 grid gap-2">
                {["Dashboard", "My skills", "Openings", "Applications"].map((item, index) => (
                  <div key={item} className={`rounded-xl px-3 py-2 text-sm ${index === 0 ? "bg-white shadow-soft" : "text-plum/60"}`}>
                    {item}
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-4">
              <div className="flex items-center justify-between">
                <div className="font-display text-3xl">Hello, Shivam</div>
                <div className="font-mono text-xs text-violet">CSE 2026</div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[
                  ["Readiness", 72, "#2F9599"],
                  ["Best match", 94, "#7285C2"],
                  ["Verified", 40, "#C08010"],
                ].map(([label, value, color]) => (
                  <div key={label} className="rounded-2xl bg-petal/60 p-3 text-center">
                    <div className="font-display text-3xl" style={{ color }}>
                      {value}%
                    </div>
                    <div className="label">{label}</div>
                  </div>
                ))}
              </div>
              <div className="rounded-2xl bg-white/80 p-3">
                <div className="label">learn next</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {["Docker", "Linux", "Statistics", "Testing"].map((skill) => (
                    <span key={skill} className="chip bg-petal">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="mt-6 flex justify-center">
            <Link to={ctaTo} className="btn-primary">
              Open Setu
            </Link>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

export default function Landing() {
  const reduced = useReducedMotion();
  const { user } = useAuth();
  const ctaTo = user ? homeFor(user.role) : "/login";

  const heroRef = useRef(null);
  const introRef = useRef(null);
  const revealRef = useRef(null);
  const hero = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const intro = useScroll({ target: introRef, offset: ["start end", "end start"] });
  const reveal = useScroll({ target: revealRef, offset: ["start end", "end end"] });

  return (
    <div className="bg-cream">
      <div ref={heroRef} className="h-[160vh]">
        <Hero progress={hero.scrollYProgress} reduced={reduced} />
      </div>
      <div ref={introRef} className="h-[180vh]">
        <Intro progress={intro.scrollYProgress} reduced={reduced} />
      </div>
      <div ref={revealRef} className="h-[170vh]">
        <Reveal progress={reveal.scrollYProgress} reduced={reduced} ctaTo={ctaTo} />
      </div>
      <footer className="bg-plum px-6 py-8 text-center font-mono text-xs text-cream/60">Setu. Skill mapping and placement. Built at a hackathon.</footer>
    </div>
  );
}
