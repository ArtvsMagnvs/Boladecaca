# GraphQL — Por qué NO en Aithera

## Resumen

**GraphQL** es una alternativa a REST con schema tipado y queries flexibles. Aithera V0.7.3 usa REST. **GraphQL NO se usa en Aithera**.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## GraphQL basics

```graphql
type Project {
    id: ID!
    name: String!
    tasks: [Task!]!
}

type Query {
    project(id: ID!): Project
    projects: [Project!]!
}

type Mutation {
    createProject(name: String!): Project!
}
```

Cliente pide lo que necesita:
```graphql
query {
    project(id: 1) {
        name
        tasks { title }
    }
}
```

## Por qué Aithera NO usa GraphQL

- ❌ **Overhead**: schema separado, resolvers, persisted queries.
- ❌ **Single-user**: no hay necesidad de queries flexibles.
- ❌ **REST es suficiente** para Aithera (single device, few endpoints).
- ❌ **Complejidad de caché**: GraphQL no es REST-cacheable.
- ❌ **N+1 queries**: hay que pensar en dataloader.

## Cuando SÍ usar GraphQL

- ✅ Multi-client (mobile, web, embedded) con diferentes necesidades.
- ✅ Schema complejo (redes sociales, CMS).
- ✅ Queries dinámicas (UI-driven).
- ✅ Aggregations complejas.

## Para Aithera

Aithera es **personal project, single-user, single-device**. REST es la elección correcta.

**Si Aithera se vuelve multi-client en V1.0+** (mobile + web + Telegram), GraphQL podría tener sentido.

## Alternativas modernas

- **tRPC**: TypeScript-only, end-to-end type-safe. No aplica a Python.
- **REST + OpenAPI**: lo que Aithera usa.

## Referencias cruzadas

- [JWIKI-072 api-design-rest.md](./api-design-rest.md)
- [JWIKI-074 api-design-trpc.md](./api-design-trpc.md)

## Fuentes

1. https://graphql.org/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified