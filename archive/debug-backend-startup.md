# Debug: backend startup failure — RESOLVED

**Session ID**: `backend-startup-fail`
**Status**: [CLOSED] — Fixed and verified
**Date opened**: 2026-06-26
**Date closed**: 2026-06-26

## Symptoms
- User reported `iniciar backend no funciona`
- `iniciar_backend.bat` exited with code 255
- Error in stderr: `La sintaxis del comando no es correcta.`

## Hypotheses evaluated

| # | Hypothesis | Confirmed? | Evidence |
|---|-----------|-----------|----------|
| H1 | `.bat` parser corrupts API key (`=` inside) | ❌ rejected | Test with stripped-down .bat proved the loop never reached the API key line |
| H2 | CRLF/LF encoding issue in `.env` | ❌ rejected | Hex dump of `.env` showed clean LF, no BOM |
| H3 | Dependency-check Python one-liner breaks | ❌ rejected | Dependency check reached "Dependencias criticas instaladas" successfully |
| H4 | Stale process holding port 8000 | ❌ rejected | Port 8000 was free when .bat was tested |
| **H5** | **`for /f` with `%%a:~0,1%` substring expansion inside a block fails in `cmd.exe`** | **✅ CONFIRMED** | 5 controlled experiments proved that `if not "%%a:~0,1%"="#" set "%%a=%%b"` inside `for /f` triggers `La sintaxis del comando no es correcta.` |
| H6 | Variables set inside `for` block aren't visible after (delayed expansion) | partial | Caught as a secondary issue; needed `setlocal enabledelayedexpansion` |

## Root cause

The original `iniciar_backend.bat` contained:
```bat
for /f "tokens=1,* delims==" %%a in (".env") do (
    if not "%%a"=="" if not "%%a:~0,1%"="#" set "%%a=%%b"
)
```

Two bugs:
1. **`%%a:~0,1%` substring expansion** of a `for` loop variable inside a compound `if` is **not supported** by `cmd.exe`. It triggers "La sintaxis del comando no es correcta." at PARSE time before any line runs, which is why no `echo` inside the block ever printed.
2. **No `enabledelayedexpansion`**: variables set inside a `for` block are not reliably visible after the block ends.

## Fix applied

[`backend/iniciar_backend.bat`](file:///c:/Users/Alejandro/Desktop/CLAUDE/Aithera/backend/iniciar_backend.bat):

1. `setlocal enabledelayedexpansion` at the top of the file
2. Replace the broken loop with:
   ```bat
   for /f "usebackq tokens=1,* delims==" %%a in (`findstr /v /b "#" .env`) do (
       if not "%%a"=="" set "%%a=%%b"
   )
   ```
   - `usebackq` + backticks makes the parens a **command** (run `findstr`)
   - `findstr /v /b "#" .env` filters out comment lines BEFORE the loop (no need for substring check)
   - `if not "%%a"=="" set` is a simple condition that works

## Verification (post-fix)

```
=== EXIT: 0 ===
[OK] Python: c:\Users\Alejandro\Desktop\CLAUDE\Aithera\backend\venv\Scripts\python.exe
[OK] Dependencias criticas instaladas.
Cargando configuracion desde .env...
[OK] Variables de entorno cargadas.
AI_PROVIDER=minimax
MINIMAX_MODEL=MiniMax-M2.7-highspeed
MINIMAX_API_KEY: SET
```

End-to-end live verification:
- `iniciar_backend.bat` ran successfully
- Backend listening on port 8000
- `GET /` → `{"name":"Aithera","version":"0.3.0","status":"running"}`
- `GET /health` → `{"status":"healthy"}`
- `GET /api/ai/status` → `{"provider":"minimax","model":"MiniMax-M2.7-highspeed","healthy":true,"fallback_active":false,"primary_provider":"minimax"}`

## Cleanup

All temporary debug test files removed. Only [`iniciar_backend.bat`](file:///c:/Users/Alejandro/Desktop/CLAUDE/Aithera/backend/iniciar_backend.bat) was modified.
