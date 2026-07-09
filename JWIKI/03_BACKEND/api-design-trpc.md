# tRPC — Alternativa TypeScript end-to-end typesafe

## Resumen

**tRPC** es una alternativa moderna a REST para TypeScript monorepos. End-to-end type-safe sin schemas separados. **NO se usa en Aithera** (backend Python).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## tRPC basics

```typescript
// server
import { initTRPC } from "@trpc/server";
const t = initTRPC.create();

export const appRouter = t.router({
    getProject: t.procedure
        .input(z.object({ id: z.string() }))
        .query(async ({ input }) => {
            return await db.project.findUnique({ where: { id: input.id } });
        }),
});

export type AppRouter = typeof appRouter;

// client
import { createTRPCProxyClient } from "@trpc/client";
const client = createTRPCProxyClient<AppRouter>({ url: "/trpc" });
const project = await client.getProject.query({ id: "1" });
// TypeScript sabe la shape del return
```

## Ventajas

- ✅ **End-to-end typesafe**: sin OpenAPI/codegen.
- ✅ **Zero overhead**: similar a function calls.
- ✅ **Refactor safe**: cambios en server → cliente detecta TS errors.

## Desventajas

- ❌ **TypeScript-only**: backend debe ser TS.
- ❌ **Monorepo**: requiere cliente y servidor en mismo repo.
- ❌ **No OpenAPI standard**: otros clientes (Python, etc.) no se integran bien.

## Para Aithera

Aithera backend es **Python** (FastAPI). tRPC requiere TypeScript backend. **No aplica**.

**Si Aithera migrara a Node/TS backend**, tRPC sería opción. Pero no es el caso.

## Cuando SÍ usar tRPC

- ✅ Monorepo TS (Next.js fullstack).
- ✅ TypeScript-first project.
- ✅ Type safety es prioridad #1.

## Alternativas para Python

- **FastAPI + Pydantic**: type-safe Python.
- **gRPC + Protobuf**: contrato strict, multi-language.

## Referencias cruzadas

- [JWIKI-072 api-design-rest.md](./api-design-rest.md)
- [JWIKI-073 api-design-graphql.md](./api-design-graphql.md)

## Fuentes

1. https://trpc.io/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified