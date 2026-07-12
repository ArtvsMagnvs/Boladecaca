# Observability — Metrics Prometheus

## Resumen

**Métricas** (counters, gauges, histograms) son críticas para monitoring + alerting. **NO usado en Aithera V0.7.3** (logs only). V0.85+ considera.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Prometheus setup

```bash
pip install prometheus-client prometheus-fastapi-instrumentator
```

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

@app.on_event("startup")
async def startup():
    Instrumentator().instrument(app).expose(app)

# Custom metric
from prometheus_client import Counter, Histogram

chat_requests = Counter("aithera_chat_requests_total", "Total chat requests")
chat_latency = Histogram("aithera_chat_latency_seconds", "Chat latency")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    chat_requests.inc()
    with chat_latency.time():
        response = await ai_manager.chat(request)
    return response
```

## Metrics expuestos

```
GET /metrics
# HELP aithera_chat_requests_total Total chat requests
# TYPE aithera_chat_requests_total counter
aithera_chat_requests_total 1234.0

# HELP aithera_chat_latency_seconds Chat latency
# TYPE aithera_chat_latency_seconds histogram
aithera_chat_latency_seconds_bucket{le="0.5"} 100
aithera_chat_latency_seconds_bucket{le="1.0"} 200
```

## Dashboards Grafana

- Chat requests / sec.
- LLM latency (TTFT, total).
- Memory usage.
- Error rate.

## Para Aithera

- ❌ V0.7.3: NO Prometheus.
- ⏳ V0.85+: opcional para self-monitoring.

## Fuentes

1. https://prometheus.io/
2. https://github.com/trallnag/prometheus-fastapi-instrumentator

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified