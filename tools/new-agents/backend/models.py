from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

# Using Flask's current_app is better for fetching config dynamically, 
# but a simpler approach for these tests is to pass the URL or retrieve it from app context.
# We'll retrieve the DATABASE_URL from the Flask config if active.
from flask import current_app
from config import Config

Base = declarative_base()

class LlmConfig(Base):
    __tablename__ = 'llm_config'

    id = Column(Integer, primary_key=True)
    config_key = Column(String(64), unique=True, nullable=False)
    api_key = Column(Text, nullable=False)
    base_url = Column(Text, nullable=False)
    model = Column(String(128), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

def get_engine():
    # If inside app context, use app's db url (allows overriding for tests)
    db_url = current_app.config.get('DATABASE_URL') if current_app else Config.DATABASE_URL
    return create_engine(db_url)

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
