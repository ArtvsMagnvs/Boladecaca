# Aithera — Plan de Reescritura: Hub Visual + Sistema de Voz

**Decisión confirmada:** reescritura completa del frontend en Electron + React + TypeScript. El backend FastAPI (Fases 0, 1, 2 y 6, ya auditado, depurado y probado con peticiones reales) se mantiene sin cambios — es la fuente de verdad y el nuevo frontend consume exactamente los mismos endpoints REST/SSE.

---

## 1. Arquitectura

- **Stack**: Vite + React 18 + TypeScript + Zustand (estado) + React Router (navegación) + Electron (empaquetado de escritorio).
- **Backend**: FastAPI sin cambios. El frontend habla con `http://localhost:8000/api` exactamente igual que hacía `desktop.py`.
- **Animación**: Canvas 2D + WebGL (vía `three.js` o `@react-three/fiber`) para el núcleo de IA; Framer Motion para transiciones de UI; CSS puro con GPU acceleration (`transform`/`opacity`) para todo lo demás. Nada de animaciones por JS de layout (`top`/`left`/`width`) — eso es lo que causa lag.
- **Por qué este reparto**: reutiliza el backend ya probado, permite WebGL/60fps reales (imposible en CustomTkinter), y aísla el riesgo en una sola capa nueva.

## 2. Sistema de diseño (basado en investigación real: Raycast, Arc Browser, Jarvis UI 2026)

- **Filosofía**: dark-first (no "modo oscuro" como opción secundaria — la interfaz nace oscura). Jerarquía por luminancia, no por sombras. Bordes sutiles para profundidad en vez de drop-shadows pesados.
- **Paleta**: negro profundo (#0A0A0F) y grises oscuros como base; azul suave (#5EA8FF / #7C9CFF) y blanco suave (#E8EAF0) como acentos. Nada de neón saturado, rojo intenso permanente, verde fosforito ni estética gamer.
- **Glassmorphism quirúrgico**: solo en paneles flotantes, menús contextuales y el propio núcleo de IA — nunca como fondo general de toda la pantalla.
- **Tipografía**: sans-serif geométrica (Inter o similar), pesos variables para jerarquía en vez de tamaños muy distintos.
- **Motion**: todas las transiciones con `transform`/`opacity` (GPU), 200-300ms, easing `cubic-bezier` suave. Nunca aparición brusca — todo entra con fade + slight scale/translate.

## 3. Hub Central

Layout en tres zonas alrededor del núcleo (centro):

| Zona | Contenido |
|---|---|
| Centro | Núcleo de IA animado (siempre visible) |
| Izquierda | Proyectos, Tareas, Agentes (resumen + accesos) |
| Derecha | Calendario, Emails importantes, Actividad reciente |
| Inferior | Estado del sistema, IA activa, modelo activo, estado de voz |

### Núcleo de IA — Estados y comportamiento visual

| Estado | Comportamiento |
|---|---|
| Reposo | Movimiento muy suave, "respiración" (escala 1.0↔1.03 en ~4s, easing suave) |
| Escuchando | Ondas concéntricas suaves saliendo del núcleo, brillo aumentado |
| Pensando | Rotación interna, partículas orbitando, ondas internas más complejas |
| Hablando | Pulsos sincronizados con la amplitud del audio (Web Audio API), reacción en tiempo real |
| Procesando | Variante de "pensando" con indicador de progreso sutil |
| Error | Pulso breve en tono rojizo apagado (no rojo intenso), vuelve a reposo |

Implementación: esfera/blob en `@react-three/fiber` con shader simple de ruido (Perlin) modulado por un parámetro `intensity` por estado; transición entre estados con interpolación de 300-500ms, nunca un corte brusco.

## 4. Voice Center (especificación completa)

- **Arquitectura de proveedores** (activable/desactivable cada uno, interfaz común): ElevenLabs, MiniMax Voice, OpenAI Voice, Piper, Coqui.
- **Idiomas**: Español (España/Argentina/México/Colombia), Inglés, Francés, Japonés, Chino.
- **Catálogo de voces**: masculinas/femeninas/neutras, cada una con nombre, proveedor, idioma, acento y botón "Escuchar muestra" (reproduce sin guardar cambios).
- **Controles**: velocidad, tono, energía, expresividad, volumen.
- **Personalidad de voz**: campo de prompt editable + presets (Formal, Profesional, Asistente ejecutivo, Amigable, Directo, Sarcástico, Personalizado). Se inyecta como parte del system prompt del proveedor de IA activo.
- **Voz consciente del contexto**: el tono se ajusta según el tipo de evento (error crítico = más serio; recordatorio = más relajado; reunión importante = más profesional) — mapeo de "tipo de situación" a ajuste de parámetros de voz.
- **Activación por voz**: arquitectura preparada para wake-word ("Aithera"/"Hola Aithera") sin implementarlo todavía — solo el punto de extensión.
- **Indicadores**: ondas + brillo mientras escucha; transcripción + animación de voz mientras responde.

## 5. Inventario de pantallas (CustomTkinter → React)

| Pantalla actual | Estado | Prioridad de migración |
|---|---|---|
| Dashboard | Se convierte en el nuevo Hub Central | Fase 3 |
| Chat | Migrar con streaming SSE | Fase 4 |
| Proyectos / Tareas / Calendario | Migrar con toda la lógica de Fase 6 | Fase 5 |
| Configuración (8 proveedores IA) | Migrar gestión completa | Fase 6 |
| Voice Center | Nuevo, no existía | Fase 7 |
| Email Assistant / Agentes | Migrar | Fase 8 |

## 6. Roadmap de implementación

1. Scaffold del proyecto (Vite+React+TS+Electron) + cliente API.
2. Sistema de diseño base (tokens, componentes primitivos).
3. Hub Central + Núcleo de IA animado.
4. Chat con streaming.
5. Proyectos / Tareas / Calendario.
6. Configuración de IA.
7. Voice Center completo.
8. Email Assistant + Agentes.
9. Empaquetado Electron + auditoría final iterativa.

**Nota de expectativas:** esto es una reescritura completa de 9 pantallas con animación real. Se construye y se prueba fase por fase — cada fase queda funcional y verificada antes de pasar a la siguiente, en vez de dejar todo a medias para el final.
