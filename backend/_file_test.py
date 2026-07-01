"""Prueba FINAL: que archivo se ejecuta realmente."""
import sys
sys.stdout.write(f"[FILE-DEBUG] __file__={__file__}\n")
sys.stdout.write(f"[FILE-DEBUG] sys.argv={sys.argv}\n")
sys.stdout.write(f"[FILE-DEBUG] sys.executable={sys.executable}\n")
sys.stdout.write(f"[FILE-DEBUG] cwd={__import__('os').getcwd()}\n")
sys.stdout.flush()
# Leer el archivo y buscar el print
with open(__file__) as f:
    content = f.read()
sys.stdout.write(f"[FILE-DEBUG] contiene 'DBG] engine.url' = {'engine.url' in content}\n")
sys.stdout.write(f"[FILE-DEBUG] contiene 'r.id=8' = {'r.id=8' in content}\n")
sys.stdout.flush()