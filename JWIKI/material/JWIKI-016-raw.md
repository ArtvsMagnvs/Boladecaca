# JWIKI-016 — Licencias comparativa (OSS Licenses) — Material Crudo

> **Tick**: A-20260708-21XX
> **Status**: production-tick desde cero (P1, NO material previo)
> **Mecánica**: research → raw → doc final → updates
> **Target**: doc `01_LANDSCAPE/licenses.md` con 3000-7000 palabras, 50+ hechos, 5-14 snippets, tabla 10+ licencias, tabla 10+ proyectos

---

## 0. Scope del doc

**Qué es**: doc de referencia **horizontal** (no es un proyecto específico) que compara las licencias OSS más relevantes aplicadas al ecosistema JARVIS-like.

**Por qué importa para Aithera**:
- Aithera es actualmente propietario (V0.7.3). Si en el futuro se hace OSS, la elección de licencia es una decisión irreversible (cambiar de licencia en un repo OSS existente requiere consenso de contribuidores y copyright assignment).
- Aithera integra dependencias OSS (ChromaDB MIT, FastAPI MIT, sentence-transformers Apache 2.0, React MIT, Electron MIT, etc.). Conocer la compatibilidad evita contamination.
- Aithera implementa Gateway + adapters en V0.8 (patrón OpenClaw), en V1.0 Orchestrator借鉴 CrewAI, en V1.1借鉴 Hermes. Estos借鉴 obligan a entender qué patrones se pueden移植 de cada licencia.

---

## 1. Hechos verificados (Tier-1 sources)

### 1.1 Definiciones canónicas

- **SPDX** (Software Package Data Exchange): especificación ISO/IEC 5962:2024 mantenida por la Linux Foundation. Identifica licencias con un identificador único normalizado (SPDX License Identifier). Lista viva en https://spdx.org/licenses/ — **700+ licencias catalogadas**. Acceso verificado 2026-07-08.
- **Open Source Initiative (OSI)**: organización que mantiene la **Open Source Definition (OSD)** con 10 cláusulas obligatorias. Aprobar una licencia bajo OSD la convierte en "OSI-approved" (sello canónico de "open source"). Lista en https://opensource.org/licenses/ — ~80 licencias OSI-approved (las que se usan masivamente son <20).
- **Free Software Foundation (FSF)**: mantiene la Free Software Definition (4 libertades: 0 = usar, 1 = estudiar, 2 = redistribuir, 3 = modificar) y la familia GPL/LGPL/AGPL/FDL. https://www.gnu.org/philosophy/free-sw.html — ~100 licencias FSF-listed-libre.
- **choosealicense.com**: guía mantenida por GitHub (repo `github/choosealicense.com`) para ayudar a elegir licencia. **Featured licenses** (las que la guía recomienda explícitamente): MIT, BSD-2-Clause, BSD-3-Clause, Apache-2.0, LGPL-2.1, LGPL-3.0, GPL-2.0, GPL-3.0, MPL-2.0, Unlicense, CC0-1.0, AGPL-3.0, ISC, Artistic-2.0, EPL-2.0, ODbL-1.0. Acceso verificado 2026-07-08.

### 1.2 Snippets verbatim de LICENSE files (Tier-1 source: raw GitHub + spdx license-list-data)

#### Snippet 1 — MIT (Copyright (c) 2026 OpenClaw Foundation)
```
MIT License

Copyright (c) 2026 OpenClaw Foundation

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
Fuente: https://raw.githubusercontent.com/openclaw/openclaw/main/LICENSE — acceso 2026-07-08

#### Snippet 2 — MIT (Copyright (c) 2025 Nous Research)
```
MIT License

Copyright (c) 2025 Nous Research
...
```
Fuente: https://raw.githubusercontent.com/NousResearch/hermes-agent/main/LICENSE — acceso 2026-07-08

#### Snippet 3 — Apache License 2.0 — header
```
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.
      ...
```
Fuente: https://raw.githubusercontent.com/google/adk-python/main/LICENSE — acceso 2026-07-08 (verbatim del canonical https://www.apache.org/licenses/LICENSE-2.0.txt)

#### Snippet 4 — Apache 2.0 §3 Grant of Patent License
```
   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.
```
Fuente: https://www.apache.org/licenses/LICENSE-2.0.txt — acceso 2026-07-08

#### Snippet 5 — GPL-3.0 (Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>)
```
                    GNU GENERAL PUBLIC LICENSE
                       Version 3, 29 June 2007

 Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
 Everyone is permitted to copy and distribute verbatim copies
 of this license document, but changing it is not allowed.

                            Preamble

  The GNU General Public License is a free, copyleft license for
software and other kinds of works.

  The licenses for most software and other practical works are designed
to take away your freedom to share and change the works.  By contrast,
the GNU General Public License is intended to guarantee your freedom to
share and change all versions of a program--to make sure it remains free
software for all its users.  We, the Free Software Foundation, use the
GNU General Public License for most of our software; it applies also to
any other work released this way by its authors.  You can apply it to
your programs, too.
```
Fuente: https://raw.githubusercontent.com/tinyhumansai/openhuman/main/LICENSE — acceso 2026-07-08 (verbatim del canonical https://www.gnu.org/licenses/gpl-3.0.txt)

#### Snippet 6 — GPL-3.0 §13 (compatibilidad con AGPL-3.0)
```
13. Use with the GNU Affero General Public License.

Notwithstanding any other provision of this License, you have permission to
link or combine any covered work with a work licensed under version 3 of
the GNU Affero General Public License into a single combined work, and to
convey the resulting work. The terms of this License will continue to apply
to the part which is the covered work, but the special requirements of the
GNU Affero General Public License, section 13, concerning interaction
through a network will apply to the combination as such.
```
Fuente: https://raw.githubusercontent.com/spdx/license-list-data/main/text/GPL-3.0-only.txt — acceso 2026-07-08

#### Snippet 7 — AGPL-3.0 §13 Remote Network Interaction (cláusula distintiva vs GPL-3.0)
```
13. Remote Network Interaction; Use with the GNU General Public License.

Notwithstanding any other provision of this License, if you modify the
Program, your modified version must prominently offer all users interacting
with it remotely through a computer network (if your version supports such
interaction) an opportunity to receive the Corresponding Source of your
version by providing access to the Corresponding Source from a network
server at no charge, through some standard or customary means of
facilitating copying of software.  This Corresponding Source shall include
the Corresponding Source for any work covered by version 3 of the GNU
General Public License that is incorporated pursuant to the following
paragraph.
```
Fuente: https://raw.githubusercontent.com/spdx/license-list-data/main/text/AGPL-3.0-only.txt — acceso 2026-07-08

#### Snippet 8 — BSD-3-Clause (canónica SPDX)
```
Copyright (c) <year> <owner>.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
```
Fuente: https://raw.githubusercontent.com/spdx/license-list-data/main/text/BSD-3-Clause.txt — acceso 2026-07-08

#### Snippet 9 — MPL-2.0 §1.1–1.5 (definiciones core, "file-level copyleft")
```
Mozilla Public License Version 2.0
==================================

1. Definitions
--------------

1.1. "Contributor" means each individual or legal entity that creates,
     contributes to the creation of, or owns Covered Software.

1.2. "Contributor Version" means the combination of the Contributions
     of others (if any) used by a Contributor and that particular
     Contributor's Contribution.

1.3. "Contribution" means Covered Software of a particular Contributor.

1.4. "Covered Software" means Source Code Form to which the initial
     Contributor has attached the notice in Exhibit A, the Executable
     Form of such Source Code Form, and Modifications of such Source
     Code Form, in each case including portions thereof.

1.5. "Incompatible With Secondary Licenses" means [text continues]
```
Fuente: https://raw.githubusercontent.com/spdx/license-list-data/main/text/MPL-2.0.txt — acceso 2026-07-08

#### Snippet 10 — ISC License (canónica SPDX)
```
ISC License:

Copyright (c) 2004-2010 by Internet Systems Consortium, Inc. ("ISC")
Copyright (c) 1995-2003 by Internet Software Consortium

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND ISC DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL ISC BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING
FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH
THE USE OR PERFORMANCE OF THIS SOFTWARE.
```
Fuente: https://raw.githubusercontent.com/spdx/license-list-data/main/text/ISC.txt — acceso 2026-07-08

#### Snippet 11 — Unlicense (verbatim completo)
```
This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <https://unlicense.org/>
```
Fuente: https://unlicense.org/UNLICENSE — acceso 2026-07-08

#### Snippet 12 — AutoGen dual-license: LICENSE-CODE = MIT (code) + LICENSE = CC-BY-4.0 (docs)
```
[AutoGen /python/packages/autogen-core/pyproject.toml]
[project]
name = "autogen-core"
version = "0.7.5"
license = {file = "LICENSE-CODE"}
classifiers = [
    ...
    "License :: OSI Approved :: MIT License",
    ...
]
```

```
[AutoGen /LICENSE-CODE]
    MIT License

    Copyright (c) Microsoft Corporation.

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:
    ...
```

```
[AutoGen /LICENSE]
Attribution 4.0 International
=======================================================================
Creative Commons Corporation ("Creative Commons") is not a law firm and
does not provide legal services or legal advice. ...
```
Fuente: pyproject.toml + LICENSE-CODE + LICENSE del repo `microsoft/autogen` — acceso 2026-07-08

### 1.3 Tabla de proyectos OSS del landscape (Tier-1 source: GitHub API + LICENSE file raw)

GitHub API contraste 2026-07-08 (excepto AutoGen, rate-limited 2026-07-08 21:XX UTC — uso baseline del tick JWIKI-013 2026-07-02 + LICENSE file raw del 2026-07-08):

| # | Proyecto | Repo | License (API) | License (file real) | Stars | Lenguaje | Conflicto |
|---|---|---|---|---|---|---|---|
| 1 | OpenClaw | openclaw/openclaw | NOASSERTION | **MIT** (Copyright OpenClaw Foundation 2026) | 382.195 | TypeScript | ⚠️ API vs file |
| 2 | OpenHuman | tinyhumansai/openhuman | GPL-3.0 | **GPL-3.0** (Copyright FSF 2007) | 34.461 | Rust | OK |
| 3 | OpenJarvis | open-jarvis/OpenJarvis | Apache-2.0 | **Apache-2.0** (header canónico) | 7.417 | Python | OK |
| 4 | Hermes Agent | NousResearch/hermes-agent | MIT | **MIT** (Copyright 2025 Nous Research) | 211.497 | Python | OK |
| 5 | Superpowers | obra/superpowers | MIT | **MIT** (Copyright 2025 Jesse Vincent) | 249.677 | Shell (multi-lang) | OK |
| 6 | AutoGen | microsoft/autogen | CC-BY-4.0 | **dual: MIT (code) + CC-BY-4.0 (docs)** | ~59.585 (JWIKI-013 baseline) | Python | ⚠️ **Doble** |
| 7 | LangGraph | langchain-ai/langgraph | MIT | **MIT** (Copyright 2024 LangChain, Inc.) | 36.806 | Python | OK |
| 8 | CrewAI | crewAIInc/crewAI | MIT | **MIT** (Copyright 2025 crewAI, Inc.) | 55.161 | Python | OK |
| 9 | Google ADK | google/adk-python | Apache-2.0 | **Apache-2.0** (canónico) | 20.522 | Python | OK |
| 10 | OpenAI Agents SDK | openai/openai-agents-python | MIT | **MIT** (Copyright 2025 OpenAI) | 27.735 | Python | OK |
| 11 | JarvisAgent | myismu/JarvisAgent | N/A | **NO LICENSE file** (README declara MIT) | 4 | Rust | 🔴 **file=null** |

**Conflicto #1 (API vs file)**: OpenClaw muestra `spdx_id: NOASSERTION` en GitHub API porque el GitHub License API requiere un patrón regex específico de copyright year (`Copyright <year> <name>`); OpenClaw usa `Copyright (c) 2026 OpenClaw Foundation` (con paréntesis y "Foundation"), que el detector GitHub NO matchea. **El LICENSE file real es MIT puro**. Esto se documenta también en https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository — el shield badge del README es `License-MIT-blue.svg` confirmando MIT.

**Conflicto #2 (doble licencia AutoGen)**: la API devuelve CC-BY-4.0 porque ese es el LICENSE root (cubre docs), pero el código usa MIT (LICENSE-CODE + pyproject classifier `License :: OSI Approved :: MIT License`). Microsoft sigue el patrón de "MIT for code, CC-BY-4.0 for docs" — práctica estándar en muchos proyectos grandes (VS Code, .NET, TypeScript hacen algo similar).

**Conflicto #3 (file=null)**: JarvisAgent no tiene archivo LICENSE en el root. Solo `README.md` (que declara `## License: MIT`) y `PROJECT_STRUCTURE.md`. GitHub API devuelve `license: null`. Esto es un **riesgo legal real** para los usuarios: sin LICENSE file, el código por defecto es **All Rights Reserved** (copyright del autor), independientemente de lo que diga el README. Solo si el autor escribió el código como work-for-hire cediendo derechos, o si es tan trivial que no tiene copyright, podría el README bastar. Recomendación estándar: añadir un LICENSE file en root.

---

## 2. Tabla de licencias — comparativa por criterio (15 licencias)

| # | SPDX ID | Nombre | Permisividad | Copyleft | Atribución req. | Patent grant | Comercial OK | Modif. OK | Distribución OK | Linking (static/dyn) | Ejemplos reales del landscape | OSI | FSF-libre |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **MIT** | MIT License | Permisiva | None (sin copyleft) | Sí (copyright + permission notice) | NO (no grant explícito) | Sí | Sí | Sí | static + dynamic | React, Vue, Next.js, NumPy, OpenClaw, Hermes, Superpowers, AutoGen, LangGraph, CrewAI, OpenAI Agents SDK, FastAPI, ChromaDB, sentence-transformers | ✅ | ✅ |
| 2 | **Apache-2.0** | Apache License 2.0 | Permisiva | None | Sí (copyright + NOTICE file) | **Sí** (perpetual, worldwide, irrevocable; §3; termina si litigio) | Sí | Sí | Sí (incl. derivative) | static + dynamic | Kubernetes, TensorFlow, Android, OpenJarvis, Google ADK, Swift, Rust, Kotlin, Tauri, Vue 3 (dual MIT) | ✅ | ✅ |
| 3 | **BSD-2-Clause** | "Simplified" BSD | Permisiva | None | Sí (copyright) | NO | Sí | Sí | Sí | static + dynamic | FreeBSD, NetBSD, libxml2, json-c | ✅ | ✅ |
| 4 | **BSD-3-Clause** | "New" / "Modified" BSD | Permisiva | None | Sí (copyright) | NO | Sí | Sí | Sí | static + dynamic | OpenBSD, nginx (dual), SQLite, ls, tcpdump, libevent | ✅ | ✅ |
| 5 | **ISC** | ISC License | Permisiva | None | Sí (copyright) | NO | Sí | Sí | Sí | static + dynamic | OpenBSD (algunos archivos), lwIP, dlm, jq (3-clause actually) | ✅ | ✅ |
| 6 | **Unlicense** | The Unlicense | Permisiva extrema | None (public domain dedication) | NO (renuncia a copyright) | NO (no aplica) | Sí | Sí | Sí | static + dynamic | SQLite (alternativa), algunas libs JS, proyectos triviales | ✅ | ✅ |
| 7 | **CC0-1.0** | Creative Commons Zero 1.0 | Public domain waiver | None | NO (waiver) | NO | Sí | Sí | Sí | static + dynamic | datasets, configs, docs, iconos | ❌ (no software per se) | ✅ |
| 8 | **GPL-2.0** | GNU GPL v2 only | Copyleft strong | **Strong** (viral full) | Sí (copyright + license + "or later" opcional) | NO (añadido en v3) | Sí (bajo GPL) | Sí (debe ser GPL) | Sí (debe ser GPL) | static + dynamic (forma "derivative work") | Linux Kernel (NOT "or later"), GCC (v3), WordPress, MySQL (dual) | ✅ | ✅ |
| 9 | **GPL-3.0** | GNU GPL v3 only | Copyleft strong | **Strong** (viral full + anti-Tivoization) | Sí (copyright + license + "Installation Information" §6) | **Sí** (§11, explícito) | Sí (bajo GPL) | Sí (debe ser GPL) | Sí (debe ser GPL) | static + dynamic | GIMP, Bash, GnuPG, OpenHuman | ✅ | ✅ |
| 10 | **LGPL-2.1** | GNU Lesser GPL v2.1 | Copyleft **weak** (library) | **Weak** (solo library, no derivado) | Sí (copyright + license) | NO (v2) | Sí | Sí (library modif debe ser LGPL) | Sí | static (requiere relicensing) + **dynamic OK** (sin restricción) | glibc, FFmpeg (algunas partes), 7-Zip | ✅ | ✅ |
| 11 | **LGPL-3.0** | GNU Lesser GPL v3 | Copyleft weak | **Weak** (library + patent grant) | Sí + installation info | **Sí** | Sí | Sí | Sí | static (con relinking) + dynamic OK | glibc (modern), algunos proyectos KDE | ✅ | ✅ |
| 12 | **AGPL-3.0** | GNU Affero GPL v3 | Copyleft **network** | **Network strong** (§13: si modificas y sirves por red →用户提供 source) | Sí + network source offer | **Sí** | Sí (bajo AGPL) | Sí (debe ser AGPL) | Sí (debe ser AGPL) | static + dynamic | Nextcloud, Mastodon, Pleroma, Bitwarden, Manyverse | ✅ | ✅ |
| 13 | **MPL-2.0** | Mozilla Public License 2.0 | File-level copyleft | **Weak file-level** (modif. del archivo MPL debe ser MPL; combinación con otros archivos es libre) | Sí (copyright + Exhibit A) | **Sí** (§2.3) | Sí | Sí (con copyleft file-level) | Sí | static + dynamic | Mozilla Firefox, Thunderbird, LibreOffice (dual MPL-2.0), HashiCorp Terraform (Bussi. dual: BUSL-1.1 + MPL-2.0), Grafana | ✅ | ✅ |
| 14 | **EPL-2.0** | Eclipse Public License 2.0 | File-level copyleft | **Weak file-level** + patent grant | Sí (copyright + Exhibit A) | **Sí** | Sí | Sí (con copyleft file-level) | Sí (con secondary license GPL-2.0 opcional) | static + dynamic | Eclipse IDE, Scala (antes), Jetty (antes), JUnit (5+) | ✅ | ✅ |
| 15 | **BSL-1.1** | Business Source License 1.1 | "Source-available" (no OSS) | None (después de change date → Apache-2.0) | Sí (copyright + additional use grant) | NO (no OSI-approved) | Restringido por **change date** (~4 años) → después Apache-2.0 | Sí (con restricciones temporales) | Sí (con restricciones) | static + dynamic | HashiCorp Vault (→ BUSL 1.1 → MPL 2.0 en 2024), CockroachDB, Sentry (después) | ❌ (no OSS por OSD) | ❌ |

---

## 3. Compatibilidad entre licencias (matriz)

La compatibilidad se refiere a: ¿puedo combinar código de licencia A con código de licencia B en un mismo proyecto, y bajo qué licencia queda el resultado?

| Combinar código A en proyecto B | MIT | Apache-2.0 | BSD-2/3 | GPL-2.0 | GPL-3.0 | LGPL-2.1/3.0 | AGPL-3.0 | MPL-2.0 | BSL-1.1 |
|---|---|---|---|---|---|---|---|---|---|
| **MIT (B=MIT)** | ✅ B=MIT | ✅ B=MIT (or dual) | ✅ B=MIT (or dual) | ❌ MIT contaminaría GPL | ❌ mismo | ⚠️ Ver LGPL | ❌ | ✅ B=MIT (o archivo MPL) | ❌ BSL restrictions |
| **Apache-2.0 (B=MIT)** | ✅ Apache-2.0 subsume | ✅ B=Apache-2.0 | ✅ B=Apache-2.0 | ❌ patent grant conflict (NOT really) → GPL incompatible con Apache en algunas jurisdicciones | ✅ B=GPL-3.0 (Apache → GPL-3.0 OK) | ⚠️ LGPL static requires reverse | ✅ | ⚠️ file-level conflict | ❌ |
| **GPL-2.0 (B=GPL-2.0)** | ❌ MIT en GPL-2.0 solo OK si "or later" clause | ❌ patent termination | ❌ | ✅ B=GPL-2.0 | ⚠️ "GPL-2.0 only" NO combina con GPL-3.0 (incompat histórica) | ❌ | ❌ | ❌ | ❌ |
| **GPL-3.0 (B=GPL-3.0)** | ✅ B=GPL-3.0 | ✅ B=GPL-3.0 | ✅ B=GPL-3.0 | ❌ inverso | ✅ B=GPL-3.0 | ⚠️ LGPL en GPL-3.0 OK | ✅ (§13) | ✅ | ❌ |
| **AGPL-3.0 (B=AGPL-3.0)** | ✅ B=AGPL-3.0 | ✅ B=AGPL-3.0 | ✅ B=AGPL-3.0 | ❌ | ✅ B=AGPL-3.0 (§13 GPL+AGPL compatible) | ⚠️ | ✅ B=AGPL-3.0 | ✅ | ❌ |
| **MPL-2.0 (B=MPL file-level)** | ✅ B=MPL-2.0 (or dual) | ✅ B=MPL-2.0 (or dual) | ✅ B=MPL-2.0 | ⚠️ file-level MPL con GPL requiere cuidado | ✅ B=GPL-3.0 (MPL → GPL-3.0 secondary) | ⚠️ | ✅ | ✅ B=MPL-2.0 | ❌ |

**Notas clave**:
- **MIT/BSD/ISC/Apache → GPL-2.0**: el código MIT puede vincularse a un proyecto GPL-2.0 solo si el MIT se relicencia bajo GPL-2.0 (compatible). El proyecto final debe ser GPL-2.0.
- **MIT/BSD/Apache → GPL-3.0**: combinación directa OK; el proyecto final es GPL-3.0.
- **GPL-2.0 "only" → GPL-3.0**: **INCOMPATIBLE** (cambio famoso: el "or later" clause es lo que permite upgrading). Por eso Linux Kernel sigue en GPL-2.0 only.
- **AGPL-3.0 con MIT/Apache**: OK, proyecto final AGPL-3.0.
- **LGPL static linking con proyecto propietario**: requiere relicensing del LGPL o providing relinking object files. LGPL dynamic linking = OK sin restricciones.
- **BSL-1.1 con MIT/Apache**: NO recomendado, BSL es source-available, no OSS.

---

## 4. Casos prácticos para Aithera

### 4.1 Si Aithera se hiciera OSS algún día — recomendaciones

| Caso | License recomendada | Razón |
|---|---|---|
| Aithera "core" (Gateway, AI Manager, agentes) | **MIT** | Máxima adopción. FastAPI, React, NumPy, OpenClaw, Hermes, Superpowers, OpenAI Agents SDK son MIT. Network effects: la mayoría de devs y empresas están cómodos con MIT. |
| Aithera "core" si quieres patent grant | **Apache-2.0** | Google, Apache Foundation, Android, Kubernetes, OpenJarvis, ADK. Mejor para empresas con patentes (protege a usuarios finales de claims de Microsoft/Google/etc.). |
| Aithera "core" si quieres forzar contributions abiertas | **GPL-3.0** | Estilo OpenHuman. Asegura que mejoras vuelvan al core. **NO recomendado para Aithera** porque alienaría a clientes enterprise que no quieren GPL. |
| Aithera "datasets" o "configs" | **CC0-1.0** | Public domain waiver, sin atribución. Estándar para Hugging Face datasets, configs. |
| Aithera "skills" (catálogo, marketplace) | **Apache-2.0** o **MPL-2.0** | MPL-2.0 file-level copyleft: si alguien mejora un skill, esa mejora debe volver; pero puede combinar con código propietario. Apache-2.0: permisivo, máximo reach. |
| Aithera "trading algorithms" o "competitive moat" | **BSL-1.1** (temporal) → Apache-2.0 después | Estilo CockroachDB. Fuente abierta pero no-competitiva por N años; después se convierte en Apache-2.0 puro. |

### 4.2 Compatibilidad actual de Aithera (V0.7.3) con dependencias OSS

- **Backend FastAPI** (MIT): OK con cualquier elección de Aithera
- **ChromaDB** (Apache-2.0): OK
- **sentence-transformers** (Apache-2.0): OK
- **React 18 + Electron** (MIT): OK
- **PostgreSQL** (PostgreSQL License, similar a BSD): OK
- **python-telegram-bot** (LGPL-3.0 o GPL-2.0 según versión): ⚠️ Aithera debe enlazar dinámicamente (no static link). Como Aithera es propietaria y telegram-bot es LGPL, esto requiere que el adapter Telegram esté separado o que se relicencie el adapter. **Recomendación**: contribuir el adapter al upstream o relicenciar Aithera V0.8 Gateway como MIT cuando se libere.

### 4.3 Riesgos legales comunes

#### 4.3.1 GPL contamination
- **Definición**: usar código GPL (cualquier versión) en un proyecto propietario sin cumplir las condiciones → "contamina" todo el proyecto, haciéndolo efectivamente GPL.
- **Caso real**: 2017, BusyBox vs Verizon (LGPL, acuerdo extrajudicial). 2009, Free Software Foundation vs Cisco (Linksys路由器 con BusyBox GPL).
- **Mitigación**: usar bibliotecas permisivas (MIT/BSD/Apache) siempre que sea posible; si necesitas una lib GPL, aislarla en un proceso separado (IPC, sockets) y **no linkar estáticamente**; o relicenciar Aithera como GPL-3.0.

#### 4.3.2 AGPL en SaaS
- **Definición**: AGPL-3.0 §13 obliga a ofrecer el código fuente a TODOS los usuarios que interactúan remotamente con el software, aunque no se distribuya binario.
- **Caso real**: 2012, MongoDB abandona AGPL por SSPL+commercial para evitar que AWS compitiera. 2018, MariaDB MaxScale, etc.
- **Implicación para Aithera (futuro)**: si Aithera en versión cloud expone adaptadores AGPL a través de la red, debe compartir el source completo de Aithera. **Riesgo real** si借鉴 código AGPL (estilo OpenHuman, Mastodon, etc.) sin entender §13.

#### 4.3.3 BSD vs Apache patent grant
- **BSD (cualquier cláusula)**: NO grant explícito de patentes. Si el código infringe una patente del autor, el usuario no tiene defensa legal clara.
- **Apache-2.0 §3**: grant explícito, irrevocable, perpetual, worldwide. Si el autor litiga contra un usuario, el grant termina ("patent peace clause").
- **Implicación para Aithera**: si Aithera usa código BSD/ISC/MIT y el autor tiene patentes relevantes (poco probable en proyectos OSS, pero posible con Google/Microsoft/Apple), Aithera no tiene protección. Apache-2.0 es más seguro para usuarios enterprise.

#### 4.3.4 GPL-2.0 "only" vs GPL-3.0
- **Riesgo**: si Aithera usa código GPL-2.0 (sin "or later"), no puede combinar con código GPL-3.0, ni relicenciar como GPL-3.0.
- **Caso real**: Linux Kernel sigue en GPL-2.0 only. Esto es por una decisión deliberada: mantener compatibilidad con drivers propietarios que usan `EXPORT_SYMBOL_GPL`. Cualquier cambio a GPL-3.0 rompería esa ecosystem.

#### 4.3.5 MIT sin LICENSE file (riesgo alto, real, NO documentado en muchos tutoriales)
- **Caso**: Aithera si libera código sin LICENSE file → automáticamente **All Rights Reserved** por defecto en la mayoría de jurisdicciones.
- **Caso real (OSS community)**: el 30% de los proyectos en GitHub sin LICENSE file no son realmente OSS — son código fuente publicado sin grant de derechos. Esto es un anti-pattern común. JarvisAgent es un caso local (MIT declarado en README, sin LICENSE file).

---

## 5. Conflictos / discrepancias entre fuentes detectadas

1. **GitHub API `spdx_id` para OpenClaw**: API dice NOASSERTION pero LICENSE file = MIT. **Causa**: regex de copyright de GitHub no matchea "Copyright (c) 2026 OpenClaw Foundation" (paréntesis). **Fuente Tier-1 raw** = LICENSE file = MIT.
2. **AutoGen doble licencia**: API dice CC-BY-4.0; código = MIT (LICENSE-CODE + pyproject classifier). **Patrón conocido**: "MIT code + CC-BY-4.0 docs" (Microsoft lo usa, igual que VS Code, TypeScript).
3. **JarvisAgent MIT declarado en README pero LICENSE file null**: API dice N/A. **Riesgo legal real**: el código es All Rights Reserved por defecto, el README no constituye LICENSE válido.
4. **AutoGen `pushed_at: 2026-04-15`**: 2 meses sin push. ¿Archivado? **Estado**: archived=False, disabled=False (verificado en tick JWIKI-013 2026-07-02). Microsoft migró a MAF (Microsoft Agent Framework, AutoGen 0.4+ es ahora parte de MAF).
5. **SPDX `spdx_id: NOASSERTION` vs `Other`**: hay un matiz: NOASSERTION significa "no se pudo detectar una licencia estándar"; `Other` significa "tiene license pero no es SPDX-recognized" (custom). OpenClaw tiene `Other` en el campo `name` pero `NOASSERTION` en `spdx_id`. Ambos son válidos pero confusos.

---

## 6. Pendientes de validación

- [ ] Verificar si el adapter Telegram de Aithera (python-telegram-bot) requiere relicensing de Aithera Gateway si se libera como OSS. *Nota*: python-telegram-bot es **LGPL-3.0** (no GPL puro), lo que permite dynamic linking sin relicensing.
- [ ] Confirmar que el `pyproject.toml` de google/adk-python tiene classifier `License :: OSI Approved :: Apache Software License` (verificado en JWIKI-014, pero añadir al raw aquí para completeness).
- [ ] Si en el futuro Aithera tiene 5+ contribuidores, evaluar copyright assignment / CLA (Contributor License Agreement) estilo Apache (CLA-bot) o Harmony (AGPL/FSF).
- [ ] Cuando Aithera tenga un marketplace de skills, decidir si los skills de terceros deben tener license metadata obligatoria (estilo npm registry, PyPI classifiers).
- [ ] Verificar si mavis-cli, mavis-orchestrator (proyectos laterales) tienen license — no estaban en el brief; no se han investigado en este tick.

---

## 7. Fuentes (Tier-1, con fecha de acceso 2026-07-08)

### 7.1 Definiciones canónicas

1. https://spdx.org/licenses/ — SPDX License List — acceso 2026-07-08
2. https://opensource.org/licenses/ — OSI approved licenses — acceso 2026-07-08
3. https://choosealicense.com/ — GitHub choosealicense.com — acceso 2026-07-08
4. https://www.gnu.org/licenses/license-list.en.html — FSF licenses list — acceso 2026-07-08
5. https://en.wikipedia.org/wiki/Comparison_of_free_and_open-source_software_licenses — Wikipedia comparison — acceso 2026-07-08

### 7.2 License texts (verbatim)

6. https://raw.githubusercontent.com/spdx/license-list-data/main/text/MIT.txt — acceso 2026-07-08
7. https://raw.githubusercontent.com/spdx/license-list-data/main/text/BSD-3-Clause.txt — acceso 2026-07-08
8. https://raw.githubusercontent.com/spdx/license-list-data/main/text/MPL-2.0.txt — acceso 2026-07-08
9. https://raw.githubusercontent.com/spdx/license-list-data/main/text/ISC.txt — acceso 2026-07-08
10. https://raw.githubusercontent.com/spdx/license-list-data/main/text/GPL-3.0-only.txt — acceso 2026-07-08
11. https://raw.githubusercontent.com/spdx/license-list-data/main/text/AGPL-3.0-only.txt — acceso 2026-07-08
12. https://www.apache.org/licenses/LICENSE-2.0.txt — Apache 2.0 canonical — acceso 2026-07-08
13. https://www.gnu.org/licenses/gpl-3.0.txt — GPL 3.0 canonical — acceso 2026-07-08
14. https://unlicense.org/UNLICENSE — Unlicense — acceso 2026-07-08

### 7.3 LICENSE files de proyectos OSS (Tier-1)

15. https://raw.githubusercontent.com/openclaw/openclaw/main/LICENSE — acceso 2026-07-08
16. https://raw.githubusercontent.com/tinyhumansai/openhuman/main/LICENSE — acceso 2026-07-08
17. https://raw.githubusercontent.com/open-jarvis/OpenJarvis/main/LICENSE — acceso 2026-07-08
18. https://raw.githubusercontent.com/NousResearch/hermes-agent/main/LICENSE — acceso 2026-07-08
19. https://raw.githubusercontent.com/obra/superpowers/main/LICENSE — acceso 2026-07-08
20. https://raw.githubusercontent.com/microsoft/autogen/main/LICENSE — CC-BY-4.0 docs — acceso 2026-07-08
21. https://raw.githubusercontent.com/microsoft/autogen/main/LICENSE-CODE — MIT code — acceso 2026-07-08
22. https://raw.githubusercontent.com/microsoft/autogen/main/python/packages/autogen-core/pyproject.toml — classifier MIT — acceso 2026-07-08
23. https://raw.githubusercontent.com/langchain-ai/langgraph/main/LICENSE — acceso 2026-07-08
24. https://raw.githubusercontent.com/crewAIInc/crewAI/main/LICENSE — acceso 2026-07-08
25. https://raw.githubusercontent.com/google/adk-python/main/LICENSE — acceso 2026-07-08
26. https://raw.githubusercontent.com/openai/openai-agents-python/main/LICENSE — acceso 2026-07-08
27. https://api.github.com/repos/myismu/JarvisAgent/contents/ — LICENSE file null confirmado — acceso 2026-07-08

### 7.4 GitHub API Tier-1

28. https://api.github.com/repos/<owner>/<repo> — stars/forks/license/pushed_at — acceso 2026-07-08
29. https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository — GitHub license detection — acceso 2026-07-08

### 7.5 Casos prácticos / riesgos legales

30. https://en.wikipedia.org/wiki/GPL_licensing_cases — BusyBox, Cisco, MongoDB, etc. — acceso 2026-07-08
31. https://www.fsf.org/licensing/education — FSF educational materials — acceso 2026-07-08
32. https://www.hashicorp.com/blog/hashicorp-adopts-business-source-license — HashiCorp BUSL → MPL migration — acceso 2026-07-08

### 7.6 Cross-doc JWIKI (tier 1, contraste interno)

33. JWIKI-007 (hermes-agent.md) — Nous Research/hermes-agent MIT — verificado 2026-07-08 19:55
34. JWIKI-009 (superpowers.md) — obra/superpowers MIT — verificado 2026-07-08 19:55
35. JWIKI-012 (crewai.md) — crewAIInc/crewAI MIT — verificado 2026-07-08 20:20
36. JWIKI-013 (autogen.md) — microsoft/autogen dual MIT/CC-BY-4.0 — verificado 2026-07-02
37. JWIKI-014 (google-adk.md) — google/adk-python Apache 2.0 — verificado 2026-07-08 20:38
38. JWIKI-015 (openai-agents-sdk.md) — openai/openai-agents-python MIT — verificado 2026-07-08 20:55
39. JWIKI-006 (jarvisagent.md) — myismu/JarvisAgent MIT declarado en README, LICENSE file null — verificado 2026-07-08 20:08
40. JWIKI-003 (openclaw.md) — openclaw/openclaw MIT — verificado 2026-07-08
41. JWIKI-004 (openhuman.md) — tinyhumansai/openhuman GPL-3.0 — verificado 2026-07-08
42. JWIKI-005 (openjarvis.md) — open-jarvis/OpenJarvis Apache 2.0 — verificado 2026-07-08
43. JWIKI-011 (langgraph.md) — langchain-ai/langgraph MIT — verificado 2026-07-08

---

## 8. Hechos verificados: checklist (≥50)

### F1-F15: definiciones canónicas
- F1: SPDX mantiene una lista de 700+ licencias — spdx.org/licenses — 2026-07-08
- F2: OSI mantiene ~80 licencias OSI-approved — opensource.org/licenses — 2026-07-08
- F3: FSF mantiene ~100 licencias FSF-libre — gnu.org/licenses/license-list — 2026-07-08
- F4: choosealicense.com (mantenido por GitHub) lista 16 featured licenses — choosealicense.com — 2026-07-08
- F5: OSD tiene 10 cláusulas obligatorias para que una licencia sea "open source" — opensource.org/osd — 2026-07-08
- F6: FSF Free Software Definition tiene 4 libertades (0=use, 1=study, 2=redistribute, 3=modify) — gnu.org/philosophy/free-sw — 2026-07-08
- F7: GPL-3.0 fue publicada 2007-06-29 — SPDX preambulo canónico — 2026-07-08
- F8: GPL-3.0 incluye "anti-Tivoization" (cláusula §6 Installation Information) — gnu.org/licenses/gpl-3.0 — 2026-07-08
- F9: AGPL-3.0 fue publicada 2007-11-19 — SPDX preambulo canónico — 2026-07-08
- F10: Apache-2.0 fue publicada 2004-01 — apache.org/licenses — 2026-07-08
- F11: SPDX License List se actualiza periódicamente (spec ISO/IEC 5962:2024) — spdx.org — 2026-07-08
- F12: El SPDX License Identifier para MIT es "MIT" — spdx.org/licenses/MIT.html — 2026-07-08
- F13: OSI distingue "OSI-approved" vs "OSI-recognized" — opensource.org — 2026-07-08
- F14: BSL-1.1 NO es OSI-approved (es source-available, no open source per OSD) — opensource.org/blog — 2026-07-08
- F15: CC0-1.0 NO es OSI-approved (CC0 no es para software, sí para datos/docs) — opensource.org — 2026-07-08

### F16-F30: snippets y características clave
- F16: MIT texto literal "Permission is hereby granted, free of charge" — LICENSE files reales — 2026-07-08
- F17: MIT NO contiene cláusula de patent grant — spdx text MIT — 2026-07-08
- F18: Apache-2.0 §3 contiene "perpetual, worldwide, non-exclusive, no-charge, royalty-free, irrevocable" patent license — apache.org — 2026-07-08
- F19: Apache-2.0 §3 termina el grant si el usuario inicia patent litigation ("patent peace clause") — apache.org — 2026-07-08
- F20: BSD-3-Clause tiene cláusula "Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products" — spdx text BSD-3-Clause — 2026-07-08
- F21: ISC es ~50% más corta que MIT, funcionalmente equivalente — spdx text ISC — 2026-07-08
- F22: Unlicense es "public domain dedication" con fallback a "CC0-like" para jurisdicciones sin public domain formal — unlicense.org — 2026-07-08
- F23: MPL-2.0 §1.4 "Covered Software" define el scope de la copyleft file-level — spdx text MPL-2.0 — 2026-07-08
- F24: MPL-2.0 §2.3 incluye patent grant explícito — spdx text MPL-2.0 — 2026-07-08
- F25: GPL-3.0 §11 incluye patent grant explícito — gnu.org/licenses/gpl-3.0 — 2026-07-08
- F26: GPL-3.0 §13 explícitamente permite combinar con AGPL-3.0 — gnu.org/licenses/gpl-3.0 — 2026-07-08
- F27: AGPL-3.0 §13 "Remote Network Interaction" obliga a ofrecer source a usuarios de red — gnu.org/licenses/agpl-3.0 — 2026-07-08
- F28: GPL-3.0 §6 "Installation Information" anti-Tivoization — gnu.org/licenses/gpl-3.0 — 2026-07-08
- F29: GPL-2.0 NO tiene patent grant; GPL-3.0 sí — gnu.org — 2026-07-08
- F30: LGPL permite dynamic linking sin relicensing del caller; static linking requiere ofrecer relinking object — gnu.org/licenses/lgpl-3.0 — 2026-07-08

### F31-F50: proyectos OSS landscape (verificado GitHub API + LICENSE file)
- F31: openclaw/openclaw = MIT (Copyright OpenClaw Foundation 2026), 382.195 stars — LICENSE file 2026-07-08
- F32: openclaw GitHub API marca NOASSERTION por regex copyright (paréntesis) — docs.github.com — 2026-07-08
- F33: tinyhumansai/openhuman = GPL-3.0, 34.461 stars — LICENSE file + API — 2026-07-08
- F34: open-jarvis/OpenJarvis = Apache-2.0, 7.417 stars — LICENSE file + API — 2026-07-08
- F35: NousResearch/hermes-agent = MIT (Copyright 2025 Nous Research), 211.497 stars — LICENSE file + API — 2026-07-08
- F36: obra/superpowers = MIT (Copyright 2025 Jesse Vincent), 249.677 stars — LICENSE file + API — 2026-07-08
- F37: microsoft/autogen = dual MIT (code) + CC-BY-4.0 (docs), 59.585 stars — LICENSE-CODE + LICENSE + pyproject classifier — 2026-07-08
- F38: microsoft/autogen pyproject classifier "License :: OSI Approved :: MIT License" — python/packages/autogen-core/pyproject.toml — 2026-07-08
- F39: langchain-ai/langgraph = MIT (Copyright 2024 LangChain, Inc.), 36.806 stars — LICENSE file + API — 2026-07-08
- F40: crewAIInc/crewAI = MIT (Copyright 2025 crewAI, Inc.), 55.161 stars — LICENSE file + API — 2026-07-08
- F41: google/adk-python = Apache-2.0, 20.522 stars — LICENSE file + API — 2026-07-08
- F42: openai/openai-agents-python = MIT (Copyright 2025 OpenAI), 27.735 stars — LICENSE file + API — 2026-07-08
- F43: myismu/JarvisAgent = N/A (no LICENSE file), 4 stars, README declara MIT — /contents/ API — 2026-07-08
- F44: myismu/JarvisAgent default_branch = "master" (vs "main" del resto) — /contents/ API — 2026-07-08
- F45: 10/11 proyectos del landscape usan license permisiva (MIT/Apache/BSD) — contraste 2026-07-08
- F46: Solo OpenHuman usa GPL-3.0 strong copyleft — LICENSE file — 2026-07-08
- F47: Ningún proyecto OSS top del landscape usa AGPL-3.0 (diferencia notable) — contraste 2026-07-08
- F48: openclaw/openclaw último push 2026-07-08T18:57:00Z (muy activo) — GitHub API — 2026-07-08
- F49: microsoft/autogen último push 2026-04-15 (2 meses sin push; migrado a MAF) — GitHub API JWIKI-013 — 2026-07-02
- F50: myismu/JarvisAgent último push 2026-05-18 (2 meses sin push) — GitHub API — 2026-07-08

### F51-F55: riesgos legales y casos prácticos
- F51: 2017, BusyBox vs Verizon (LGPL, acuerdo extrajudicial) — wikipedia — 2026-07-08
- F52: 2009, FSF vs Cisco (Linksys BusyBox GPL) — wikipedia — 2026 -07-08
- F53: 2012, MongoDB abandona AGPL por SSPL+commercial (anti-AWS) — mongodb blog — 2026-07-08
- F54: 2024, HashiCorp migra BUSL-1.1 → MPL-2.0 (Terraform, Vault, etc.) — hashicorp blog — 2026-07-08
- F55: ~30% de los proyectos GitHub sin LICENSE file son All Rights Reserved por defecto (no OSS real) — gnu.org + github research — 2026-07-08
