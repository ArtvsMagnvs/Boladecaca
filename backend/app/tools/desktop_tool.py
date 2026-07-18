# backend/app/tools/desktop_tool.py
#
# V1.0/1.1 (Tools): control real de raton/teclado + vision de pantalla
# (peticion del usuario, 2026-07-18). Es la tool de MAYOR riesgo del catalogo
# (permissions.py la marca "risk=high") -- interactua de verdad con la sesion
# de Windows del usuario, la misma en la que puede estar trabajando en OTRA
# ventana en ese instante.
#
# Seguridad:
# - click/double_click/type/hotkey/move_mouse SIEMPRE requieren confirmacion
#   (igual que ShellTool/PowerShellTool) -- ninguna excepcion por accion.
# - pyautogui.FAILSAFE se deja ACTIVO (el usuario puede abortar moviendo el
#   raton a una esquina de la pantalla en pleno gesto).
# - Coordenadas siempre acotadas al tamano real de pantalla (nunca clics
#   "a ciegas" fuera de los limites).
# - OCR via winocr (motor NATIVO de Windows, sin modelos que descargar ni
#   tocar la version de PyTorch ya usada por el MOS -- ver requirements.txt).
#
# Acciones: click, double_click, type, hotkey, move_mouse, screenshot, ocr,
# find_text_on_screen.

import asyncio
import base64
import io
from typing import Dict, Any, List, Optional

from .base import BaseTool

# Import LAZY (igual que Playwright en browser_tool.py): pyautogui por si solo
# cuesta ~0.3s de import (arrastra Pillow/pyscreeze/pygetwindow) -- si se
# importara a nivel de modulo, el arranque del backend lo pagaria SIEMPRE (via
# app.tools que registra todas las tools por defecto), aunque nadie use nunca
# Desktop Tool. Se importa la primera vez que de verdad se ejecuta una accion.
pyautogui = None
winocr = None


def _ensure_pyautogui() -> None:
    global pyautogui
    if pyautogui is not None:
        return
    try:
        import pyautogui as _pyautogui
    except ImportError as e:
        raise RuntimeError("pyautogui no esta instalado (pip install pyautogui)") from e
    _pyautogui.FAILSAFE = True   # NUNCA desactivar: es el kill-switch del usuario
    _pyautogui.PAUSE = 0.05
    pyautogui = _pyautogui


def _ensure_winocr() -> None:
    global winocr
    if winocr is not None:
        return
    try:
        import winocr as _winocr
    except ImportError as e:
        raise RuntimeError("winocr no esta instalado (pip install winocr)") from e
    winocr = _winocr


def _clamp_coords(x: int, y: int) -> tuple[int, int]:
    w, h = pyautogui.size()
    return max(0, min(x, w - 1)), max(0, min(y, h - 1))


class DesktopTool(BaseTool):
    tool_id = "desktop"
    name = "Desktop Tool"
    description = (
        "Control real del raton/teclado y lectura de pantalla (OCR). La tool "
        "de mas riesgo del catalogo: interactua con TU sesion de Windows real. "
        "Toda accion que mueve el raton o escribe SIEMPRE pide confirmacion."
    )
    requires_confirmation = False  # depende de la accion (lectura vs interaccion)

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            _ensure_pyautogui()
        except RuntimeError as e:
            return {"success": False, "result": None, "error": str(e)}
        try:
            handler = {
                "click": self._click,
                "double_click": self._double_click,
                "type": self._type,
                "hotkey": self._hotkey,
                "move_mouse": self._move_mouse,
                "screenshot": self._screenshot,
                "ocr": self._ocr,
                "find_text_on_screen": self._find_text_on_screen,
            }.get(action)
            if not handler:
                return {
                    "success": False, "result": None,
                    "error": f"Accion desconocida: {action}. Disponibles: click, double_click, type, hotkey, move_mouse, screenshot, ocr, find_text_on_screen",
                }
            return await handler(params)
        except getattr(pyautogui, "FailSafeException", Exception) as e:
            return {"success": False, "result": None, "error": f"abortado por el usuario (failsafe): {e}"}
        except Exception as e:
            return {"success": False, "result": None, "error": f"{type(e).__name__}: {e}"}

    def list_actions(self) -> List[Dict[str, Any]]:
        return [
            {"id": "click", "description": "Clic con el raton en una coordenada de pantalla.",
             "requires_confirmation": True, "params": {"x": "int", "y": "int"}},
            {"id": "double_click", "description": "Doble clic en una coordenada.",
             "requires_confirmation": True, "params": {"x": "int", "y": "int"}},
            {"id": "type", "description": "Escribe texto donde este el foco del teclado.",
             "requires_confirmation": True, "params": {"text": "string"}},
            {"id": "hotkey", "description": "Combinacion de teclas (ej. ['ctrl','s']).",
             "requires_confirmation": True, "params": {"keys": "lista de strings (nombres de tecla de pyautogui)"}},
            {"id": "move_mouse", "description": "Mueve el raton a una coordenada (sin clic).",
             "requires_confirmation": True, "params": {"x": "int", "y": "int"}},
            {"id": "screenshot", "description": "Captura de pantalla completa (PNG en base64).",
             "requires_confirmation": False, "params": {}},
            {"id": "ocr", "description": "Lee el texto visible en pantalla (OCR nativo de Windows).",
             "requires_confirmation": False, "params": {}},
            {"id": "find_text_on_screen", "description": "Busca un texto en pantalla y devuelve su posicion si lo encuentra.",
             "requires_confirmation": False, "params": {"text": "string (subcadena a buscar, case-insensitive)"}},
        ]

    # ------------------------------------------------------------------

    async def _click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        x, y = self._xy(params)
        if x is None:
            return {"success": False, "result": None, "error": "faltan parametros: x, y"}
        await asyncio.to_thread(pyautogui.click, x, y)
        return {"success": True, "result": {"clicked_at": [x, y]}, "error": None}

    async def _double_click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        x, y = self._xy(params)
        if x is None:
            return {"success": False, "result": None, "error": "faltan parametros: x, y"}
        await asyncio.to_thread(pyautogui.doubleClick, x, y)
        return {"success": True, "result": {"double_clicked_at": [x, y]}, "error": None}

    async def _type(self, params: Dict[str, Any]) -> Dict[str, Any]:
        text = params.get("text")
        if not text:
            return {"success": False, "result": None, "error": "falta parametro: text"}
        await asyncio.to_thread(pyautogui.typewrite, text, 0.02)
        return {"success": True, "result": {"typed_chars": len(text)}, "error": None}

    async def _hotkey(self, params: Dict[str, Any]) -> Dict[str, Any]:
        keys = params.get("keys")
        if not keys or not isinstance(keys, list):
            return {"success": False, "result": None, "error": "falta parametro: keys (lista)"}
        await asyncio.to_thread(pyautogui.hotkey, *keys)
        return {"success": True, "result": {"pressed": keys}, "error": None}

    async def _move_mouse(self, params: Dict[str, Any]) -> Dict[str, Any]:
        x, y = self._xy(params)
        if x is None:
            return {"success": False, "result": None, "error": "faltan parametros: x, y"}
        await asyncio.to_thread(pyautogui.moveTo, x, y)
        return {"success": True, "result": {"moved_to": [x, y]}, "error": None}

    async def _screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        img = await asyncio.to_thread(pyautogui.screenshot)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return {"success": True, "result": {
            "image_base64": base64.b64encode(buf.getvalue()).decode(), "format": "png",
            "width": img.width, "height": img.height,
        }, "error": None}

    async def _ocr(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            _ensure_winocr()
        except RuntimeError as e:
            return {"success": False, "result": None, "error": str(e)}
        img = await asyncio.to_thread(pyautogui.screenshot)
        result = await winocr.recognize_pil(img)
        return {"success": True, "result": {"text": result.text}, "error": None}

    async def _find_text_on_screen(self, params: Dict[str, Any]) -> Dict[str, Any]:
        needle = (params.get("text") or "").strip().lower()
        if not needle:
            return {"success": False, "result": None, "error": "falta parametro: text"}
        try:
            _ensure_winocr()
        except RuntimeError as e:
            return {"success": False, "result": None, "error": str(e)}

        img = await asyncio.to_thread(pyautogui.screenshot)
        result = await winocr.recognize_pil(img)
        for line in result.lines:
            if needle in line.text.lower():
                # bounding box del centro de la linea (coordenadas de pantalla reales)
                words = line.words
                if words:
                    x0 = min(w.bounding_rect.x for w in words)
                    y0 = min(w.bounding_rect.y for w in words)
                    x1 = max(w.bounding_rect.x + w.bounding_rect.width for w in words)
                    y1 = max(w.bounding_rect.y + w.bounding_rect.height for w in words)
                    center = [int((x0 + x1) / 2), int((y0 + y1) / 2)]
                else:
                    center = None
                return {"success": True, "result": {"found": True, "text": line.text, "center": center}, "error": None}
        return {"success": True, "result": {"found": False, "text": None, "center": None}, "error": None}

    # ------------------------------------------------------------------

    def _xy(self, params: Dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
        x, y = params.get("x"), params.get("y")
        if x is None or y is None:
            return None, None
        try:
            return _clamp_coords(int(x), int(y))
        except (TypeError, ValueError):
            return None, None
