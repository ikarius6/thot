from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./thot.db")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Define REGEXP function for SQLite
import re
from sqlalchemy import event

def regexp(expr, item):
    if item is None:
        return False
    reg = re.compile(expr, re.I)
    return reg.search(item) is not None

@event.listens_for(engine, "connect")
def sqlite_engine_connect(dbapi_connection, connection_record):
    dbapi_connection.create_function("REGEXP", 2, regexp)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class ImageHash(Base):
    __tablename__ = "image_hashes"

    id = Column(Integer, primary_key=True, index=True)
    phash = Column(String, unique=True, index=True)
    tags = Column(String)  # Comma-separated tags, shared by all images with this hash
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to all images with this hash
    images = relationship("Image", back_populates="image_hash")


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    filename = Column(String, index=True)
    hash_id = Column(Integer, ForeignKey("image_hashes.id"), nullable=True, index=True)
    is_active = Column(Integer, default=1, index=True)  # Using Integer as Boolean for SQLite compatibility if needed, though Boolean works too
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to the hash entry
    image_hash = relationship("ImageHash", back_populates="images")


class TagQueue(Base):
    __tablename__ = "tag_queue"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, index=True)
    status = Column(String, default="pending")  # pending/processing/done/error
    error_msg = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WatchedFolder(Base):
    __tablename__ = "watched_folders"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)



class Settings(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String)


Base.metadata.create_all(bind=engine)
