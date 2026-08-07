from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import DATABASE_URL
from app.database import Base
from app import models  # noqa: F401


# Alembic Config
config = context.config


# Usa a mesma URL configurada pela aplicação
config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL,
)


# Configura logging do alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# Metadata usada pelo autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Executa migrations sem abrir conexão direta com o banco.
    """
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Executa migrations usando conexão real com o banco.
    """
    configuration = config.get_section(
        config.config_ini_section
    )

    if configuration is None:
        configuration = {}

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()