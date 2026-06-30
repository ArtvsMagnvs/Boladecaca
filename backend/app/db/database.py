from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# NOTA (Fase 0 - Auditoria, junio 2026):
# Esta es la UNICA base de datos que usa realmente la aplicacion en runtime.
# Existe tambien un archivo "backend/aithera.db" en la raiz del repositorio
# que NO es leido por este modulo: es un artefacto huerfano de una version
# anterior del proyecto (posiblemente creado al ejecutar uvicorn desde otro
# directorio de trabajo). No se ha borrado automaticamente para no arriesgar
# datos del usuario sin confirmacion explicita. Antes de asumir que esos
# datos existen o no, verificar directamente en %APPDATA%/Aithera/aithera.db
# (la ruta calculada abajo), que es la fuente de verdad.
DB_PATH = os.path.join(os.environ.get('APPDATA') or '.', 'Aithera', 'aithera.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine('sqlite:///' + DB_PATH, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        config = db.query(Config).first()
        if not config:
            c = Config(key='ai_provider', value='ollama')
            db.add(c)
            m = Config(key='default_model', value='llama3')
            db.add(m)
            v = Config(key='voice_enabled', value='true')
            db.add(v)
            db.commit()
    finally:
        db.close()

class Config(Base):
    __tablename__ = 'config'
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True)
    value = Column(Text)

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    description = Column(Text)
    status = Column(String(50), default='active')
    progress = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    description = Column(Text)
    status = Column(String(50), default='pending')
    priority = Column(String(20), default='medium')
    project_id = Column(Integer, ForeignKey('projects.id'))
    due_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class CalendarEvent(Base):
    __tablename__ = 'calendar_events'
    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    description = Column(Text)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    all_day = Column(Boolean, default=False)
    color = Column(String(20), default='#00d4ff')
    created_at = Column(DateTime, default=datetime.utcnow)

class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(Integer, primary_key=True)
    role = Column(String(20))
    content = Column(Text)
    agent_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True)
    role = Column(String(20))
    content = Column(Text)
    model_used = Column(String(100))
    tokens_used = Column(Integer)
    agent_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class Agent(Base):
    __tablename__ = 'agents'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True)
    agent_type = Column(String(50))
    description = Column(Text)
    system_prompt = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

init_db()
