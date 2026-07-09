# Proveedores chinos — MiniMax, DeepSeek, Qwen, Zhipu, Doubao

## Resumen

Los proveedores chinos han ganado terreno enorme en 2024-2026 con pricing agresivo, open weights y rendimiento competitivo. Este doc es un overview complementario a JWIKI-024 (DeepSeek), 026 (Qwen), 027 (MiniMax).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Panorama de proveedores chinos

| Proveedor | Empresa | Modelo flagship | Open weights | Pricing | Notas |
|---|---|---|---|---|---|
| **DeepSeek** | DeepSeek AI | V4 / R1 | ✅ MIT-like | $0.07-$1.10/M | 🥇 Champion en pricing |
| **Qwen** | Alibaba | Qwen3-72B | ✅ Apache-2.0 + Qwen License | $0.05-$1.20/M | Multilingual excelso |
| **MiniMax** | MiniMax | M2.7-highspeed | ❌ (closed) | [no público] | Razonador, Aithera default |
| **Zhipu GLM** | Zhipu AI | GLM-4 / GLM-4-Plus | Parcial | Tier-2 | Código |
| **Doubao** | ByteDance | Doubao-pro | ❌ (closed) | Barato | Multimodal |
| **ERNIE** | Baidu | ERNIE 4.0 | ❌ | Barato | Chino nativo |
| **Tongyi Qianwen** | Alibaba (Qwen alias) | (mismo Qwen) | ✅ | (mismo Qwen) | — |
| **Moonshot Kimi** | Moonshot AI | kimi-k2 | ❌ | Barato | Long context 2M |
| **Yi** | 01.AI | Yi-Lightning | ✅ Apache-2.0 | Tier-2 | Bilingüe |
| **Baichuan** | Baichuan Inc. | Baichuan 4 | ✅ | Barato | Chino |

## DeepSeek — el disruptor

Ver [JWIKI-024 deepseek.md](./deepseek.md).

## Qwen (Alibaba) — el más completo

Ver [JWIKI-026 qwen.md](./qwen.md).

## MiniMax — Aithera default

Ver [JWIKI-027 minimax.md](./minimax.md). Razonador, max 2048 tokens.

## Zhipu GLM — código fuerte

GLM-4-Plus y GLM-4-9B son alternativas razonables a DeepSeek/Qwen. Disponible vía API + open weights en HuggingFace.

## Moonshot Kimi — long context

`kimi-k2` ofrece **2M context** (competencia directa a Gemini 3.5). API abierta pero closed weights.

## Doubao (ByteDance) — multimodal

`doubao-pro` con vision + audio. Bastante usado en China.

## ERNIE (Baidu) — Chino nativo

`ERNIE 4.0` optimizado para chino. Closed weights, API tier-2.

## Comparativa por caso de uso

| Caso | Mejor proveedor chino |
|---|---|
| **Reasoning** | DeepSeek R1 |
| **Long context (2M)** | Moonshot Kimi |
| **Multimodal (image+audio)** | Doubao o Gemini |
| **Open weights self-host** | Qwen3-32B o DeepSeek-R1-Distill-32B |
| **Multilingual excelente** | Qwen3 |
| **Razonador Aithera-friendly** | MiniMax M2.7-highspeed |
| **Barato** | DeepSeek-V4-flash |

## Tendencias 2024-2026

- **DeepSeek R1 (Enero 2025)** abrió la era de reasoning open weights accesible.
- **Qwen3** (2025) es referencia para multilingual.
- **Proveedores chinos han bajado precios 10-30x** vs OpenAI/Anthropic.
- **Closed providers chinos** (MiniMax, Doubao, Kimi) tienen modelos competitivos pero pricing opaco.

## Aithera y proveedores chinos

Aithera V0.7.3 ya integra **DeepSeek + MiniMax + Ollama (Qwen vía Ollama) + OpenRouter (que ofrece modelos chinos)**. Le falta añadir Qwen directo, Kimi, GLM.

## Referencias cruzadas

- [JWIKI-019 README.md](./README.md)
- [JWIKI-024 deepseek.md](./deepseek.md)
- [JWIKI-026 qwen.md](./qwen.md)
- [JWIKI-027 minimax.md](./minimax.md)

## Fuentes

1. https://platform.deepseek.com/
2. https://qwen.alibaba.com/
3. https://platform.MiniMax.io/  (proxy reference)
4. https://www.zhipuai.cn/
5. https://platform.moonshot.cn/
6. https://www.volcengine.com/product/doubao

## Nivel de confianza

**80%** — Panorama general, precios aproximados.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified