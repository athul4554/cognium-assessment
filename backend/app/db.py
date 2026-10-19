import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Docker sets DATABASE_URL; local runs (e.g. alembic) fall back to the .env credentials
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://{user}:{password}@localhost:{port}/{db}".format(
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        port=os.getenv("DB_PORT", "5432"),
        db=os.getenv("POSTGRES_DB", "user-risk-assessment"),
    ),
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
