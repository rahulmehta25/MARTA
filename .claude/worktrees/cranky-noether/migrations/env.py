"""
Alembic Environment Configuration for MARTA Platform
Handles database migrations with proper logging and configuration
"""
import asyncio
import os
import sys
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Add the project root to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import settings and models
from config.settings import settings
from src.database.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL from settings
config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def include_name(name, type_, parent_names):
    """Include only specific schemas/tables in migrations"""
    if type_ == "schema":
        return name in [None, "public"]
    else:
        return True

def include_object(object, name, type_, reflected, compare_to):
    """Filter objects to include in migrations"""
    # Skip views and materialized views in autogenerate
    if type_ == "table" and name.startswith("mv_"):
        return False
    
    # Skip temporary tables
    if type_ == "table" and (name.startswith("tmp_") or name.startswith("temp_")):
        return False
    
    return True

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with connection"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=include_name,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
        # Custom migration options
        user_module_prefix='marta_',
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def process_revision_directives(context, revision, directives):
    """Process revision directives for enhanced migration generation"""
    # Add custom logic for migration processing
    migration_script = directives[0]
    
    # Add helpful comments to generated migrations
    if migration_script.upgrade_ops_list:
        migration_script.message = f"Auto-generated migration: {migration_script.message}"
    
    # Log migration generation
    print(f"Generated migration: {migration_script.rev_id} - {migration_script.message}")


async def run_async_migrations() -> None:
    """Run migrations in async mode"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Check if we're running in async mode
    if context.get_x_argument(as_dictionary=True).get('async', False):
        asyncio.run(run_async_migrations())
        return

    # Synchronous mode
    from sqlalchemy import engine_from_config
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()