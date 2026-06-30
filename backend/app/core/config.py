# Aithera Core Configuration
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # App settings
    APP_NAME = "Aithera"
    VERSION = "0.1"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # API settings
    API_URL = "http://localhost:8000"
    API_PREFIX = "/api"
    
    # AI Settings
    DEFAULT_AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3")
    
    # Ollama settings
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    
    # OpenAI settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")
    
    # Anthropic settings
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aithera.db")


settings = Settings()
