import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Configuracion de Vite para Aithera.
// base: "./" es necesario para que Electron pueda cargar los assets con
// rutas relativas cuando se empaqueta (file://), en vez de rutas absolutas
// "/assets/..." que solo funcionan servidas desde un dominio raiz.
export default defineConfig({
  base: "./",
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  optimizeDeps: {
    include: ["three"],
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    commonjsOptions: {
      include: [/three/, /node_modules/],
    },
  },
});
