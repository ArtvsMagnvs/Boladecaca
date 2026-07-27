import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/index.css";
// [Tema] Importar el store aplica el tema guardado (.dark/.light en <html>)
// ANTES del primer render — sin parpadeo de tema al arrancar.
import "./store/useThemeStore";
// [I18N-1] Importar el store de idioma arranca la reconciliación con el
// backend (app_language) al iniciar, antes de que ningún componente use t().
import "./store/useI18n";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
