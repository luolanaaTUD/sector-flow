from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@event.listens_for(engine, "connect")
def _set_db_timezone(dbapi_connection, connection_record):
    """Keep all DB sessions on Asia/Shanghai for timestamp consistency."""
    del connection_record
    with dbapi_connection.cursor() as cursor:
        cursor.execute("SET TIME ZONE 'Asia/Shanghai'")


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import fund_flow  # noqa: F401 – ensures table metadata is registered
    Base.metadata.create_all(bind=engine)
