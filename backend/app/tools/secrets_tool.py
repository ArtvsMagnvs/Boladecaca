# backend/app/tools/secrets_tool.py
#
# V1.0/1.1 (Tools): almacen generico de secretos del usuario (API keys de
# servicios externos que Aithera todavia no modela con su propio flujo, p.ej.
# credenciales de un servicio que un agente necesita usar puntualmente).
#
# NO sustituye los almacenes ya existentes con su propio ciclo de vida:
# AIProviderConfig (proveedores IA, cifrado por AIManager) ni el token de
# Telegram (cifrado en su propio endpoint). Este es el cajon generico para
# TODO LO DEMAS -- misma tecnica de cifrado (DPAPI via app.core.secrets),
# namespace propio en la tabla Config ("secret:<name>") para no chocar con
# ninguna key interna existente.
#
# Acciones:
#   get_secret    -> devuelve el valor DESCIFRADO (uso interno de un agente/tool)
#   set_secret    -> guarda/actualiza un secreto (cifrado en reposo)
#   list_secrets  -> lista los NOMBRES + valor ENMASCARADO (nunca el valor real)
#   delete_secret -> elimina un secreto
#
# get_secret NO requiere confirmacion (lectura por el propio sistema para uso
# interno), pero set_secret/delete_secret si -- son cambios de estado sensible.

from typing import Dict, Any, List

from .base import BaseTool
from app.core.secrets import encrypt, decrypt, mask

_PREFIX = "secret:"


class SecretsTool(BaseTool):
    tool_id = "secrets"
    name = "Secrets Tool"
    description = (
        "Guarda y recupera API keys/credenciales genericas, cifradas en reposo "
        "(DPAPI). list_secrets NUNCA devuelve el valor real, solo enmascarado."
    )
    requires_confirmation = False  # depende de la accion

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            handler = {
                "get_secret": self._get_secret,
                "set_secret": self._set_secret,
                "list_secrets": self._list_secrets,
                "delete_secret": self._delete_secret,
            }.get(action)
            if not handler:
                return {
                    "success": False, "result": None,
                    "error": f"Accion desconocida: {action}. Disponibles: get_secret, set_secret, list_secrets, delete_secret",
                }
            return await handler(params)
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "get_secret",
                "description": "Obtiene el valor descifrado de un secreto guardado (uso interno).",
                "requires_confirmation": False,
                "params": {"name": "string (ej. 'brave_search_api_key')"},
            },
            {
                "id": "set_secret",
                "description": "Guarda o actualiza un secreto (se cifra en reposo con DPAPI).",
                "requires_confirmation": True,
                "params": {"name": "string", "value": "string"},
            },
            {
                "id": "list_secrets",
                "description": "Lista los nombres de secretos guardados con su valor enmascarado.",
                "requires_confirmation": False,
                "params": {},
            },
            {
                "id": "delete_secret",
                "description": "Elimina un secreto guardado.",
                "requires_confirmation": True,
                "params": {"name": "string"},
            },
        ]

    def _key(self, name: str) -> str:
        return f"{_PREFIX}{name}"

    async def _get_secret(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = (params.get("name") or "").strip()
        if not name:
            return {"success": False, "result": None, "error": "falta parametro: name"}
        from app.db.database import SessionLocal
        from app.db.models import Config

        db = SessionLocal()
        try:
            row = db.query(Config).filter(Config.key == self._key(name)).first()
            if not row:
                return {"success": False, "result": None, "error": f"secreto no encontrado: {name}"}
            return {"success": True, "result": {"name": name, "value": decrypt(row.value)}, "error": None}
        finally:
            db.close()

    async def _set_secret(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = (params.get("name") or "").strip()
        value = params.get("value")
        if not name or not value:
            return {"success": False, "result": None, "error": "faltan parametros: name y value"}
        from app.db.database import SessionLocal
        from app.db.models import Config

        db = SessionLocal()
        try:
            key = self._key(name)
            row = db.query(Config).filter(Config.key == key).first()
            enc = encrypt(value)
            if row:
                row.value = enc
            else:
                db.add(Config(key=key, value=enc))
            db.commit()
            return {"success": True, "result": {"name": name, "saved": True}, "error": None}
        finally:
            db.close()

    async def _list_secrets(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.db.database import SessionLocal
        from app.db.models import Config

        db = SessionLocal()
        try:
            rows = db.query(Config).filter(Config.key.like(f"{_PREFIX}%")).all()
            items = [
                {"name": r.key[len(_PREFIX):], "value_preview": mask(decrypt(r.value))}
                for r in rows
            ]
            return {"success": True, "result": {"secrets": items, "count": len(items)}, "error": None}
        finally:
            db.close()

    async def _delete_secret(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = (params.get("name") or "").strip()
        if not name:
            return {"success": False, "result": None, "error": "falta parametro: name"}
        from app.db.database import SessionLocal
        from app.db.models import Config

        db = SessionLocal()
        try:
            row = db.query(Config).filter(Config.key == self._key(name)).first()
            if not row:
                return {"success": False, "result": None, "error": f"secreto no encontrado: {name}"}
            db.delete(row)
            db.commit()
            return {"success": True, "result": {"name": name, "deleted": True}, "error": None}
        finally:
            db.close()
