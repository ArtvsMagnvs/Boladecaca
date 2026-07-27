# Codex CLI — instalación y login asistidos desde la UI (2026-07-24)
#
# Objetivo (petición del usuario): que CUALQUIER usuario que instale Aithera
# pueda activar Codex con un botón, sin tocar la terminal. Dos piezas:
#
#   1) INSTALAR con un botón — `npm install -g @openai/codex`, en un hilo con la
#      salida capturada y estados idle/installing/done/failed (MISMO patrón que
#      la instalación de Kokoro en voice.py y de los modelos de Ollama). Se usa
#      npm (el paquete OFICIAL y firmado de OpenAI en el registro de npm), no el
#      instalador `curl … | sh` (ejecutar un script remoto es justo lo que se
#      evita). Si no hay Node/npm, se dice claramente y se ofrece la guía.
#
#   2) INICIAR SESIÓN con un botón — lanza `codex login`, que abre el NAVEGADOR
#      del usuario para que inicie sesión con su cuenta de ChatGPT. Aithera NUNCA
#      introduce las credenciales (eso lo hace el usuario en su navegador, igual
#      que el OAuth de Google que ya existe): auto-rellenar la contraseña no es
#      posible ni permitido. Se detecta el éxito por la aparición de
#      `~/.codex/auth.json` (el almacén de credenciales documentado) y/o el exit 0
#      del proceso. Si el navegador no se abre solo, se surface la URL para que el
#      usuario la abra a mano.
#
# La guía rápida y realista (comandos exactos) vive en la UI como fallback SIEMPRE
# visible, por si algo falla o el usuario prefiere hacerlo en su terminal.
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.logging_config import get_system_logger

logger = get_system_logger("codex.setup")

router = APIRouter(prefix="/codex", tags=["Codex"])

# Estado en memoria de los procesos lanzados desde la UI (mismo enfoque que
# _KOKORO_INSTALL en voice.py). No necesita BD: es efímero por sesión del backend.
_INSTALL: dict = {"status": "idle", "detail": None}   # idle|installing|done|failed
_LOGIN: dict = {"status": "idle", "detail": None, "url": None}  # idle|running|done|failed


def _find_codex() -> str | None:
    return shutil.which("codex")


def _find_npm() -> str | None:
    return shutil.which("npm")


def _auth_file() -> Path:
    """El almacén de credenciales documentado por OpenAI (learn.chatgpt.com/docs/auth):
    `~/.codex/auth.json`. Puede vivir también en el keyring del SO, así que su
    AUSENCIA no prueba "sin sesión" — pero su presencia sí es señal fiable de login."""
    return Path(os.path.expanduser("~")) / ".codex" / "auth.json"


def _authenticated() -> bool:
    try:
        return _auth_file().is_file()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Instalación (npm)
# ---------------------------------------------------------------------------
def _install_worker() -> None:
    try:
        if _find_npm() is None:
            _INSTALL.update(
                status="failed",
                detail="No se encontró npm (Node.js). Instala Node.js desde nodejs.org y "
                       "vuelve a pulsar Instalar, o instala Codex a mano (ver la guía).",
            )
            return
        _INSTALL.update(status="installing", detail="Instalando @openai/codex con npm…")
        # Comando CONSTANTE (sin entrada del usuario) → shell=True es seguro y
        # además resuelve el shim `npm.cmd`/`codex.cmd` en Windows. Paquete oficial.
        r = subprocess.run(
            "npm install -g @openai/codex",
            shell=True, capture_output=True, text=True, timeout=1800,
        )
        if r.returncode != 0 or _find_codex() is None:
            tail = (r.stderr or r.stdout or "").strip()[-500:]
            _INSTALL.update(status="failed", detail=tail or f"npm terminó con código {r.returncode}")
            return
        _INSTALL.update(status="done", detail=None)
    except subprocess.TimeoutExpired:
        _INSTALL.update(status="failed", detail="La instalación tardó demasiado (timeout).")
    except Exception as e:
        _INSTALL.update(status="failed", detail=f"{type(e).__name__}: {e}")


@router.post("/install")
def install() -> JSONResponse:
    """Lanza `npm install -g @openai/codex` en un hilo (salida/estado en /status).
    Idempotente: si ya está instalado o en curso, lo dice sin duplicar."""
    if _find_codex() is not None:
        return JSONResponse(content={"started": False, "message": "Codex ya está instalado."})
    if _INSTALL["status"] == "installing":
        return JSONResponse(content={"started": False, "message": "Ya hay una instalación en curso."})
    _INSTALL.update(status="installing", detail=None)
    threading.Thread(target=_install_worker, daemon=True).start()
    return JSONResponse(content={"started": True, "message": "Instalando Codex…"})


# ---------------------------------------------------------------------------
# Login (codex login — el usuario inicia sesión en su navegador)
# ---------------------------------------------------------------------------
def _login_worker() -> None:
    try:
        if _find_codex() is None:
            _LOGIN.update(status="failed", detail="Codex no está instalado. Pulsa Instalar primero.")
            return
        _LOGIN.update(status="running", detail="Abriendo el navegador para iniciar sesión…", url=None)
        # `codex login` abre el navegador (OAuth con ChatGPT) y espera el callback.
        # Comando constante → shell=True (resuelve `codex.cmd` en Windows).
        proc = subprocess.Popen(
            "codex login", shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        # Salvaguarda: si el flujo se queda colgado (el usuario no completa el
        # login), se mata a los 10 min para no dejar el proceso vivo.
        killer = threading.Timer(600, lambda: proc.poll() is None and proc.kill())
        killer.daemon = True
        killer.start()
        try:
            for line in proc.stdout or []:
                line = (line or "").strip()
                if not line:
                    continue
                m = re.search(r"https?://\S+", line)
                if m:
                    _LOGIN["url"] = m.group(0)   # por si el navegador no se abrió solo
                _LOGIN["detail"] = line[:200]
                if _authenticated():
                    break
            proc.wait(timeout=30)
        finally:
            killer.cancel()
            if proc.poll() is None:
                proc.kill()
        if _authenticated() or proc.returncode == 0:
            _LOGIN.update(status="done", detail="Sesión de Codex iniciada.")
        else:
            _LOGIN.update(
                status="failed",
                detail=(_LOGIN.get("url") and f"No se detectó la sesión. Abre esta URL para iniciar sesión: {_LOGIN['url']}")
                        or "El login no se completó. Ejecuta `codex login` en una terminal.",
            )
    except Exception as e:
        _LOGIN.update(status="failed", detail=f"{type(e).__name__}: {e}")


@router.post("/login")
def login() -> JSONResponse:
    """Lanza `codex login` (abre el navegador del usuario). Aithera no introduce
    credenciales: el usuario inicia sesión con su cuenta de ChatGPT. Estado en
    /status; si el navegador no se abre, /status trae la URL para abrirla a mano."""
    if _find_codex() is None:
        return JSONResponse(content={"started": False, "message": "Codex no está instalado. Instálalo primero."})
    if _authenticated():
        return JSONResponse(content={"started": False, "message": "Ya has iniciado sesión en Codex."})
    if _LOGIN["status"] == "running":
        return JSONResponse(content={"started": False, "message": "Ya hay un inicio de sesión en curso."})
    _LOGIN.update(status="running", detail=None, url=None)
    threading.Thread(target=_login_worker, daemon=True).start()
    return JSONResponse(content={"started": True, "message": "Abriendo el navegador para iniciar sesión…"})


# ---------------------------------------------------------------------------
# Estado (barato: sin lanzar procesos — solo `which` + existencia de auth.json)
# ---------------------------------------------------------------------------
@router.get("/status")
def status() -> JSONResponse:
    installed = _find_codex() is not None
    authenticated = installed and _authenticated()
    ready = installed and authenticated
    return JSONResponse(content={
        "installed": installed,
        "authenticated": authenticated,
        "ready": ready,
        "npm_available": _find_npm() is not None,
        "install_status": _INSTALL["status"],
        "install_detail": _INSTALL["detail"],
        "login_status": _LOGIN["status"],
        "login_detail": _LOGIN["detail"],
        "login_url": _LOGIN.get("url"),
    })
