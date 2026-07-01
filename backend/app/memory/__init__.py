# backend/app/memory/__init__.py
#
# V0.6 (Fase 3 Memory System): paquete de memoria semantica de Aithera.
#
# Importar `app.memory.memory_manager` activa el singleton `memory_manager`.
# El constructor es lazy y robusto: si chromadb o sentence-transformers
# fallan, `memory_manager.is_healthy()` devolvera False y los metodos
# devolveran resultados vacios sin romper el backend.

from .memory_manager import MemoryManager, memory_manager, CHROMA_PATH

__all__ = ["MemoryManager", "memory_manager", "CHROMA_PATH"]