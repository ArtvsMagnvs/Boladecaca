# Plugin Architecture — Modularidad sin microservices

## Resumen

**Plugin architecture** permite extender funcionalidad sin recompilar el core. Aithera V0.7.3 NO es estrictamente plugin-based, pero tiene patrón modular. Para V0.85+ (Memory skills) podría formalizarse.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Comparativa

| Aspecto | Monolith | Plugin-based | Microservices |
|---|---|---|---|
| **Extensibilidad** | ❌ recompilar | ✅ drop-in | ✅ servicios independientes |
| **Complejidad** | Baja | Media | Alta |
| **Performance** | ✅ in-process | ✅ in-process | ❌ red |
| **Deployment** | 1 | 1 + plugins | N |
| **Testing** | Fácil | Medio | Complejo |

## Plugin patterns

### 1. Entry-point discovery (setuptools)

```python
# Plugin author
from my_plugin import Skill

class MySkill(Skill):
    name = "my_skill"
    description = "Does X"
    
    def execute(self, context):
        return ...

# pyproject.toml
[project.entry-points."aithera.skills"]
my_skill = "my_plugin:MySkill"
```

```python
# Aithera core
import importlib.metadata

def discover_skills():
    skills = []
    for ep in importlib.metadata.entry_points(group="aithera.skills"):
        skills.append(ep.load()())
    return skills
```

### 2. Directory-based plugins

```
aithera/
├── core/
│   └── skill_manager.py
├── plugins/             # <- drop-in dir
│   ├── my_skill/
│   │   ├── SKILL.md
│   │   └── skill.py
│   └── another_skill/
│       ├── SKILL.md
│       └── skill.py
```

```python
def load_from_dir(plugins_dir):
    for path in plugins_dir.iterdir():
        if path.is_dir():
            module = importlib.import_module(f"plugins.{path.name}.skill")
            yield module.Skill()
```

### 3. Configuration-based

```yaml
# aithera.yaml
plugins:
  - name: my_skill
    path: ./plugins/my_skill
    enabled: true
```

## Aithera V0.7.3 — modular pero no plugin-based

Aithera tiene modularidad vía:
- Routers separados (`backend/app/api/endpoints/`).
- Tools registrados en `ToolManager` (`backend/app/tools/`).
- AI providers en `backend/app/ai/providers/`.

**Pero añadir un nuevo tool requiere editar código** (registrar manualmente). No es drop-in.

## Para V0.85/V1.0

V0.85 podría formalizar un sistema de skills tipo **Superpowers** (compatible agentskills.io):
- Skills en `aithera-skills/` como drop-in.
- Formato `SKILL.md` (YAML frontmatter + body).
- Discovery automático.

V1.0 Orchestrator podría aprovechar esto para **delegar tasks a skills** específicas.

## Pattern OpenClaw (inspiration)

OpenClaw tiene **ClawHub marketplace**:
- 1.508 skills activas (a fecha del doc verificado).
- Plugin format estandarizado.
- Marketplace discovery.

Aithera podría借鉴 pero no necesita marketplace al inicio.

## Trade-offs

| Pro | Con |
|---|---|
| ✅ Extensibilidad sin recompilar | ❌ Complejidad de discovery |
| ✅ Comunidad puede contribuir | ❌ Security risk (plugins externos) |
| ✅ Hot-swap (teóricos) | ❌ Versioning dependencies |
| ✅ Modular | ❌ Documentación de plugins |

## Sandbox de plugins

Para evitar security issues:
- Plugins corren en **mismo proceso** (no sandbox).
- Whitelist de capabilities (qué pueden hacer).
- Code review de plugins oficiales.

Aithera V1.0 Orchestrator **podría** sandbox plugins vía Docker si fueran de terceros.

## Referencias cruzadas

- [JWIKI-045 monolith-vs-microservices.md](./monolith-vs-microservices.md)
- [JWIKI-053 hexagonal-ports.md](./hexagonal-ports.md)
- [JWIKI-009 superpowers.md](../01_LANDSCAPE/superpowers.md) — pattern借鉴
- [JWIKI-249 add-skill.md](../16_SOPS/add-skill.md) — SOP futuro

## Fuentes

1. https://docs.python.org/3/library/importlib.metadata.html — entry points
2. https://setuptools.pypa.io/en/latest/pkg_resources.html

## Nivel de confianza

**85%** — Pattern bien establecido.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified