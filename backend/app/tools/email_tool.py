# backend/app/tools/email_tool.py
#
# V0.7 (Fase 4 Email + Calendar): herramienta de Gmail.
#
# Acciones:
#   list_inbox        -> lista emails (label INBOX por defecto)
#   get_email         -> email completo por id
#   search_emails     -> busqueda con sintaxis de Gmail
#   create_draft      -> crea borrador en Gmail (no requiere confirmacion)
#   send_email        -> envia email (requiere confirmacion SIEMPRE)
#   classify_email    -> clasifica email con IA (urgent/follow_up/informational/spam)
#   list_auto_reply_rules    -> lista las reglas de auto-respuesta configuradas
#   add_auto_reply_rule      -> anade una regla de auto-respuesta
#   update_auto_reply_rule   -> actualiza una regla existente
#   delete_auto_reply_rule   -> elimina una regla
#   test_auto_reply          -> prueba si un email matchea alguna regla (dry-run)
#
# Las acciones de gestion de auto-reply (list/add/update/delete/test) NO
# requieren Google OAuth - funcionan contra la tabla local
# email_auto_reply_rules. Asi el usuario puede configurar sus reglas
# desde la UI o el chat sin necesidad de tener cuenta Google.
#
# Las acciones de Gmail (list_inbox, get_email, search_emails, create_draft,
# send_email, classify_email) SI requieren Google OAuth. Si no esta
# conectado, devuelven un error claro.

import dataclasses
import json
import base64
import os
import re
from datetime import datetime
from email.mime.text import MIMEText
from typing import Dict, Any, List, Literal, Optional

from .base import BaseTool
from app.integrations import google_auth


# Etiquetas validas para el campo "matching" de las auto-reply rules.
VALID_MATCHINGS = {"sender_contains", "subject_contains", "sender_domain"}


def _extract_email_address(from_header: str) -> str:
    """De un header 'From' (ej. 'John Doe <john@example.com>'), saca el email."""
    if not from_header:
        return ""
    match = re.search(r"<([^>]+)>", from_header)
    if match:
        return match.group(1).strip().lower()
    return from_header.strip().lower()


def _extract_domain(email_or_from: str) -> str:
    """Devuelve el dominio de un email. Si ya es 'user@dominio.com' lo devuelve."""
    email = _extract_email_address(email_or_from)
    if "@" in email:
        return email.split("@", 1)[1].lower()
    return ""


def _render_template(template: str, sender: str, subject: str, body: str) -> str:
    """Sustituye {sender}, {subject}, {body} en la plantilla."""
    return (template or "").format(
        sender=sender or "",
        subject=subject or "",
        body=(body or "")[:500],
    )


def _rule_can_promote_safe(r) -> bool:
    """V0.7.3 (Sprint 4, B6): wrapper fail-soft de rule_can_promote."""
    try:
        from app.services.email_service import rule_can_promote
        return rule_can_promote(
            getattr(r, "autonomy", "auto"),
            getattr(r, "approved_count", 0),
            getattr(r, "edited_count", 0),
            getattr(r, "rejected_count", 0),
        )
    except Exception:
        return False


class EmailTool(BaseTool):
    tool_id = "email"
    name = "Email Tool"
    description = (
        "Lee, busca y envia emails via Gmail. Tambien gestiona las reglas de "
        "auto-respuesta configurables (responder automaticamente a emails de "
        "determinados remitentes sin pedir confirmacion)."
    )
    requires_confirmation = False  # depende de la accion

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Acciones que NO requieren Google OAuth (auto-reply config).
            if action == "list_auto_reply_rules":
                return await self._list_auto_reply_rules()
            if action == "add_auto_reply_rule":
                return await self._add_auto_reply_rule(params)
            if action == "update_auto_reply_rule":
                return await self._update_auto_reply_rule(params)
            if action == "delete_auto_reply_rule":
                return await self._delete_auto_reply_rule(params)
            if action == "test_auto_reply":
                return await self._test_auto_reply(params)

            # Acciones de Gmail - requieren OAuth.
            if not google_auth.is_connected():
                return {
                    "success": False,
                    "result": None,
                    "error": (
                        "Google no esta conectado. Configura client_id/client_secret "
                        "en Settings (seccion Google) y completa el flujo OAuth."
                    ),
                }
            creds = google_auth.get_credentials()
            if not creds:
                return {
                    "success": False,
                    "result": None,
                    "error": "credenciales Google invalidas o expiradas",
                }

            handler = {
                "list_inbox": self._list_inbox,
                "list_inbox_preview": self._list_inbox_preview,
                "get_email": self._get_email,
                "search_emails": self._search_emails,
                "create_draft": self._create_draft,
                "send_email": self._send_email,
                "classify_email": self._classify_email,
            }.get(action)
            if not handler:
                return {
                    "success": False,
                    "result": None,
                    "error": f"Accion desconocida: {action}",
                }
            return await handler(creds, params)
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"{type(e).__name__}: {e}",
            }

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "list_inbox",
                "description": "Lista los ultimos N emails del inbox.",
                "requires_confirmation": False,
                "params": {
                    "max_results": "int (default 20)",
                    "label": "string (default INBOX)",
                },
            },
            {
                "id": "list_inbox_preview",
                "description": "Lista los ultimos N emails con asunto, remitente, fecha, snippet y estado leido/no leido.",
                "requires_confirmation": False,
                "params": {"max_results": "int (default 15)"},
            },
            {
                "id": "get_email",
                "description": "Obtiene el contenido completo de un email.",
                "requires_confirmation": False,
                "params": {"email_id": "string"},
            },
            {
                "id": "search_emails",
                "description": 'Busca emails con sintaxis Gmail (ej. "from:jefe@empresa.com subject:reunion").',
                "requires_confirmation": False,
                "params": {"query": "string", "max_results": "int opcional"},
            },
            {
                "id": "create_draft",
                "description": "Crea un borrador en Gmail (no se envia).",
                "requires_confirmation": False,
                "params": {
                    "to": "string",
                    "subject": "string",
                    "body": "string",
                },
            },
            {
                "id": "send_email",
                "description": "Envia un email. SIEMPRE requiere confirmacion.",
                "requires_confirmation": True,
                "params": {
                    "to": "string",
                    "subject": "string",
                    "body": "string",
                },
            },
            {
                "id": "classify_email",
                "description": "Clasifica un email con IA (urgent/follow_up/informational/spam).",
                "requires_confirmation": False,
                "params": {"email_id": "string"},
            },
            # --- Auto-reply rules (no requieren Google) ---
            {
                "id": "list_auto_reply_rules",
                "description": "Lista las reglas de auto-respuesta configuradas.",
                "requires_confirmation": False,
                "params": {},
            },
            {
                "id": "add_auto_reply_rule",
                "description": (
                    "Anade una regla de auto-respuesta. matching: sender_contains | "
                    "subject_contains | sender_domain. pattern: substring o dominio. "
                    "reply_template puede usar {sender}, {subject}, {body}."
                ),
                "requires_confirmation": False,
                "params": {
                    "name": "string (ej. 'Respuesta a jefe')",
                    "matching": "string (sender_contains | subject_contains | sender_domain)",
                    "pattern": "string (ej. '@empresa.com')",
                    "reply_template": "string (ej. 'Recibido, gracias. Te respondo pronto.')",
                    "enabled": "bool opcional (default True)",
                },
            },
            {
                "id": "update_auto_reply_rule",
                "description": "Actualiza una regla existente por id.",
                "requires_confirmation": False,
                "params": {
                    "id": "int (id de la regla)",
                    "name": "string opcional",
                    "matching": "string opcional",
                    "pattern": "string opcional",
                    "reply_template": "string opcional",
                    "enabled": "bool opcional",
                },
            },
            {
                "id": "delete_auto_reply_rule",
                "description": "Elimina una regla por id.",
                "requires_confirmation": False,
                "params": {"id": "int"},
            },
            {
                "id": "test_auto_reply",
                "description": "Comprueba si un email (sender + subject + body) matchea alguna regla. NO envia nada.",
                "requires_confirmation": False,
                "params": {
                    "sender": "string (header From)",
                    "subject": "string",
                    "body": "string",
                },
            },
        ]

    # ------------------------------------------------------------------
    # Auto-reply rules (no requieren Google)
    # ------------------------------------------------------------------

    async def _list_auto_reply_rules(self) -> Dict[str, Any]:
        from app.db.database import SessionLocal
        from app.db.models import EmailAutoReplyRule

        db = SessionLocal()
        try:
            rules = db.query(EmailAutoReplyRule).order_by(
                EmailAutoReplyRule.created_at.desc()
            ).all()
            items = []
            for r in rules:
                try:
                    emails = json.loads(r.sender_emails or "[]")
                except Exception:
                    emails = []
                try:
                    domains = json.loads(r.sender_domains or "[]")
                except Exception:
                    domains = []
                items.append({
                    "id": r.id,
                    "name": r.name,
                    # V0.7 extra (nuevo)
                    "sender_emails": emails,
                    "sender_domains": domains,
                    "action": getattr(r, "action", "auto_send"),
                    "detect_meeting_with_ia": getattr(r, "detect_meeting_with_ia", True),
                    # V0.7 legacy
                    "matching": r.matching,
                    "pattern": r.pattern,
                    "reply_template": r.reply_template,
                    # V0.7.3b (Sprint 4b): respuesta generada por IA
                    "ai_prompt": getattr(r, "ai_prompt", None),
                    "enabled": r.enabled,
                    # V0.7.3 (Sprint 4, B6): autonomia gradual
                    "autonomy": getattr(r, "autonomy", "auto") or "auto",
                    "approved_count": getattr(r, "approved_count", 0) or 0,
                    "edited_count": getattr(r, "edited_count", 0) or 0,
                    "rejected_count": getattr(r, "rejected_count", 0) or 0,
                    "can_promote": _rule_can_promote_safe(r),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                })
            return {"success": True, "result": {"rules": items, "count": len(items)}, "error": None}
        finally:
            db.close()

    async def _add_auto_reply_rule(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.db.database import SessionLocal
        from app.db.models import EmailAutoReplyRule

        name = (params.get("name") or "").strip()
        sender_emails = params.get("sender_emails") or []
        sender_domains = params.get("sender_domains") or []
        action = (params.get("action") or "auto_send").strip()
        # V0.7.3 (Sprint 4, B6): toda regla nueva nace en 'propose' salvo
        # peticion explicita. La promocion a 'auto' se gana con feedback.
        autonomy = (params.get("autonomy") or "propose").strip()
        if autonomy not in {"propose", "auto"}:
            return {"success": False, "result": None, "error": f"autonomy invalido: {autonomy!r}"}
        detect_meeting = bool(params.get("detect_meeting_with_ia", True))
        matching = params.get("matching") or "sender_contains"
        pattern = (params.get("pattern") or "").strip()
        reply_template = params.get("reply_template") or ""
        # V0.7.3b (Sprint 4b): instruccion de respuesta generada por IA
        ai_prompt = (params.get("ai_prompt") or "").strip() or None
        enabled = bool(params.get("enabled", True))

        if not name:
            return {"success": False, "result": None, "error": "falta parametro: name"}
        if action not in {"auto_send", "create_draft", "alert_only"}:
            return {
                "success": False,
                "result": None,
                "error": f"action invalido: {action!r}. Valores: auto_send, create_draft, alert_only",
            }
        if matching and matching not in VALID_MATCHINGS:
            return {
                "success": False,
                "result": None,
                "error": f"matching invalido: {matching!r}. Valores: {sorted(VALID_MATCHINGS)}",
            }
        has_emails = isinstance(sender_emails, list) and any(e.strip() for e in sender_emails)
        has_domains = isinstance(sender_domains, list) and any(d.strip() for d in sender_domains)
        has_pattern = bool(pattern)
        if not (has_emails or has_domains or has_pattern):
            return {
                "success": False,
                "result": None,
                "error": "debes indicar al menos un email, dominio o patron",
            }
        # V0.7 extra (FIX): la plantilla es opcional si detect_meeting_with_ia=True
        # porque la IA genera la respuesta completa para reuniones.
        # Solo es obligatoria si NO se detectan reuniones con IA.
        if not reply_template.strip() and not detect_meeting and not ai_prompt:
            return {
                "success": False,
                "result": None,
                "error": "hace falta reply_template o ai_prompt si detect_meeting_with_ia=False",
            }

        emails_clean = [e.strip().lower() for e in (sender_emails or []) if isinstance(e, str) and e.strip()]
        domains_clean = [d.strip().lower() for d in (sender_domains or []) if isinstance(d, str) and d.strip()]

        db = SessionLocal()
        try:
            rule = EmailAutoReplyRule(
                autonomy=autonomy,
                ai_prompt=ai_prompt,
                name=name,
                sender_emails=json.dumps(emails_clean),
                sender_domains=json.dumps(domains_clean),
                action=action,
                detect_meeting_with_ia=detect_meeting,
                matching=matching or "sender_contains",
                pattern=pattern or "*",
                reply_template=reply_template,
                enabled=enabled,
            )
            db.add(rule)
            db.commit()
            db.refresh(rule)
            return {
                "success": True,
                "result": {"id": rule.id, "name": rule.name, "created": True},
                "error": None,
            }
        finally:
            db.close()

    async def _update_auto_reply_rule(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.db.database import SessionLocal
        from app.db.models import EmailAutoReplyRule

        rule_id = params.get("id")
        if not rule_id:
            return {"success": False, "result": None, "error": "falta parametro: id"}
        try:
            rule_id = int(rule_id)
        except (TypeError, ValueError):
            return {"success": False, "result": None, "error": "id debe ser int"}

        db = SessionLocal()
        try:
            rule = db.query(EmailAutoReplyRule).filter(EmailAutoReplyRule.id == rule_id).first()
            if not rule:
                return {"success": False, "result": None, "error": f"regla no encontrada: id={rule_id}"}

            if "name" in params and params["name"]:
                rule.name = params["name"]
            if "sender_emails" in params:
                emails = [e.strip().lower() for e in params["sender_emails"] if isinstance(e, str) and e.strip()]
                rule.sender_emails = json.dumps(emails)
            if "sender_domains" in params:
                domains = [d.strip().lower() for d in params["sender_domains"] if isinstance(d, str) and d.strip()]
                rule.sender_domains = json.dumps(domains)
            if "action" in params:
                if params["action"] not in {"auto_send", "create_draft", "alert_only"}:
                    return {
                        "success": False,
                        "result": None,
                        "error": f"action invalido: {params['action']!r}",
                    }
                rule.action = params["action"]
            if "detect_meeting_with_ia" in params:
                rule.detect_meeting_with_ia = bool(params["detect_meeting_with_ia"])
            # V0.7.3b (Sprint 4b): instruccion de respuesta IA ("" la borra)
            if "ai_prompt" in params:
                val = (params["ai_prompt"] or "").strip()
                rule.ai_prompt = val or None
            # V0.7.3 (Sprint 4, B6): promocion/degradacion manual de autonomia
            if "autonomy" in params:
                if params["autonomy"] not in {"propose", "auto"}:
                    return {
                        "success": False,
                        "result": None,
                        "error": f"autonomy invalido: {params['autonomy']!r}",
                    }
                rule.autonomy = params["autonomy"]
            if "matching" in params:
                if params["matching"] and params["matching"] not in VALID_MATCHINGS:
                    return {
                        "success": False,
                        "result": None,
                        "error": f"matching invalido: {params['matching']!r}",
                    }
                rule.matching = params["matching"]
            if "pattern" in params and params["pattern"]:
                rule.pattern = params["pattern"]
            if "reply_template" in params and params["reply_template"]:
                rule.reply_template = params["reply_template"]
            if "enabled" in params:
                rule.enabled = bool(params["enabled"])
            rule.updated_at = datetime.utcnow()
            db.commit()
            return {"success": True, "result": {"id": rule.id, "updated": True}, "error": None}
        finally:
            db.close()

    async def _delete_auto_reply_rule(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from app.db.database import SessionLocal
        from app.db.models import EmailAutoReplyRule

        rule_id = params.get("id")
        if not rule_id:
            return {"success": False, "result": None, "error": "falta parametro: id"}
        try:
            rule_id = int(rule_id)
        except (TypeError, ValueError):
            return {"success": False, "result": None, "error": "id debe ser int"}

        db = SessionLocal()
        try:
            rule = db.query(EmailAutoReplyRule).filter(EmailAutoReplyRule.id == rule_id).first()
            if not rule:
                return {"success": False, "result": None, "error": f"regla no encontrada: id={rule_id}"}
            db.delete(rule)
            db.commit()
            return {"success": True, "result": {"id": rule_id, "deleted": True}, "error": None}
        finally:
            db.close()

    async def _test_auto_reply(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Comprueba si un email matchea alguna regla. NO envia nada.
        Util para que el chat pruebe si una regla funcionara sin enviar.
        """
        from app.db.database import SessionLocal
        from app.db.models import EmailAutoReplyRule

        sender = params.get("sender", "")
        subject = params.get("subject", "")
        body = params.get("body", "")

        db = SessionLocal()
        try:
            rules = db.query(EmailAutoReplyRule).filter(EmailAutoReplyRule.enabled == True).all()  # noqa: E712
            matches = []
            for rule in rules:
                if _rule_matches(rule, sender, subject):
                    matches.append({
                        "rule_id": rule.id,
                        "name": rule.name,
                        "matching": rule.matching,
                        "pattern": rule.pattern,
                        "reply_text": _render_template(rule.reply_template, sender, subject, body),
                    })
            return {
                "success": True,
                "result": {
                    "matches": matches,
                    "count": len(matches),
                    "would_auto_reply": len(matches) > 0,
                },
                "error": None,
            }
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Gmail (requieren OAuth)
    # ------------------------------------------------------------------

    async def _list_inbox(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        from googleapiclient.discovery import build

        max_results = int(params.get("max_results", 20))
        max_results = max(1, min(max_results, 100))
        label = params.get("label", "INBOX")

        def _do():
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            return service.users().messages().list(
                userId="me",
                labelIds=[label],
                maxResults=max_results,
            ).execute()

        result = await asyncio_run_sync(_do)
        messages = result.get("messages", [])
        return {
            "success": True,
            "result": {
                "count": len(messages),
                "messages": [{"id": m["id"], "thread_id": m.get("threadId")} for m in messages],
            },
            "error": None,
        }

    async def _list_inbox_preview(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        """V0.7.1 (Fase 4b): lista los ultimos emails del inbox con metadatos
        (asunto, remitente, fecha, snippet) y si estan sin leer (label UNREAD).
        Pensado para mostrar la bandeja de entrada en la UI del Email Assistant."""
        from googleapiclient.discovery import build

        max_results = int(params.get("max_results", 15))
        max_results = max(1, min(max_results, 50))

        def _do():
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            listing = service.users().messages().list(
                userId="me", labelIds=["INBOX"], maxResults=max_results
            ).execute()
            ids = [m["id"] for m in listing.get("messages", [])]
            out = []
            for mid in ids:
                msg = service.users().messages().get(
                    userId="me", id=mid, format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                ).execute()
                headers = {
                    h["name"].lower(): h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }
                out.append({
                    "id": mid,
                    "subject": headers.get("subject", "(sin asunto)"),
                    "from": headers.get("from", ""),
                    "date": headers.get("date", ""),
                    "snippet": msg.get("snippet", ""),
                    "unread": "UNREAD" in msg.get("labelIds", []),
                })
            return out

        items = await asyncio_run_sync(_do)
        return {
            "success": True,
            "result": {"count": len(items), "items": items},
            "error": None,
        }

    async def _get_email(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        from googleapiclient.discovery import build

        email_id = params.get("email_id")
        if not email_id:
            return {"success": False, "result": None, "error": "falta parametro: email_id"}

        def _do():
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            return service.users().messages().get(
                userId="me", id=email_id, format="full"
            ).execute()

        msg = await asyncio_run_sync(_do)
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        body_text = _extract_body_text(msg.get("payload", {}))
        return {
            "success": True,
            "result": {
                "id": email_id,
                "subject": headers.get("subject", ""),
                "from": headers.get("from", ""),
                "to": headers.get("to", ""),
                "date": headers.get("date", ""),
                "snippet": msg.get("snippet", ""),
                "body_text": body_text[:5000],
            },
            "error": None,
        }

    async def _search_emails(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        from googleapiclient.discovery import build

        query = params.get("query", "")
        if not query:
            return {"success": False, "result": None, "error": "falta parametro: query"}
        max_results = int(params.get("max_results", 20))
        max_results = max(1, min(max_results, 100))

        def _do():
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            return service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()

        result = await asyncio_run_sync(_do)
        return {
            "success": True,
            "result": {
                "count": len(result.get("messages", [])),
                "messages": [{"id": m["id"]} for m in result.get("messages", [])],
            },
            "error": None,
        }

    async def _create_draft(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        from googleapiclient.discovery import build

        to = params.get("to", "")
        subject = params.get("subject", "")
        body = params.get("body", "")
        if not to or not subject:
            return {
                "success": False,
                "result": None,
                "error": "faltan parametros: to y subject son obligatorios",
            }

        def _do():
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            msg = MIMEText(body)
            msg["to"] = to
            msg["subject"] = subject
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            return service.users().drafts().create(
                userId="me", body={"message": {"raw": raw}}
            ).execute()

        draft = await asyncio_run_sync(_do)
        return {
            "success": True,
            "result": {"draft_id": draft.get("id"), "message_id": draft.get("message", {}).get("id")},
            "error": None,
        }

    async def _send_email(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        from googleapiclient.discovery import build

        to = params.get("to", "")
        subject = params.get("subject", "")
        body = params.get("body", "")
        if not to or not subject:
            return {
                "success": False,
                "result": None,
                "error": "faltan parametros: to y subject son obligatorios",
            }

        def _do():
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            msg = MIMEText(body)
            msg["to"] = to
            msg["subject"] = subject
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            return service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()

        sent = await asyncio_run_sync(_do)
        return {
            "success": True,
            "result": {"message_id": sent.get("id"), "thread_id": sent.get("threadId")},
            "error": None,
        }

    async def _classify_email(self, creds, params: Dict[str, Any]) -> Dict[str, Any]:
        email_id = params.get("email_id")
        if not email_id:
            return {"success": False, "result": None, "error": "falta parametro: email_id"}

        # Primero obtenemos el email
        email_resp = await self._get_email(creds, {"email_id": email_id})
        if not email_resp["success"]:
            return email_resp
        email = email_resp["result"]

        # Luego pedimos a la IA que clasifique
        from app.ai.ai_manager import ai_manager

        prompt = (
            "Clasifica este email en UNA de estas categorias: "
            "meeting, urgent, follow_up, informational, spam.\n"
            "- meeting: propone una reunion, cita, quedada, llamada, evento en fecha concreta\n"
            "- urgent: requiere accion inmediata pero NO es una reunion\n"
            "- follow_up: pide respuesta o seguimiento\n"
            "- informational: solo informa, no requiere accion\n"
            "- spam: publicidad, phishing o no solicitado\n"
            "Responde SOLO con JSON valido: {\"category\": \"...\", \"reason\": \"...\"}\n\n"
            f"De: {email.get('from', '')}\n"
            f"Asunto: {email.get('subject', '')}\n"
            f"Cuerpo (primeros 500 chars): {(email.get('body_text') or '')[:500]}"
        )
        try:
            ai_resp = await ai_manager.chat(
                message=prompt,
                system_prompt="Eres un clasificador de emails. Responde SOLO con JSON valido.",
            )
            text = ai_resp.get("response", "")
            # Intentar parsear el JSON de la respuesta
            import re as _re
            match = _re.search(r"\{[^{}]+\}", text)
            if match:
                classification = json.loads(match.group(0))
            else:
                classification = {"category": "informational", "reason": "no se pudo parsear la respuesta"}
            return {
                "success": True,
                "result": {
                    "email_id": email_id,
                    "classification": classification,
                },
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "result": None,
                "error": f"error clasificando con IA: {type(e).__name__}: {e}",
            }


# ----------------------------------------------------------------------
# Helpers (module-level, no necesitan self)
# ----------------------------------------------------------------------

import asyncio as _asyncio


def _rule_matches(rule, sender: str, subject: str) -> bool:
    """Devuelve True si el email (sender, subject) matchea la regla.

    V0.7 extra: matching multi-fuente:
      1) sender_emails (lista exacta de emails, case-insensitive)
      2) sender_domains (lista de dominios, case-insensitive)
      3) matching+pattern legacy (compatibilidad V0.7 original)

    Si sender_emails y sender_domains estan vacios pero matching+pattern
    tienen valor, se usa el matching legacy.
    """
    if not rule.enabled:
        return False

    sender_email = _extract_email_address(sender)
    sender_domain = _extract_domain(sender)

    # V0.7 extra: matching por listas (B-01: OR independiente entre
    # sender_emails y sender_domains). Antes se hacia return False al no
    # matchear sender_emails, sin llegar a comprobar sender_domains.
    try:
        emails_list = json.loads(rule.sender_emails or "[]")
    except (json.JSONDecodeError, TypeError):
        emails_list = []
    try:
        domains_list = json.loads(rule.sender_domains or "[]")
    except (json.JSONDecodeError, TypeError):
        domains_list = []

    has_emails = isinstance(emails_list, list) and bool(emails_list)
    has_domains = isinstance(domains_list, list) and bool(domains_list)

    if has_emails or has_domains:
        matched = False
        if has_emails:
            matched = matched or any(
                e and e.strip().lower() == sender_email for e in emails_list
            )
        if has_domains:
            matched = matched or any(
                d and d.strip().lower() == sender_domain for d in domains_list
            )
        return matched

    # V0.7 legacy: matching+pattern
    if rule.matching and rule.pattern:
        if rule.matching == "sender_contains":
            return rule.pattern.lower() in sender.lower()
        if rule.matching == "subject_contains":
            return rule.pattern.lower() in subject.lower()
        if rule.matching == "sender_domain":
            return rule.pattern.lower() in sender_domain or sender_domain == rule.pattern.lower()

    return False


def check_auto_reply_match(sender: str, subject: str, body: str = "") -> Optional[Dict[str, Any]]:
    """Helper publico: dado un email, devuelve la primera regla que matchea
    y el texto de respuesta ya renderizado. None si no hay match.

    Lo usa el chat/AgentManager para responder automaticamente cuando el
    usuario ha configurado reglas para ciertos remitentes.
    """
    from app.db.database import SessionLocal
    from app.db.models import EmailAutoReplyRule

    db = SessionLocal()
    try:
        rules = db.query(EmailAutoReplyRule).filter(
            EmailAutoReplyRule.enabled == True  # noqa: E712
        ).order_by(EmailAutoReplyRule.created_at.asc()).all()
        for rule in rules:
            if _rule_matches(rule, sender, subject):
                return {
                    "rule_id": rule.id,
                    "name": rule.name,
                    "matching": rule.matching,
                    "pattern": rule.pattern,
                    "action": getattr(rule, "action", "auto_send"),
                    "reply_text": _render_template(rule.reply_template, sender, subject, body),
                    # V0.7.3b (Sprint 4b): si hay ai_prompt, el caller debe
                    # generar la respuesta con IA y usar reply_text de fallback
                    "ai_prompt": getattr(rule, "ai_prompt", None),
                    "detect_meeting_with_ia": getattr(rule, "detect_meeting_with_ia", True),
                }
        return None
    finally:
        db.close()


async def asyncio_run_sync(fn):
    """Ejecuta una funcion sync en el thread por defecto para no bloquear el loop."""
    return await _asyncio.get_event_loop().run_in_executor(None, fn)


def _extract_body_text(payload: Dict[str, Any]) -> str:
    """Extrae el texto plano del body de un email de Gmail."""
    if payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        try:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        except Exception:
            return ""
    parts = payload.get("parts", []) or []
    for part in parts:
        if part.get("mimeType", "").startswith("text/plain"):
            data = part.get("body", {}).get("data")
            if data:
                try:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                except Exception:
                    return ""
        if part.get("parts"):
                inner = _extract_body_text(part)
                if inner:
                    return inner
    return ""


# ----------------------------------------------------------------------
# Helpers para propuestas de reunion (V0.7 extra)
# ----------------------------------------------------------------------

import json as _json
from datetime import datetime as _dt, timedelta as _td


async def extract_meeting_datetime(subject: str, body: str) -> Optional[str]:
    """V0.7 extra: usa la IA para extraer la fecha/hora propuesta de una reunion.

    Devuelve un ISO datetime string o None si no se puede extraer.
    Estrategia:
      1) Pedirle a la IA que identifique la fecha/hora y devuelva ISO 8601
      2) Fallback: regex basica que busca "manana", "pasado manana",
         "el lunes", "el martes", dias de la semana, formatos dd/mm/yyyy
    """
    try:
        from app.ai.ai_manager import ai_manager
        today = _dt.now()
        prompt = (
            f"Hoy es {today.strftime('%Y-%m-%d %A')}.\n"
            "De este email, extrae la fecha y hora EXACTA que propone el "
            "remitente para una reunion. Si no hay reunion propuesta o "
            "no se puede deducir fecha concreta, responde null.\n"
            "Responde SOLO con un JSON valido: "
            '{"datetime": "YYYY-MM-DDTHH:MM:SS", "confidence": 0.0-1.0, "text": "fragmento relevante"}\n\n'
            f"Asunto: {subject or '(sin asunto)'}\n\n"
            f"Cuerpo: {(body or '')[:1500]}"
        )
        ai_resp = await ai_manager.chat(
            message=prompt,
            system_prompt="Eres un extractor de fechas. Responde SOLO con JSON valido.",
        )
        text = ai_resp.get("response", "")
        import re as _re
        m = _re.search(r"\{[^{}]+\}", text)
        if m:
            data = _json.loads(m.group(0))
            dt_str = data.get("datetime")
            if dt_str and dt_str != "null":
                return dt_str
    except Exception as e:
        print(f"[email_tool] extract_meeting_datetime IA fallo: {e}")
    # Fallback regex
    return _extract_datetime_regex(subject or "", body or "")


def _parse_hour_minute(text: str):
    """Extrae (hora, minuto) de frases tipo 'a las 11', '11h', '11:30',
    'a las 4 de la tarde'. Devuelve None si no hay hora explicita."""
    import re as _re
    m = _re.search(r"a\s+las?\s+(\d{1,2})(?::(\d{2}))?\s*h?", text)
    if not m:
        m = _re.search(r"\b(\d{1,2}):(\d{2})\b", text)      # 11:30
    if not m:
        m = _re.search(r"\b(\d{1,2})\s*h\b", text)          # 11h
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2)) if (m.lastindex and m.lastindex >= 2 and m.group(2)) else 0
    # Franja horaria: 'de la tarde' / 'de la noche' -> +12 si viene en formato 12h
    if ("tarde" in text or "noche" in text) and hour < 12:
        hour += 12
    if hour == 24:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute


# Meses en espanol para fechas tipo "2 de julio"
_SPANISH_MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}


def _extract_datetime_regex(subject: str, body: str) -> Optional[str]:
    """Fallback sin IA: busca palabras clave ('manana', dias de semana,
    '2 de julio', dd/mm) y la hora explicita ('a las 11', '11h', '11:30').
    Devuelve ISO datetime. Si no hay hora explicita, usa 10:00 por defecto."""
    import re as _re
    text = f"{subject}\n{body}".lower()
    hm = _parse_hour_minute(text)
    base_hour, base_minute = hm if hm else (10, 0)
    today = _dt.now().replace(hour=base_hour, minute=base_minute, second=0, microsecond=0)

    # manana / pasado manana
    if "pasado mañana" in text or "pasado manana" in text:
        return (today + _td(days=2)).isoformat()
    if "mañana" in text or "manana" in text:
        return (today + _td(days=1)).isoformat()
    if "hoy" in text:
        return today.isoformat()
    # dias de semana
    weekdays = {
        "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
        "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6,
    }
    for wd, target in weekdays.items():
        if wd in text:
            days_ahead = (target - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (today + _td(days=days_ahead)).isoformat()
    # fecha con mes en texto: "2 de julio" / "2 julio"
    m = _re.search(r"\b(\d{1,2})\s+(?:de\s+)?(" + "|".join(_SPANISH_MONTHS) + r")\b", text)
    if m:
        try:
            d = int(m.group(1))
            mo = _SPANISH_MONTHS[m.group(2)]
            y = today.year
            candidate = _dt(y, mo, d, base_hour, base_minute)
            # Si la fecha ya paso este ano, asumimos el ano que viene.
            if candidate.date() < _dt.now().date():
                candidate = _dt(y + 1, mo, d, base_hour, base_minute)
            return candidate.isoformat()
        except ValueError:
            pass
    # formato dd/mm/yyyy
    m = _re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-]?(\d{2,4})?", text)
    if m:
        try:
            d, mo = int(m.group(1)), int(m.group(2))
            y = int(m.group(3)) if m.group(3) else today.year
            if y < 100:
                y += 2000
            return _dt(y, mo, d, base_hour, base_minute).isoformat()
        except ValueError:
            pass
    return None


async def generate_meeting_reschedule_reply(
    sender: str,
    subject: str,
    original_body: str,
    original_proposed_iso: str,
    new_proposed_iso: str,
) -> str:
    """V0.7 extra: usa la IA para redactar una respuesta amable proponiendo
    la nueva fecha. NO usa plantilla - es texto generado por IA."""
    try:
        from app.ai.ai_manager import ai_manager
        prompt = (
            f"Redacta una respuesta breve, profesional y amable (en espanol) a "
            f"este email:\n\n"
            f"De: {sender}\n"
            f"Asunto: {subject}\n"
            f"Cuerpo: {original_body[:1000]}\n\n"
            f"El remitente propuso: {original_proposed_iso}\n"
            f"NO PUEDO aceptar esa fecha porque ya tengo compromiso.\n"
            f"Mi contrapropuesta es: {new_proposed_iso}\n\n"
            "Instrucciones:\n"
            "- Saluda al remitente por su nombre si aparece\n"
            "- Agradece la propuesta\n"
            "- Indica amablemente que esa fecha ya tengo compromiso\n"
            "- Propone la nueva fecha\n"
            "- Pide confirmacion\n"
            "- NO uses saludos demasiado formales\n"
            "- Maximo 5 lineas\n"
            "- Solo el cuerpo del email, sin asunto"
        )
        ai_resp = await ai_manager.chat(
            message=prompt,
            system_prompt=(
                "Eres Aithera, un asistente personal de IA. "
                "Redactas emails breves, amables y profesionales en espanol."
            ),
        )
        return ai_resp.get("response", "").strip()
    except Exception as e:
        # Fallback si IA falla
        print(f"[email_tool] generate_meeting_reschedule_reply IA fallo: {e}")
        return (
            f"Hola,\n\n"
            f"Gracias por tu mensaje. Lamentablemente el {original_proposed_iso} "
            f"ya tengo un compromiso previo.\n\n"
            f"Te propongo el {new_proposed_iso} en su lugar. "
            f"Confirmame si te viene bien y lo bloqueo.\n\n"
            f"Un saludo,\nAithera"
        )


async def detect_meeting_confirmation(sender_email: str, subject: str, body: str) -> bool:
    """V0.7 extra: usa la IA para detectar si un email confirma una reunion."""
    try:
        from app.ai.ai_manager import ai_manager
        prompt = (
            f"Este email es respuesta a una propuesta de reunion. "
            f"Determina si CONFIRMA la fecha propuesta o si la rechaza/propone otra.\n"
            f"Responde SOLO con JSON: {{\"confirmed\": true/false, \"new_datetime\": \"YYYY-MM-DDTHH:MM:SS o null\", \"reason\": \"...\"}}\n\n"
            f"De: {sender_email}\n"
            f"Asunto: {subject}\n"
            f"Cuerpo: {body[:1000]}"
        )
        ai_resp = await ai_manager.chat(
            message=prompt,
            system_prompt="Eres un clasificador. Responde SOLO con JSON valido.",
        )
        import re as _re
        m = _re.search(r"\{[^{}]+\}", ai_resp.get("response", ""))
        if m:
            data = _json.loads(m.group(0))
            return bool(data.get("confirmed")), data.get("new_datetime"), data.get("reason", "")
    except Exception as e:
        print(f"[email_tool] detect_meeting_confirmation IA fallo: {e}")
    return False, None, "IA no pudo clasificar"


async def generate_meeting_accept_reply(
    sender: str,
    subject: str,
    original_body: str,
    confirmed_datetime_iso: str,
) -> str:
    """V0.7 extra (FIX): usa IA para redactar una respuesta ACEPTANDO una reunion.

    Se usa cuando el email propone una reunion y el calendario esta libre.
    La IA genera un email corto y amable confirmando la fecha.
    """
    try:
        from app.ai.ai_manager import ai_manager
        prompt = (
            f"Redacta una respuesta breve, profesional y amable (en espanol) confirmando "
            f"una reunion propuesta:\n\n"
            f"De: {sender}\n"
            f"Asunto: {subject}\n"
            f"Cuerpo: {original_body[:1000]}\n\n"
            f"Fecha y hora confirmadas: {confirmed_datetime_iso}\n\n"
            "Instrucciones:\n"
            "- Saluda al remitente por su nombre si aparece\n"
            "- Confirma la reunion\n"
            "- Agradece\n"
            "- Si el email menciona lugar, confirmalo; si no, no asumas nada\n"
            "- Maximo 4 lineas\n"
            "- Solo el cuerpo del email, sin asunto"
        )
        ai_resp = await ai_manager.chat(
            message=prompt,
            system_prompt=(
                "Eres Aithera, un asistente personal de IA. "
                "Redactas emails breves, amables y profesionales en espanol."
            ),
        )
        return ai_resp.get("response", "").strip()
    except Exception as e:
        print(f"[email_tool] generate_meeting_accept_reply IA fallo: {e}")
        return (
            f"Hola,\n\n"
            f"Confirmo nuestra reunion para el {confirmed_datetime_iso}. "
            f"Nos vemos alli.\n\n"
            f"Un saludo,\nAithera"
        )


# ----------------------------------------------------------------------
# V0.7.1 (Fase 4b, patron AMD GAIA): deteccion de reuniones en dos etapas
#   1) heuristica determinista (0 coste, sin LLM)
#   2) LLM triage (solo si la heuristica es ambigua)
# ----------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class MeetingDetection:
    """Resultado tipado e inmutable de detectar una propuesta de reunion.

    Sustituye al dict arbitrario que devolvia antes detect_meeting_proposal().
    Para serializar en una respuesta HTTP: dataclasses.asdict(detection).
    """
    is_meeting_request: bool
    confidence: Literal["high", "low", "none"]
    signals: List[str]          # keywords/patrones que activaron la deteccion
    reason: str                 # explicacion legible
    datetime_iso: Optional[str] = None
    method: Literal["heuristic", "llm", "none"] = "none"


# Frases de alta confianza (es + en) que por si solas indican propuesta de reunion.
STRONG_MEETING_PHRASES = [
    "are you free", "schedule a call", "let's meet", "lets meet",
    "set up a meeting", "invite you to", "calendar invite",
    "quieres quedar", "podemos quedar", "podemos vernos", "podemos llamar",
    "organizamos una reunion", "organizamos una reunión",
    "te viene bien", "tienes hueco",
]

# Palabras que sugieren reunion pero necesitan ademas una fecha/hora para ser
# consideradas propuesta de alta confianza.
MEETING_KEYWORDS = [
    "reunion", "reunión", "meeting", "quedamos", "quedar", "juntarnos",
    "encontrarnos", "nos vemos", "vernos", "quedada", "cita", "appointment",
    "agendar", "agenda", "llamarte", "llamada", "videollamada", "video llamada",
    "reservar", "reservamos", "book", "booking",
]


def _heuristic_meeting_detection(subject: str, body: str) -> MeetingDetection:
    """Deteccion determinista sin LLM. Rapida, 0 coste en tokens.

    Alta confianza si hay una frase de propuesta clara, o si hay una palabra de
    reunion junto a una fecha/hora concreta. Si las senales son ambiguas,
    devuelve confidence='low' para que el orquestador consulte al LLM.
    """
    text = f"{subject or ''} {body or ''}".lower()
    strong = [p for p in STRONG_MEETING_PHRASES if p in text]
    keywords = [k for k in MEETING_KEYWORDS if k in text]
    # has_date: reutilizamos el extractor (mañana, dia de semana, '2 de julio',
    # dd/mm, 'a las 11', '11h', '11:30'...). Si extrae algo, hay fecha/hora.
    date_iso = _extract_datetime_regex(subject or "", body or "")
    has_date = date_iso is not None
    signals = strong + keywords + (["patron_fecha_hora"] if has_date else [])

    # Alta confianza: propuesta clara, o (palabra de reunion + fecha/hora).
    if strong or (keywords and has_date):
        return MeetingDetection(
            is_meeting_request=True,
            confidence="high",
            signals=signals,
            reason="heuristica determinista",
            datetime_iso=date_iso,
            method="heuristic",
        )
    # Senales ambiguas (solo palabra, o solo fecha): que decida el LLM.
    if signals:
        return MeetingDetection(
            is_meeting_request=False,
            confidence="low",
            signals=signals,
            reason="senales ambiguas, requiere LLM",
            datetime_iso=date_iso,
            method="heuristic",
        )
    return MeetingDetection(
        is_meeting_request=False,
        confidence="none",
        signals=[],
        reason="sin senales de reunion",
        method="heuristic",
    )


async def _llm_meeting_detection(subject: str, body: str) -> MeetingDetection:
    """Deteccion via LLM. Mas precisa para casos ambiguos.

    Fail-loud: si el LLM no esta disponible o falla, devolvemos confidence='none'
    con un reason explicito (no asumimos silenciosamente que no es reunion).
    """
    try:
        from app.ai.ai_manager import ai_manager
        today = _dt.now()
        prompt = (
            f"Hoy es {today.strftime('%Y-%m-%d %A, %H:%M')}.\n\n"
            "Lee este email y determina si el remitente esta PROPONIENDO una "
            "reunion, cita, quedada, llamada, evento o quedada fisica/virtual "
            "para una FECHA CONCRETA (no vaga como 'cuando puedas').\n\n"
            "Responde SOLO con JSON valido:\n"
            '{"is_meeting_proposal": true/false, '
            '"datetime_iso": "YYYY-MM-DDTHH:MM:SS o null", '
            '"confidence": 0.0-1.0, '
            '"reason": "frase corta explicando porque"}\n\n'
            f"Asunto: {subject or '(sin asunto)'}\n\n"
            f"Cuerpo: {(body or '')[:2000]}"
        )
        ai_resp = await ai_manager.chat(
            message=prompt,
            system_prompt=(
                "Eres un asistente experto en detectar propuestas de reunion en emails. "
                "Responde SOLO con JSON valido. Si no hay fecha concreta, "
                "is_meeting_proposal=false."
            ),
        )
        m = re.search(r"\{[^{}]+\}", ai_resp.get("response", ""))
        if m:
            data = _json.loads(m.group(0))
            is_meeting = bool(data.get("is_meeting_proposal", False))
            dt_iso = data.get("datetime_iso")
            if dt_iso == "null":
                dt_iso = None
            conf_raw = float(data.get("confidence", 0) or 0)
            # Mapear el score 0..1 del LLM a nuestra escala discreta.
            if not is_meeting:
                confidence = "none"
            elif conf_raw >= 0.6:
                confidence = "high"
            else:
                confidence = "low"
            return MeetingDetection(
                is_meeting_request=is_meeting,
                confidence=confidence,
                signals=["llm"],
                reason=data.get("reason", ""),
                datetime_iso=dt_iso,
                method="llm",
            )
    except Exception as e:
        print(f"[email_tool] _llm_meeting_detection fallo: {e}")
        return MeetingDetection(
            is_meeting_request=False,
            confidence="none",
            signals=[],
            reason=f"LLM no disponible: {type(e).__name__}",
            method="llm",
        )
    # LLM respondio pero sin JSON parseable.
    return MeetingDetection(
        is_meeting_request=False,
        confidence="none",
        signals=[],
        reason="LLM no devolvio JSON valido",
        method="llm",
    )


async def detect_meeting_proposal(subject: str, body: str) -> MeetingDetection:
    """V0.7.1 (Fase 4b, patron GAIA): orquesta heuristica + LLM.

    Si la heuristica determinista tiene confianza alta, evitamos la llamada al
    LLM (ahorro de tokens y menor latencia). Si es ambigua, delegamos en el LLM.
    Devuelve siempre un MeetingDetection tipado.
    """
    fast = _heuristic_meeting_detection(subject, body)
    if fast.confidence == "high":
        return fast
    return await _llm_meeting_detection(subject, body)