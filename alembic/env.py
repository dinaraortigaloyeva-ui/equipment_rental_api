"""Alembic migration muhiti.

Baza manzili .env faylidan (app.config orqali) olinadi, shuning uchun
alembic.ini ichida parol saqlanmaydi.
"""

from logging.config import fileConfig

from alembic import context

from app.config import settings
from app.database import Base, engine

# Modellarni import qilish shart: shunda Base.metadata ichida jadvallar paydo bo'ladi
# va autogenerate ularni ko'ra oladi.
from app import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate uchun modellar metadatasi
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Bazaga ulanmasdan, faqat SQL skript chiqarish rejimi."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Bazaga ulanib migration bajarish rejimi (odatiy)."""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()