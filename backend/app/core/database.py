from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Settings(BaseSettings):
    DATABASE_URL: str
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()


engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.APP_ENV.lower() != "production",
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


class Base(DeclarativeBase):
    pass