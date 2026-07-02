from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
# FIX V0.2: declarative_base movido a sqlalchemy.orm en SQLAlchemy 2.0
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

# FIX V0.4 (Fase 1b PostgreSQL Migration):
# El engine ya no esta hardcoded a SQLite. Lee DATABASE_URL desde
# app.core.config (que a su vez la lee del .env). Si la URL es SQLite,
# anade connect_args={'check_same_thread': False} para que SQLAlchemy
# permita el uso multi-thread (FastAPI/uvicorn). Para PostgreSQL no
# hace falta ningun connect_args especial.
#
# Adicionalmente, garantizamos que el directorio padre de la BD SQLite
# exista antes de crear el engine, para no romper el arranque la primera
# vez en una maquina nueva.
from app.core.config import DATABASE_URL

if DATABASE_URL.startswith("sqlite"):
    # Deriva la ruta del fichero sqlite3:// y asegura que el directorio existe.
    sqlite_path = DATABASE_URL.replace("sqlite:///", "", 1)
    parent = os.path.dirname(sqlite_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    # PostgreSQL (u otro backend): connect_args vacio.
    engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _ensure_columns():
    """
    Migracion ligera sin Alembic: Base.metadata.create_all() solo CREA tablas
    que no existen, nunca anade columnas a una tabla ya existente. Como esta
    app no tenia sistema de migraciones hasta V0.4 (Alembic), cualquier columna
    nueva (ej. las de Fase 6: priority/due_date/notes en projects, assignee en
    tasks, o las de V0.4/Fase 2: allowed_tools/max_execution_time/updated_at
    en agents) se quedaria fuera de la base de datos real del usuario y cada
    insert fallaria con "no such column". Esto comprueba las columnas que
    existen de verdad en SQLite y anade las que falten con ALTER TABLE.

    NOTA V0.4 (Fase 1b PostgreSQL): usuarios en PostgreSQL NO necesitan esta
    funcion porque Alembic gestiona las migraciones via scripts/. Se conserva
    aqui SOLO para compatibilidad con instalaciones SQLite existentes que
    aun no han migrado.
    """
    from sqlalchemy import inspect, text

    expected = {
        'projects': {
            'priority': "ALTER TABLE projects ADD COLUMN priority VARCHAR(20) DEFAULT 'medium'",
            'due_date': "ALTER TABLE projects ADD COLUMN due_date DATETIME",
            'notes': "ALTER TABLE projects ADD COLUMN notes TEXT",
        },
        'tasks': {
            'assignee': "ALTER TABLE tasks ADD COLUMN assignee VARCHAR(100)",
        },
        # V0.4 (Fase 2 AgentManager + ToolSystem): nuevas columnas en agents
        # para soportar allowed_tools (whitelist de tool_id) y max_execution_time.
        'agents': {
            'allowed_tools': "ALTER TABLE agents ADD COLUMN allowed_tools TEXT DEFAULT '[]'",
            'max_execution_time': "ALTER TABLE agents ADD COLUMN max_execution_time INTEGER DEFAULT 300",
            'updated_at': "ALTER TABLE agents ADD COLUMN updated_at DATETIME",
        },
    }

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.connect() as conn:
        for table, columns in expected.items():
            if table not in existing_tables:
                continue  # create_all() ya la crea con todas las columnas.
            existing_columns = {col['name'] for col in inspector.get_columns(table)}
            for column_name, ddl in columns.items():
                if column_name not in existing_columns:
                    conn.execute(text(ddl))
        conn.commit()


def init_db():
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
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
    # Fase 6 - Proyectos y Tareas: prioridad, fecha limite y notas, para que
    # un proyecto tenga la misma informacion util que ya tenia una tarea.
    priority = Column(String(20), default='medium')
    due_date = Column(DateTime)
    notes = Column(Text)
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
    # Fase 6 - Proyectos y Tareas: responsable de la tarea.
    assignee = Column(String(100))
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
    # V0.7 (Fase 4): id del evento en Google Calendar para sync incremental.
    # Vacio/null si fue creado manualmente en Aithera (no sincronizado).
    google_event_id = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

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
    # V0.5 (Fase 2 AgentManager + ExecutionEngine): agent_type gana un
    # default 'generic' para no depender de que el cliente lo mande y para
    # que el catalog de tipos este bien definido (generic/claude_code/
    # minimax/ollama/custom).
    agent_type = Column(String(50), default='generic')
    description = Column(Text)
    system_prompt = Column(Text)
    # V0.5: lista de tool_id permitidos (ej. ["filesystem", "shell"]). Se
    # almacena como JSON string en TEXT para no anadir dependencias (json
    # nativo de Python). El ExecutionEngine valida que un agente SOLO puede
    # llamar herramientas cuyo tool_id este en esta lista.
    allowed_tools = Column(Text, default='[]')
    # V0.5: tiempo maximo de ejecucion por tarea en segundos (default 5min).
    max_execution_time = Column(Integer, default=300)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class AgentExecution(Base):
    """
    V0.5 (Fase 2 AgentManager + ExecutionEngine): registro historico de cada
    tarea lanzada por un agente. Permite auditar QUE hizo el agente, CON QUE
    herramientas, y que resultado/error obtuvo. Tambien permite cancelar
    tareas en curso desde la UI (status='cancelled').

    Estados posibles:
      - pending:   registrada en DB pero aun no lanzada
      - running:   asyncio.Task en ejecucion
      - completed: termino con exito (campo result poblado)
      - failed:    termino con error (campo error_message poblado)
      - cancelled: el usuario la cancelo antes de que terminara
    """
    __tablename__ = 'agent_executions'
    id = Column(Integer, primary_key=True)
    agent_id = Column(Integer, ForeignKey('agents.id', ondelete='CASCADE'), nullable=False)
    task_description = Column(Text)
    status = Column(String(20), default='pending')
    result = Column(Text)
    error_message = Column(Text)
    # V0.5: registro de las herramientas que el agente decidio usar durante
    # esta ejecucion. Se guarda como JSON list de {tool_id, action, params, result}.
    tool_calls = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailAutoReplyRule(Base):
    """
    V0.7 (Fase 4) + V0.7 extra: regla de auto-respuesta configurable.

    El usuario puede anadir reglas desde la UI de Email o desde el chat
    (ej. "siempre responde automaticamente a los emails de mi jefe").
    Cuando llega un email, Aithera consulta las reglas habilitadas y,
    si alguna matchea, actua segun el campo `action`.

    Campos V0.7 (legacy - mantenidos por compatibilidad):
      - matching: 'sender_contains' | 'subject_contains' | 'sender_domain'
      - pattern: substring o dominio a matchear

    Campos V0.7 extra (refactor para que sea mas intuitivo):
      - sender_emails: JSON array de emails exactos a matchear (case-insensitive)
        ej. ["jefe@empresa.com", "cliente1@gmail.com"]
      - sender_domains: JSON array de dominios completos a matchear
        ej. ["empresa.com", "cliente.com"]
      - action: 'auto_send' | 'create_draft' | 'alert_only'
        - auto_send: envia la respuesta inmediatamente
        - create_draft: crea un borrador para revision manual
        - alert_only: NO envia nada, solo registra el evento
      - detect_meeting_with_ia: bool, default True.
        Si True, Aithera usa la IA para detectar si el email propone una
        reunion. Si es asi, en vez de usar el reply_template, usa el
        workflow de propuestas (consulta calendario, propone nueva fecha).
      - reply_template: texto con {sender}, {subject}, {body} como variables.

    Nota: para mantener compatibilidad con reglas antiguas, si matching+pattern
    estan presentes, tambien se usan para matching.
    """
    __tablename__ = 'email_auto_reply_rules'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    # V0.7 (legacy)
    matching = Column(String(30), default='sender_contains')
    pattern = Column(String(200), nullable=False)
    reply_template = Column(Text, nullable=False)
    # V0.7.3 (Sprint 4, B6 - patron Inbox Zero): autonomia gradual por regla.
    #   'propose' (default): si action='auto_send', se degrada a borrador
    #                        (el usuario aprueba antes de que salga nada).
    #   'auto'             : la regla actua sola (se gana con confianza).
    # Los contadores se alimentan del feedback del usuario sobre cada
    # propuesta; con saldo >= 5 la UI ofrece "subir a automatico".
    autonomy = Column(String(10), nullable=False, default='propose')
    approved_count = Column(Integer, nullable=False, default=0)
    edited_count = Column(Integer, nullable=False, default=0)
    rejected_count = Column(Integer, nullable=False, default=0)
    enabled = Column(Boolean, default=True)
    # V0.7 extra: cuando es True, NO usa reply_template para reuniones.
    # La IA genera la respuesta completa (confirmacion o contrapropuesta).
    # Para emails NO-reunion, sigue usando reply_template.
    # V0.7 extra: matching por listas (mas intuitivo)
    sender_emails = Column(Text, default='[]')   # JSON list
    sender_domains = Column(Text, default='[]')  # JSON list
    # V0.7 extra: accion a tomar cuando matchea
    action = Column(String(20), default='auto_send')
    # V0.7 extra: deteccion de reuniones con IA
    detect_meeting_with_ia = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class CalendarAvailability(Base):
    """
    V0.7 (Fase 4): configuracion manual de disponibilidad del usuario.

    El usuario puede marcar bloques de tiempo (fecha + rango de horas)
    como available (libre para reuniones), unavailable (no disponible)
    o busy (ya tiene algo, no queremos meter otra cosa).

    Tambien sirve como override sobre lo que diga Google Calendar:
    la UI muestra el dia en color segun las reglas locales primero,
    y como secundario los eventos sincronizados de Google.

    status:
      - 'available': libre (verde)
      - 'unavailable': NO disponible (rojo)
      - 'busy': ocupado por algo ya planeado (amarillo)

    hour_start y hour_end son enteros 0-23 (hora local, sin minutos).
    Si hour_end <= hour_start, se interpreta como "todo el dia".
    """
    __tablename__ = 'calendar_availability'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)  # solo la fecha importa, hora = 00:00
    hour_start = Column(Integer, default=0)  # 0-23
    hour_end = Column(Integer, default=24)   # 0-24 (24 = fin del dia)
    status = Column(String(20), default='available')
    label = Column(String(200))  # ej. "Reunion cliente X" o "Vacaciones"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class MeetingProposal(Base):
    """
    V0.7 extra (Fase 4 Email + Calendar): propuesta de reunion automatica.

    Flujo:
      1. Llega un email pidiendo reunion (clasificado como 'meeting')
      2. Aithera extrae la fecha propuesta (IA) y consulta el calendario
      3. Si esta ocupado, Aithera genera una propuesta alternativa con IA
         consultando dias disponibles y envia un email sugiriendo la nueva fecha
      4. Cuando el remitente confirma (otro email), Aithera:
         - marca el dia/hora confirmado como 'busy' en calendar_availability
         - actualiza el estado de la propuesta a 'confirmed'

    Campos:
      - email_id_original: id del email en Gmail que pidio la reunion
      - sender, subject, body_snippet: datos del email original
      - original_proposed_datetime: lo que propuso el remitente
      - counter_proposed_datetime: lo que Aithera propuso como alternativa
      - status: pending | counter_sent | confirmed | rejected | expired
      - reply_email_id: id del email de respuesta enviado por Aithera
      - confirmation_email_id: id del email del remitente confirmando
    """
    __tablename__ = 'meeting_proposals'
    id = Column(Integer, primary_key=True)
    email_id_original = Column(String(200), nullable=False)
    sender = Column(String(300), nullable=False)
    subject = Column(String(500))
    body_snippet = Column(Text)
    original_proposed_datetime = Column(DateTime)
    counter_proposed_datetime = Column(DateTime)
    status = Column(String(30), default='pending')
    reply_email_id = Column(String(200))
    confirmation_email_id = Column(String(200))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime)


class EmailActivityLog(Base):
    """
    V0.7 extra (FIX usuario): registro PERSISTENTE de todo lo que Aithera
    hace con cada email procesado. Es el "dashboard" del Email Assistant.

    Cada accion que el sistema toma (responder, crear borrador, alertar,
    proponer reunion, error) se guarda aqui para que el usuario pueda:
      - Ver que paso con cada email
      - Filtrar por tipo (enviado/borrador/alerta/reunion/error)
      - Marcar como leido
      - Borrar entradas

    action_type:
      - 'sent': Aithera envio una respuesta automaticamente
      - 'draft': Aithera creo un borrador en Gmail
      - 'alert': Aithera detecto algo importante y avisa al usuario
      - 'meeting_proposal': Aithera propuso una nueva fecha para una reunion
      - 'meeting_confirmed': Aithera confirmo una reunion (tras respuesta del remitente)
      - 'auto_replied': Aithera respondio con plantilla (no relacionada con reuniones)
      - 'error': Error procesando el email
      - 'skipped': Email ignorado (sin regla que matchee)
    """
    __tablename__ = 'email_activity_log'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    email_id = Column(String(200))
    sender = Column(String(300))
    sender_email = Column(String(300))  # solo el email sin el nombre
    subject = Column(String(500))
    snippet = Column(Text)
    action_type = Column(String(30), nullable=False)
    # V0.7 extra: JSON con campos especificos segun action_type
    # Ej: para sent: {reply_body, message_id, rule_id}
    # Ej: para meeting_proposal: {original_date, proposed_date, calendar_status}
    # Ej: para alert: {reason, preview_reply}
    details = Column(Text)
    rule_id = Column(Integer)
    rule_name = Column(String(200))
    read = Column(Boolean, default=False)  # si el usuario ya lo vio en dashboard



class EmailTriage(Base):
    """
    V0.7.3 (Sprint 3 PLAN_MAESTRO_2026, B5): categoria de triaje por email.

    El clasificador de 2 etapas (heuristica barata -> LLM solo si ambiguo,
    patron Inbox Zero / AMD GAIA) persiste aqui el resultado para que el
    inbox se muestre categorizado sin re-clasificar en cada carga.

    category (7 fijas):
      - 'urgente'     : requiere atencion inmediata
      - 'responder'   : espera respuesta del usuario
      - 'reunion'     : propuesta/confirmacion de reunion
      - 'newsletter'  : boletines, listas de correo
      - 'factura'     : facturas, recibos, pagos
      - 'spam-social' : notificaciones de redes sociales / promos
      - 'fyi'         : informativo, sin accion requerida

    method: 'heuristic' | 'llm' | 'fallback' (LLM caido -> fyi)
    """
    __tablename__ = 'email_triage'

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(String(120), unique=True, index=True, nullable=False)
    sender = Column(String(300))
    subject = Column(String(500))
    category = Column(String(20), nullable=False, index=True)
    method = Column(String(12), nullable=False, default='heuristic')
    created_at = Column(DateTime, default=datetime.utcnow)

class AIProviderConfig(Base):
    """
    Fase 2 - Sistema de IA: proveedores configurados por el usuario.

    Esta tabla es la fuente de verdad de que proveedores de IA estan
    disponibles (ollama, openai, anthropic, gemini, minimax, deepseek,
    openrouter, grok), que modelo tienen seleccionado y cual esta activo.
    Sustituye la dependencia exclusiva de variables de entorno.

    La API key se guarda localmente en esta base de datos SQLite (que vive
    en %APPDATA%/Aithera, en la maquina del propio usuario). Nunca se
    incrusta en el codigo fuente ni se envia a servidores de Aithera.
    """
    __tablename__ = 'ai_provider_configs'
    id = Column(Integer, primary_key=True)
    provider = Column(String(50), unique=True, nullable=False)
    model = Column(String(200))
    api_key = Column(Text)
    base_url = Column(String(300))
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

init_db()
