from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import sqlalchemy_url

engine = create_engine(
    sqlalchemy_url(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)


@event.listens_for(engine, "checkout")
def set_schema(dbapi_connection, connection_record, connection_proxy):
    """Use the public schema for every pooled Neon connection.

    Neon may reset session settings after a connection is returned to its
    pool, so doing this only when a DBAPI connection is created is not
    sufficient.
    """
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET search_path TO public")


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
