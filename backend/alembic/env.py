import logging

from alembic import context
from sqlalchemy import create_engine

from app import models  # noqa: F401  registers the tables on Base.metadata
from app.db import DATABASE_URL, Base

logging.basicConfig(format="%(message)s")
logging.getLogger("alembic").setLevel(logging.INFO)

if context.is_offline_mode():
    # `alembic upgrade head --sql` prints the SQL without connecting
    context.configure(url=DATABASE_URL, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(DATABASE_URL).connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
