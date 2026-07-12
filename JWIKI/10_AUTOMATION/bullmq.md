# BullMQ — Node.js queue

## Resumen

**BullMQ** es una librería moderna de queues para Node.js, basada en Redis. **NO usado en Aithera** (Python stack).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Setup

```bash
npm install bullmq
```

```javascript
const { Queue, Worker } = require("bullmq");

// Producer
const myQueue = new Queue("tasks", { connection: { host: "localhost", port: 6379 } });

await myQueue.add("weekly-digest", { user: "..." }, {
    repeat: { pattern: "0 9 * * 1" }  // cron syntax
});

// Consumer
const worker = new Worker("tasks", async (job) => {
    if (job.name === "weekly-digest") {
        await sendWeeklyDigest(job.data.user);
    }
}, { connection: { host: "localhost", port: 6379 } });
```

## Features

- ✅ Repeatable jobs (cron pattern).
- ✅ Delayed jobs.
- ✅ Priority queues.
- ✅ Rate limiting.
- ✅ Failed jobs retry.
- ✅ Dashboard (bull-board).

## Para Aithera

- ❌ NO (Python stack).
- ✅ APScheduler + Redis es el equivalente Python (RQ o Dramatiq).

## Fuentes

1. https://docs.bullmq.io/

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified