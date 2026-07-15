// Preload script. Todo lo que el frontend necesita (datos, IA, voz) sigue
// llegando via HTTP normal al backend FastAPI en http://localhost:8000, no
// via IPC de Electron — esta sigue siendo la regla general.
//
// V0.87 (WPMS W2e): primera excepcion real y deliberada. Elegir una carpeta
// local para un proyecto (Project.repo_path) requiere el dialogo nativo del
// SO; HTTP no puede hacer eso. contextBridge expone una unica funcion
// minima (window.aithera.pickFolder), no un API generico de filesystem —
// mantiene el contextIsolation real de main.cjs. `window.aithera` no existe
// fuera de Electron (ej. Browser pane / navegador normal en desarrollo);
// el codigo que lo use debe comprobar `window.aithera?.pickFolder` antes.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("aithera", {
  pickFolder: () => ipcRenderer.invoke("dialog:pick-folder"),
});
