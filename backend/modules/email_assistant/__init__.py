# Email Assistant Module
# Aithera Email Executive Assistant V1

__version__ = "1.0.0"
__author__ = "Aithera"

from .gmail_tool import GmailTool
from .calendar_tool import CalendarTool
from .email_intelligence import EmailIntelligenceEngine
from .conversation_engine import ConversationEngine
from .memory import EmailMemory

__all__ = [
    "GmailTool",
    "CalendarTool", 
    "EmailIntelligenceEngine",
    "ConversationEngine",
    "EmailMemory"
]
