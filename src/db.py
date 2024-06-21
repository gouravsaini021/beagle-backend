from typing import List,AsyncGenerator
import pytz
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy import ForeignKey
from sqlalchemy import Integer,String,DateTime
from sqlalchemy.orm import Mapped,Session
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession,async_sessionmaker

from src import MYSQL_STRING

mysql_string=MYSQL_STRING

engine = create_async_engine(mysql_string)

SessionLocal = async_sessionmaker(
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession
)


# Dependency to get DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
        await session.close()





class Base(DeclarativeBase):
    pass


class SoftUpload(Base):
    __tablename__ = 'SoftUpload'

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    creation = mapped_column(DateTime(timezone=True), default=datetime.now(pytz.timezone('Asia/Kolkata')))
    ip = mapped_column(String(100))
    content_type = mapped_column(String(255))
    unique_id = mapped_column(String(100))
    release_version = mapped_column(String(100))
    file_path = mapped_column(String(100))
    file_extension = mapped_column(String(10))
    file_link = mapped_column(String(100))

class Heartbeat(Base):
    __tablename__ = 'Heartbeat'

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    creation = mapped_column(DateTime(timezone=True), default=datetime.now(pytz.timezone('Asia/Kolkata')))
    ip = mapped_column(String(100))
    unique_id = mapped_column(String(100))
    release_version = mapped_column(String(100))

class HeartbeatUpload(Base):
    __tablename__ = 'HeartbeatUpload'

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    creation = mapped_column(DateTime(timezone=True), default=datetime.now(pytz.timezone('Asia/Kolkata')))
    ip = mapped_column(String(100))
    unique_id = mapped_column(String(100))
    release_version = mapped_column(String(100))
    file_path = mapped_column(String(100))
    file_extension = mapped_column(String(10))
    file_link = mapped_column(String(100))

class Print2wa(Base):
    __tablename__ = 'Print2wa'

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    creation = mapped_column(DateTime(timezone=True))
    timestamp = mapped_column(DateTime(timezone=True))
    ip = mapped_column(String(50))
    phone_number = mapped_column(String(50))
    device_id = mapped_column(String(100))
    release_version = mapped_column(String(100))
    file_link = mapped_column(String(100))
    file_extension = mapped_column(String(100))
    file_path = mapped_column(String(100))
    content_type = mapped_column(String(255))