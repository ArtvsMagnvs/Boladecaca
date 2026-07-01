#!/usr/bin/env python3
"""Update jwiki-tick-a cron prompt to FORCE reporting to root session."""
import subprocess

PROMPT = """Tick JWIKI UNICO (24/7, un solo equipo secuencial ritmo 30min desde 2026-06-30 19:15):

1. Lee JWIKI/00_INDEX/task_queue.md y wiki-map.md. Toma el SIGUIENTE ID con estado pending (mas bajo, sin importar paridad). Si todos los items activos ya tienen in_progress zombi, no crees nuevos spawns; simplemente emite alerta por saturacion.

2. Despacha al investigador principal (aithera-wiki-investigador) SOLO si la cuota MiniMax-M3 parece sana (verificar `mavis session list mavis --purpose 'cron:mavis:jwiki-tick-a'` recientes; si los ultimos 3+ ticks cayeron con errorCode 42212, NO despachar, solo alerta).

3. AL TERMINAR (obligatorio, regla innegociable): ejecuta SIEMPRE este comando para reportar al chat raiz. Sustituye SELF por el ID de tu propia sesion (lo encontraras en el session metadata del contexto de invocacion):

   mavis communication send --from SELF --to mvs_bc3b13a27aa04947b4eeae28e21a6047 --command prompt --content "JWIKI TICK HH:MM EUROPE/PARIS - Estado: alerta|done|verified|rejected - ticks/A-YYYYMMDD-HHMM.md - cola: <resumen 1 linea>"

4. Si falla el `mavis communication send` por Token Plan (errorCode 42212), registra el error pero intenta enviar un payload minimo:
   "ALERTA: cron HH:MM fallo por cuota MiniMax-M3 - ver ticks/A-YYYYMMDD-HHMM.md"

5. Si el tick anterior aun no cerro (>35 min), NO despaches investigador; emite alerta via el mismo `mavis communication send`.

SIN EL `mavis communication send` AL CHAT RAIZ (mvs_bc3b13a27aa04947b4eeae28e21a6047), ESTE CHAT NO RECIBE NADA. El archivo ticks/A-*.md es secundario; el IM al chat raiz es lo que mantiene al usuario informado.

Siembra este conocimiento en ~/.mavis/agents/mavis/memory/MEMORY.md si descubres que el bypass funciona (entrada nueva: 'JWIKI cron fires 2026-07-01 -- REPORTE OBLIGATORIO via mavis communication send mvs_bc3b13a27aa04947b4eeae28e21a6047'). 24/7.
"""

MAVIS = r"C:\Users\Alejandro\.mavis\bin\mavis.cmd"
result = subprocess.run(
    [MAVIS, "cron", "update", "mavis", "jwiki-tick-a", "--prompt", PROMPT],
    capture_output=True, text=True, timeout=60
)
print("RC:", result.returncode)
print("STDOUT:", result.stdout[:3000])
print("STDERR:", result.stderr[:3000])
