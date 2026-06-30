# Architect Agent - AI Agent for project architecture assistance
from typing import Dict, Any, Optional
from app.ai.ai_manager import ai_manager


SYSTEM_PROMPT = """Eres Aithera Architect, un agente especializado en arquitectura de software y diseño de sistemas.

Tu especialidad incluye:
- Diseño de arquitectura de aplicaciones
- Patrones de diseño (MVC, microservices, event-driven, etc.)
- Revisión de código y mejores prácticas
- Planificación técnica de proyectos
- Base de datos y modelado de datos

Siempre proporciona código bien documentado y explicaciones claras. Prioriza soluciones simples y mantenibles."""


class ArchitectAgent:
    """Agent specialized in software architecture."""
    
    def __init__(self):
        self.name = "Architect"
        self.system_prompt = SYSTEM_PROMPT
    
    async def analyze(self, query: str) -> Dict[str, Any]:
        """Analyze a query related to architecture."""
        return await ai_manager.chat(
            message=query,
            system_prompt=self.system_prompt
        )
    
    async def review_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Review code and provide architecture feedback."""
        prompt = f"""Por favor revisa el siguiente código en {language} y proporciona retroalimentación sobre:

1. Calidad del código
2. Posibles mejoras de arquitectura
3. Problemas potenciales
4. Mejores prácticas

Código a revisar:
```{language}
{code}
```"""
        return await ai_manager.chat(prompt, self.system_prompt)


# Global architect agent instance
architect_agent = ArchitectAgent()
