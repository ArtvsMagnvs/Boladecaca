// Aithera Desktop (Electron) - proceso principal.
//
// Igual que la app de escritorio anterior (CustomTkinter), este proceso NO
// arranca el backend Python: el usuario sigue iniciando primero
// "iniciar_backend.bat" y luego la app de escritorio. Mantener ese flujo de
// arranque ya probado evita introducir una nueva fuente de fallos al migrar
// la capa visual.
const { app, BrowserWindow, session } = require("electron");
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

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1024,
    minHeight: 700,
    backgroundColor: "#0A0A0F",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
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
