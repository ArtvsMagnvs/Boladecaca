# Framer Motion — Animaciones en Aithera

## Resumen

**Framer Motion 11** es la librería de animaciones usada en Aithera V0.7.3. Ver CLAUDE.md §2.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Versión

Framer Motion 11.x (CLAUDE.md §2).

## Hello World

```tsx
import { motion } from "framer-motion";

function FadeIn({ children }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
        >
            {children}
        </motion.div>
    );
}
```

## Variants

```tsx
const variants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
};

<motion.ul variants={variants} initial="hidden" animate="visible">
    {items.map(item => (
        <motion.li key={item.id} variants={variants}>{item.text}</motion.li>
    ))}
</motion.ul>
```

## AnimatePresence (mount/unmount)

```tsx
import { AnimatePresence, motion } from "framer-motion";

<AnimatePresence>
    {messages.map(msg => (
        <motion.div
            key={msg.id}
            initial={{ opacity: 0, x: -100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 100 }}
        >
            {msg.text}
        </motion.div>
    ))}
</AnimatePresence>
```

## Gestos

```tsx
<motion.div
    drag
    dragConstraints={{ left: 0, right: 100, top: 0, bottom: 100 }}
    whileHover={{ scale: 1.1 }}
    whileTap={{ scale: 0.9 }}
/>
```

## Layout animations

```tsx
<motion.div layout>
    {expanded ? <Expanded /> : <Collapsed />}
</motion.div>
```

## Aithera

- ✅ Page transitions.
- ✅ List item animations.
- ✅ Modal mount/unmount.
- ✅ Hover effects.
- ❌ NO usar para 3D (eso es R3F).

## Referencias cruzadas

- [JWIKI-088 3d-threejs.md](./3d-threejs.md)
- [JWIKI-091 animations-gsap.md](./animations-gsap.md)

## Fuentes

1. https://www.framer.com/motion/
2. CLAUDE.md §2

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified