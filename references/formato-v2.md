# Formato de agentes — PREVIEW v2 (NO es la doc estable)

> **ADVERTENCIA**: esta referencia documenta la **preview** en https://opencode.ai/v2/docs/agents/ + https://opencode.ai/v2/docs/permissions/ + https://opencode.ai/v2/docs/config (verificado 30/09/2026). La **documentacion oficial estable en espanol** (https://opencode.ai/docs/es/agents/) usa un esquema DIFERENTE (`permission:` mapa, acciones `bash`/`task`, campo `disable`, JSON `agent:` singular, default `mode: all`) y es la **normativa** de esta skill: ver `references/formato-v1.md`. Usar este formato SOLO cuando se haya verificado que el binario instalado (serie 2.x) lo requiere; la preview puede cambiar. El validador marca los archivos con `permissions:` lista como no conformes a la doc estable.

Contrastes clave preview vs doc estable: `permissions:` (lista) vs `permission:` (mapa); accion `shell` vs `bash`; accion `subagent` vs `task`; `disabled` vs `disable`; JSON `agents:` vs `agent:`; default `mode: primary` vs `all`; `temperature`/`top_p`/`prompt`/`tools`/`maxSteps` **prohibidos** en preview pero **validos** (o deprecados) en estable; `color` solo hex en preview vs hex o tema en estable; built-in `scout` no existe en preview pero SI en estable.

## Estructura del archivo

```markdown
---
description: Obligatoria en subagentes (la ve el modelo que decide a quien lanzar).
mode: primary | subagent | all        # default en v2: primary
model: provider/model#variante        # p. ej. anthropic/claude-sonnet-4-5#high
                                    # en JSON tambien forma extendida:
                                    #   model: { providerID, model, variant }
steps: 8                              # maximo positivo de pasos; en el ultimo quita herramientas y pide resumen; entrada nueva del usuario reinicia el conteo
hidden: true                          # quita de listings, descubrimiento y catalogo de subagentes (visibilidad, NO seguridad)
color: "#ff6b6b"                      # solo hex de 6 digitos
disabled: true                        # elimina el agente (built-in o custom) en este punto de la carga
permissions:                          # LISTA ORDENADA de reglas
  - { action: "*", resource: "*", effect: deny }
  - { action: read, resource: "src/**", effect: allow }
request:                              # overlay de headers/body (AVISO: el runner v2 aun NO los envia)
  headers: { x-agent: reviewer }
  body: { temperature: 0.1 }
---

El cuerpo markdown = system prompt (reemplaza el prompt base del provider; instrucciones de proyecto, skills y references se agregan igual).
```

En JSON: clave top-level `agents:` (PLURAL) y campo `system:` para el prompt. El frontmatter (`.md`) acepta los mismos campos que una entrada `agents:`; los documentados en la doc oficial son: `description`, `mode`, `model`, `system`, `permissions`, `steps`, `hidden`, `color`, `disabled`, `request` (la doc v2 NO lista un campo `name`: el ID viene del nombre de archivo / clave JSON). En un `.md` la doc recomienda usar el CUERPO como system prompt en lugar del campo `system:` en frontmatter.

- Subagente sin `model`: hereda el modelo de la sesion padre; con `model`: usa el suyo.
- La sesion guarda SU modelo seleccionado por separado: elegir un agente primary por ID NO cambia el modelo de la sesion.

## permissions (v2) — lista de reglas {action, resource, effect}

| Campo | Significado |
|---|---|
| `action` | herramienta/accion; comodines soportados. Es un string abierto: plugins pueden definir mas acciones |
| `resource` | ruta, comando, URL, query, ID de skill/agente u otro valor segun la accion; comodines soportados |
| `effect` | `allow` / `ask` / `deny` |

**La ultima regla que coincide gana** → amplias primero, excepciones al final. Si NINGUNA regla coincide, el resultado es `ask`.

Acciones built-in y su recurso (doc de permissions v2):

| Accion | Recurso |
|---|---|
| `read` | ruta interna relativa o ruta externa canonica absoluta |
| `edit` | ruta objetivo de `edit`/`write`/`patch` |
| `glob` | patron glob solicitado |
| `grep` | expresion regular solicitada (NO la ruta de busqueda) |
| `shell` | string de comando generado por el scanner (comandos compuestos pueden producir varios) |
| `subagent` | ID del agente hijo |
| `skill` | ID de la skill |
| `question` | `*` |
| `webfetch` | URL solicitada |
| `websearch` | consulta de busqueda |
| `external_directory` | directorio externo canonico, normalmente termina en `/*` |
| `<servidor>_<herramienta>` | `*` para una herramienta MCP (caracteres no admitidos se convierten en `_`) |
| `execute` | `*`; habilita/deshabilita Code Mode (las herramientas internas aplican sus propias reglas) |
| `*` | comodin sobre todas las acciones |

**`lsp` y `doom_loop` NO son acciones del core v2** (excluidas explicitamente por la doc). `todowrite` y `list` tampoco aparecen en la tabla v2 (verificar si alguna version los reintroduce).

Matching:

- `*` casa cero o mas caracteres **incluido `/`**; `?` casa exactamente uno; resto literal.
- Rutas: backslashes se normalizan a `/`; en Windows el matching es case-insensitive; el patron casa la ruta normalizada completa.
- Un patron `shell` terminado en ` *` tambien casa el comando sin argumentos (`"git status *"` casa `git status` y `git status --short`).
- Orden de combinacion: configs de menor prioridad primero → reglas globales `permissions:` anexadas → reglas del agente anexadas al final.
- Operaciones multi-recurso (p. ej. un patch con varios archivos): cualquier `deny` deniega; si no, cualquier `ask` pregunta; si no, allow.

Politica base (todo agente, incluidos custom, arranca con esto ANTES de sus reglas):

```jsonc
[
  { "action": "*", "resource": "*", "effect": "allow" },
  { "action": "external_directory", "resource": "*", "effect": "ask" },
  { "action": "read", "resource": "*.env", "effect": "ask" },
  { "action": "read", "resource": "*.env.*", "effect": "ask" },
  { "action": "read", "resource": "*.env.example", "effect": "allow" }
]
```

Reglas globales/del agente pueden pisar esa base (p. ej. `{"action":"*","resource":"*","effect":"deny"}` como primera regla del agente = negar todo y re-allow selectivo).

Recursos con expansion de home:

- `read`, `edit`, `external_directory` → `~`, `~/`, `$HOME`, `$HOME/` se expanden al cargar la config (p. ej. `~/notes/**`).
- `shell` → texto de comando crudo, SIN expansion.

Rutas fuera del Location/worktree del proyecto necesitan aprobacion `external_directory` ANTES del propio `read`/`edit` (aplica a `read`, `edit`, `write`, `patch`). `shell` comprueba su directorio de trabajo externo y los directorios inferidos por su scanner ANTES de casar los recursos `shell`; la inferencia es best-effort, y `shell` corre con la autoridad del usuario del host — la doc recomienda allowlists estrechas en lugar de patrones que pretendan reconocer todo comando peligroso.

Control de delegacion: los permisos `subagent` del PADRE deciden que hijos puede lanzar; cada hijo corre con SUS propios permisos (no un subconjunto de los del padre). Subagentes corren con contexto fresco, en sesiones hijas de primer plano o background.

Respuestas a `ask` en clientes: `once` (una vez), `always` (guarda el patron propuesto por la herramienta como regla allow **persistente a nivel proyecto** — nunca pisa un `deny` configurado; revisarlas periodicas. Quien propone el patron guardado varia: algunas herramientas proponen `*`, `shell` propone prefijos de comando, `skill`/`subagent` proponen su ID), `reject` (rechaza y descarta el resto de pendientes de la sesion). Ademas, `experimental.policies` puede hard-deny una comprobacion de permiso (convierte allow/ask en deny; nunca otorga; las politicas globales/de Console pisan la config de proyecto).

Excepciones base de `external_directory`: opencode permite acceso a sus directorios gestionados de tool-output, shell-output, temporales y config global (la accion `read`/`edit` subyacente sigue sus propias reglas).

Scanner de shell: `experimental.portable_shell_scanner: true` reemplaza el scanner tree-sitter por el portable (NO es segundo opinion: seleccion de parser). Un comando que el scanner portable no analiza devuelve ERROR de scanner, no un deny. Las reglas, patrones guardados y inferencia de directorios siguen aplicando igual.

## Campos LEGACY PROHIBIDOS en v2

`temperature`, `top_p`, `prompt`, `permission` (mapa), `tools`, `disable`, `maxSteps`. Usar en su lugar: `request.body.*` (con el aviso de que el runner aun no lo envia; preferir configuracion a nivel provider/modelo/variante), `system`, `permissions`, `disabled`, `steps`.

## Merge (v2)

- Las definiciones se fusionan en orden de carga; escalares posteriores reemplazan; mapas `request` fusionan por clave; **reglas de permissions se ANEXAN** (append).
- `permissions` globales aplican antes que las del agente → las del agente refinan.

## Built-ins v2

| Agente | Modo | Notas |
|---|---|---|
| `build` | primary | default; permite preguntas; tools allow por defecto; lecturas de env-files sensibles y fuera del workspace → ask |
| `plan` | primary | permite preguntas; niega edits excepto archivos bajo `~/.opencode/plan`; shell con permisos |
| `general` | subagent | investigacion y multi-paso con acceso amplio; **NO puede lanzar subagentes ni preguntar** |
| `explore` | subagent | permite solo read/glob/grep/webfetch/websearch; asks para external_directory y `.env` |
| `compaction` / `title` / `summary` | ocultos | mantenimiento, no seleccionables; title/summary niegan todo, compaction conserva la base |

**v2 NO tiene `scout`.** Override de built-in: mismo ID en `agents:`.

## default_agent (v2)

```jsonc
{ "default_agent": "writer", "agents": { "writer": { "mode": "primary" } } }
```

Debe existir, ser visible y soportar primary; si no, opencode usa `build` y luego el primer primary visible. Cambiarlo NO sustituye el agente guardado en sesiones existentes.

## ID y ubicaciones

- `~/.config/opencode/agents/<name>.md` (global) / `.opencode/agents/<name>.md` (proyecto, descubiertos de cwd hacia la raiz).
- Rutas anidadas forman el ID: `.opencode/agents/team/reviewer.md` → `team/reviewer`.
- Formatos: Markdown (frontmatter + cuerpo=system) o JSONC bajo `agents:`.
