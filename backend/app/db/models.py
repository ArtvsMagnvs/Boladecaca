from app.db.database import (
    Config,
    Project,
    Task,
    CalendarEvent,
    Conversation,
    ChatMessage,
    Agent,
    AgentExecution,  # V0.5 (Fase 2 AgentManager + ExecutionEngine)
    EmailAutoReplyRule,  # V0.7 (Fase 4 Email + Calendar)
    CalendarAvailability,  # V0.7 (Fase 4 Email + Calendar)
    MeetingProposal,  # V0.7 extra (Fase 4): propuestas de reunion automaticas
    EmailActivityLog,  # V0.7 extra (FIX): dashboard persistente de actividad
    EmailTriage,  # V0.7.3 (Sprint 3): categoria de triaje por email
    MemoryJobRun,  # V0.85 (MOS M1): tracking de jobs de memoria
    Decision,  # V0.85 (MOS M1): Decision Memory (tabla + espejo mem_decision)
    AIProviderConfig,
)
