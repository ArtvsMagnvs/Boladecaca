// Aithera Desktop (Electron) - proceso principal.
//
// Igual que la app de escritorio anterior (CustomTkinter), este proceso NO
// arranca el backend Python: el usuario sigue iniciando primero
// "iniciar_backend.bat" y luego la app de escritorio. Mantener ese flujo de
// arranque ya probado evita introducir una nueva fuente de fallos al migrar
// la capa visual.
const { app, BrowserWindow, session, ipcMain, dialog } = require("electron");
const path = require("path");

// V0.7.1 (FIX): Suprimir warnings internos de Chromium DevTools que aparecen
// en la consola cuando se abre DevTools. No son bugs de nuestro codigo:
//   - "Autofill.enable wasn't found" -> DevTools llama un metodo CDP que ya no existe
//   - "Failed to fetch" en elements.js -> DevTools intenta fetchear recursos
//     que no estan disponibles en el Chromium empaquetado de Electron.
// Los filtramos a nivel de proceso y linea de comandos.
app.commandLine.appendSwitch("disable-features",
  "AutofillEnableDevtoolsIssuesObserver,AutofillAddressFormFillObserver");

const isDev = !app.isPackaged;

// V0.7.1 (FIX): Lista de mensajes de consola conocidos de Chromium DevTools
// que son ruido inofensivo (no afectan a la app). Los filtramos.
const HARMLESS_DEVTOOLS_PATTERNS = [
  /Autofill\.enable.*wasn't found/i,
  /Failed to fetch/i,
  /Autofill\.AddressFormFillObserver/i,
];

function isHarmlessDevtoolsMessage(text) {
  if (!text) return false;
  return HARMLESS_DEVTOOLS_PATTERNS.some((re) => re.test(text));
}

// [PU6a-bis v2, doc 35 §PU6] Esc lo decide SIEMPRE el renderer. La primera
// version (un flag "ui:escape-capture" que la UI mantenia al dia) tenia una
// carrera inherente: el flag podia llegar tarde y este proceso salia de
// pantalla completa cuando la UI queria cerrar el chat (fallo reportado en
// vivo). Ahora el orden es determinista: este proceso NUNCA toca Esc; la UI
// procesa la tecla con su prioridad (dialogo → chat → presencia → pagina) y,
// solo si no le queda nada que cerrar, pide salir del fullscreen por IPC.
ipcMain.on("window:exit-fullscreen", (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (win && win.isFullScreen()) win.setFullScreen(false);
});

function createWindow() {
  const win = new BrowserWindow({
    // [2026-07-21] `show: false` + `maximize()` al estar listo = Aithera SIEMPRE
    // abre MAXIMIZADA (ocupa la pantalla dentro de la ventana de Windows, sin
    // quitar la barra de tareas). El tamaño de abajo es el que tendría si la
    // restauras. Evita el parpadeo de abrir pequeña y crecer.
    width: 1280,
    height: 820,
    minWidth: 1024,
    minHeight: 700,
    show: false,
    backgroundColor: "#0A0A0F",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.once("ready-to-show", () => {
    win.maximize();
    win.show();
  });

  // [2026-07-21] F11 = PANTALLA COMPLETA TOTAL (oculta la barra de Windows),
  // toggle. Esc también sale del fullscreen (comportamiento esperado). El
  // maximizado normal (arriba) es lo de siempre; el fullscreen es el modo
  // inmersivo opcional.
  //
  // [PU6a-bis v2, doc 35 §PU6] Esc ya NO se toca aqui: este handler ve las
  // teclas ANTES que el renderer, asi que cualquier decision tomada aqui
  // le gana a la UI (con el chat abierto en fullscreen, Esc salia de
  // pantalla completa en vez de cerrar el chat — fallo reportado en vivo).
  // La tecla pasa siempre al renderer; cuando a la UI no le queda nada que
  // cerrar, pide salir del fullscreen via "window:exit-fullscreen".
  win.webContents.on("before-input-event", (event, input) => {
    if (input.type === "keyDown" && input.key === "F11") {
      win.setFullScreen(!win.isFullScreen());
      event.preventDefault();
    }
  });

  // V0.7.1 (FIX): Filtrar mensajes de consola conocidos de Chromium DevTools
  // para que no aparezcan en la consola del usuario (no son nuestros bugs).
  win.webContents.on("console-message", (event, level, message, line, source) => {
    // Solo filtrar si viene de DevTools interno (devtools://) Y matchea
    // un patron conocido de ruido.
    if (source && source.startsWith("devtools://") && isHarmlessDevtoolsMessage(message)) {
      // Cancelamos el evento (no se imprime en consola del usuario)
      event.preventDefault();
      return;
    }
  });

  if (isDev) {
    win.loadURL("http://localhost:5173");
    // V0.7.1 (FIX): No auto-abrir DevTools. Antes se abria automaticamente
    // al arrancar en modo dev, lo que disparaba los warnings de Chromium.
    // El usuario puede abrirlo manualmente con Ctrl+Shift+I cuando quiera.
    // win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }
}

// V0.87 (WPMS W2e): primer uso real de IPC en esta app (preload.cjs estaba
// vacio a proposito, como punto de extension). Un proyecto necesita apuntar
// a una carpeta local real (repo_path) y el navegador no puede leer rutas
// absolutas del sistema de archivos por seguridad — el picker nativo de
// Electron es el unico camino honesto. Sin logica de negocio aqui: solo
// devuelve la ruta elegida o null si el usuario cancela.
ipcMain.handle("dialog:pick-folder", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openDirectory", "createDirectory"],
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  return result.filePaths[0];
});

// [2026-07-25] Seleccionar ARCHIVOS para adjuntarlos a un proyecto
// (Project.docs con kind="file"). Mismo criterio que pick-folder: el navegador
// no puede dar rutas absolutas del sistema, así que el diálogo nativo es el
// único camino honesto. Multi-selección permitida; devuelve un array de rutas
// (vacío si el usuario cancela). Sin lógica de negocio aquí: el backend valida
// después que cada ruta esté dentro de HOME antes de que un agente la lea
// (app/tools/filesystem_tool.py).
ipcMain.handle("dialog:pick-files", async () => {
  const result = await dialog.showOpenDialog({
    properties: ["openFile", "multiSelections"],
  });
  if (result.canceled) return [];
  return result.filePaths;
});

app.whenReady().then(() => {
  // V0.83 (Paso 4) STT: el micro se usa desde el Hub/Chat (MediaRecorder).
  // Sin este handler, Chromium pide permiso al SO y a veces lo deniega en
  // silencio. Aithera es personal-use, asi que autorizamos media/microphone
  // por defecto. Si en el futuro se quiere granularidad, se cambia aqui.
  session.defaultSession.setPermissionRequestHandler((_wc, permission, callback) => {
    if (permission === "media" || permission === "microphone") {
      return callback(true);
    }
    return callback(true);
  });
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
