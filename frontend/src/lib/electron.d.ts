// V0.87 (WPMS W2e): declara window.aithera, expuesto por electron/preload.cjs
// via contextBridge. Solo existe dentro de Electron — en el navegador normal
// (Browser pane / `vite dev` fuera de Electron) es undefined; el codigo que
// lo use debe comprobar `window.aithera?.pickFolder` antes de llamarlo.
export {};

declare global {
  interface Window {
    aithera?: {
      pickFolder: () => Promise<string | null>;
      /** [2026-07-25] Selecciona uno o varios ARCHIVOS (rutas absolutas) para
       *  adjuntarlos a un proyecto. `[]` si el usuario cancela. */
      pickFiles: () => Promise<string[]>;
    };
  }
}
