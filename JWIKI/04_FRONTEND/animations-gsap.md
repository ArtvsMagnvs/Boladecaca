# GSAP — Alternativa animaciones

## Resumen

**GSAP** (GreenSock Animation Platform) es la librería de animaciones más completa para web. Aithera V0.7.3 usa Framer Motion, **NO GSAP**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## GSAP highlights

- ✅ **Timeline-based**: control total de secuencias.
- ✅ **Performance**: GPU-accelerated, smooth.
- ✅ **Plugins**: ScrollTrigger, MorphSVG, DrawSVG.
- ✅ **No framework**: vanilla JS.

## GSAP vs Framer Motion

| Aspecto | GSAP | Framer Motion 11 |
|---|---|---|
| Paradigma | Imperative timeline | Declarative React |
| API | gsap.to(), gsap.timeline() | motion components |
| Learning curve | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| React integration | ❌ manual | ✅ native |
| Performance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Bundle | ~30KB | ~50KB |

## Para Aithera

Framer Motion elegido por integración React nativa. GSAP sería válido para animaciones muy complejas (no necesarias en Aithera).

## Hello World

```javascript
import gsap from "gsap";

gsap.to(".box", {
    x: 100,
    duration: 1,
    ease: "power2.out",
    onComplete: () => console.log("done")
});
```

## Referencias cruzadas

- [JWIKI-090 animations-framer.md](./animations-framer.md)

## Fuentes

1. https://greensock.com/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified