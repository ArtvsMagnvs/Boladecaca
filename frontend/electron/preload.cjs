// Preload script - de momento no expone ninguna API privilegiada al
// renderer. Todo lo que el frontend necesita (datos, IA, voz) llega via
// HTTP normal al backend FastAPI en http://localhost:8000, no via IPC de
// Electron. Este archivo existe como punto de extension futuro (ej. acceso
// a microfono nativo para activacion por voz) sin tener que reestructurar
// la configuracion de seguridad de la ventana mas adelante.
