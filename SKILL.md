---
name: gestor-agentes
description: >
  Crear, editar, validar, organizar y migrar agentes y subagentes de opencode, alineado a la
  DOCUMENTACION OFICIAL ESTABLE EN ESPANOL (opencode.ai/docs/es/agents y
  opencode.ai/docs/es/permissions) y, solo como secundario, a la preview v2. Usar SIEMPRE que
  el usuario pida: crear un agente, nuevo subagente, orquestador, planeador, ejecutor, workers,
  editar el frontmatter de agentes (~/.config/opencode/agents o .opencode/agents), configurar
  permisos de agente (permission mapa, bash, task, tools deprecado), cambiar el modelo de un
  agente, mode primary/subagent/all, deshabilitar u ocultar agentes, listar u organizar el
  inventario de agentes, o migrar agentes entre la sintaxis estable y la preview v2 (en ambos
  sentidos). Incluye plantillas, validador YAML, patrones de jerarquia
  orquestador-ejecutor-workers y tabla de migracion.
license: MIT
metadata:
  version: "1.2"
  scope: global
---

# GESTOR-AGENTES — Creacion y Gestion de Agentes opencode

Skill para crear, editar, validar, organizar y migrar agentes de opencode. La referencia NORMATIVA es la **documentacion oficial estable en espanol** (`https://opencode.ai/docs/es/agents/` y `https://opencode.ai/docs/es/permissions/`, ultima actualizacion declarada 02/10/2026). La **preview v2** (`https://opencode.ai/v2/docs/...`) usa nombres de campos DIFERENTES y NO es la doc estable: aplicarla solo si la version instalada lo exige (verificar). SIEMPRE responde en espanol.

## PASO 0 — DETECTAR SINTAXIS (obligatorio antes de tocar nada)

```
opencode --version
```

| Escenario | Sintaxis de permisos | Referencia |
|---|---|---|
| **Doc estable (normativa por defecto)** | `permission:` mapa, acciones `bash`/`task`, JSON clave `agent:` (singular) | `references/formato-v1.md` |
| **Preview v2 (NO estable)** | `permissions:` lista ordenada `{action, resource, effect}`, acciones `shell`/`subagent`, JSON clave `agents:` (plural) | `references/formato-v2.md` |

Reglas:
- Agentes NUEVOS se escriben SIEMPRE en sintaxis de la doc estable, salvo que se verifique que la version instalada exige la preview.
- Escribir sintaxis de un esquema en el otro rompe o degrada silenciosamente el agente. Ante duda, valida con el script (abajo).
- Si el usuario pide "migra a v2", confirmar antes de pisar: la doc estable sigue vigente y la preview puede no ser lo que el binario instalado espera. Verificar con un agente de prueba tras cada migracion.

## UBICACIONES

| Scope | Ruta |
|---|---|
| Global | `~/.config/opencode/agents/<nombre>.md` |
| Proyecto | `.opencode/agents/<nombre>.md` |
| Config JSON | clave `agent:` (singular) en `opencode.json(c)` |

- El **nombre del archivo** (sin `.md`) = nombre/ID del agente (`review.md` → agente `review`).
- Subcarpetas formando parte del ID (`.opencode/agents/team/reviewer.md` → `team/reviewer`): SOLO documentado en la preview v2; en la doc estable NO aparece (verificar).
- La ruta alternativa `agent/` (singular) que mencionaban docs antiguas ya NO aparece en la doc estable: usar `agents/`.
- **Los cambios NO se recargan en caliente** (experiencia en esta instalacion): tras crear/editar agentes, pedir al usuario reiniciar opencode.

## WORKFLOW — CREAR UN AGENTE

1. **Proposito**: una frase — que hace y cuando usarlo. Sera la `description`, que la doc estable marca como **obligatoria** (es lo que ve el modelo para decidir si lanza el subagente).
2. **Modo** (`mode`):
   - `primary` → lo invoca el usuario (tecla Tab / combinacion `switch_agent`).
   - `subagent` → lo invoca el modelo via herramienta Task, o el usuario con `@mencion`.
   - `all` → ambas. **Default si se omite: `all`** (doc estable; la preview v2 usa `primary`).
3. **Modelo** (`model`): formato `provider/model-id` (p. ej. `anthropic/claude-sonnet-4-20250514`). Sin `model`: primary usa el global; subagente hereda el del agente primario que lo invoco. Lista con `opencode models`. El sufijo `#variante` es de la preview v2 (no documentado en la doc estable — verificar).
4. **Permisos**: principio de minimo privilegio con `permission:` (mapa). Ver reglas abajo.
5. **Prompt**: el **cuerpo del .md** es el prompt del agente. En JSON se usa `prompt: "{file:./prompts/x.txt}"` (ruta relativa al archivo de configuracion). Corto y denso: 40-80 lineas.
6. **Campos opcionales** (doc estable): `temperature` (0.0-1.0; default por modelo, ~0.55 en Qwen), `top_p`, `steps` (maximo de iteraciones; `maxSteps` esta en desuso), `disable: true`, `hidden: true` (solo subagentes), `color` (hex o color de tema). Cualquier OTRO campo desconocido se **pasa al provider** como opcion de modelo (p. ej. `reasoningEffort`, `textVerbosity`) — util solo si el modelo lo soporta.
7. **Validar**: `py scripts/validar_agentes.py [dir]` (valida contra el esquema de la doc estable y marca archivos con sintaxis preview).
8. **Reiniciar** opencode y probar: `@nombre`, Tab, o delegacion del orquestador.

Alternativa interactiva: `opencode agent create` (pregunta ubicacion, descripcion, prompt y herramientas; lo no seleccionado queda denegado).

## REGLAS DE PERMISOS (doc estable)

- La clave es **`permission` (singular)**: mapa `clave → accion` (shorthand) o `clave → { patron: accion }` (granular). Acciones: `allow` / `ask` / `deny`. Tambien existe `"*"` como clave global y, en la config global, el shorthand `permission: "allow"` que pone todo a la vez.
- **La ultima regla que coincide gana** → escribir primero la amplia (`"*"`) y despues las excepciones.
- Comodines de patron: `*` casa cero o mas de cualquier caracter; `?` casa exactamente uno; el resto literal. Matices: `"grep *"` permite `grep patron archivo`, mientras `"grep"` a secas solo casa el comando pelado; comandos con argumentos necesitan patron explicito (`"git status *"`).
- **Claves documentadas en la doc estable**: `read` (casa ruta), `edit` (cubre `edit`, `write`, `patch`), `glob` (casa patron glob), `grep` (casa expresion regular, NO la ruta), `bash` (casa comandos analizados), `task` (casa tipo de subagente), `skill` (casa nombre de skill), `lsp` (la doc la marca "no granular" hoy), `webfetch` (casa URL), `websearch` (casa consulta), `external_directory` (casa ruta externa), `doom_loop` (misma llamada 3 veces con entrada identica). Las claves `list`, `todowrite` y `question` ya NO aparecen en la lista actual de la doc estable (figuraban en docs 1.x anteriores) — verificar antes de usarlas.
- Granularidad: la doc dice "para la mayoria de los permisos puede usarse un objeto patron→accion". Ejemplos documentados: `read`, `edit`, `bash`, `external_directory`, `task`. `lsp` esta marcada explicitamente como no granular.
- **Defaults estables**: la mayoria es `allow`; `doom_loop` y `external_directory` son `ask`; `read` es `allow` pero `.env` y `.env.*` estan `deny` por defecto (`.env.example` permitido).
- Patrones de ruta admiten `~` / `$HOME` al inicio (expansion). Las rutas fuera del directorio de trabajo SIEMPRE pasan por `external_directory` aunque se escriban con `~`.
- `task`: controla que subagentes puede lanzar el agente (patrones sobre ID). `deny` **elimina al subagente de la descripcion de la herramienta Task** (el modelo no intenta invocarlo). El usuario siempre puede invocar cualquier subagente con `@mencion`, aun con `task: deny`.
- Los permisos del agente se combinan con los globales y **las reglas del agente tienen prioridad**.
- `tools:` (booleans `true/false`, comodines como `"mymcp_*": false`) esta **deprecado desde v1.1.1** y fusionado en `permission`; sigue admitido por compatibilidad. No usarlo en agentes nuevos.
- `hidden` es visibilidad (saca del autocomplete `@`), NO seguridad; la seguridad son los permisos. Aplica solo a `mode: subagent`.
- Cuando el sistema pregunta (`ask`) hay tres respuestas: `once` (esta vez), `always` (aprueba patrones sugeridos por la herramienta durante el resto de la sesion), `reject`.

## PARAMETROS DE RAZONAMIENTO QWEN (provider alibaba-token-plan)

Segun la documentacion de QwenCloud (alibabacloud.com/help/en/model-studio/deep-thinking, actualizado 28/09/2026):

| Modelo | Parametro | Valores | Default |
|---|---|---|---|
| `qwen3.8-max` / `qwen3.8-flash` | `reasoning_effort` | `low` / `medium` / `xhigh` | `xhigh` |
| `qwen3.7-plus` | `enable_thinking` + `thinking_budget` | booleano + entero tokens | ON + ~4000 |

**Nota importante**: `qwen3.7-plus` NO soporta `reasoning_effort`; su control es via `thinking_budget` numerico.

### Mecanismo "Adicional" de OpenCode v1

La doc oficial v1 (seccion "Adicional", opencode.ai/docs/es/agents/) dice:

> "Cualquier otra opcion que especifique en la configuracion de su agente se pasara directamente al proveedor como opciones de modelo."

Esto significa que campos como `reasoning_effort` en el frontmatter se pasan al provider. El ejemplo de la doc usa `reasoningEffort` (camelCase) para OpenAI, pero QwenCloud espera `reasoning_effort` (snake_case).

### Estado actual vs recomendado

- **Estado actual (02/10/2026)**: los 10 agentes usan `variant: low/medium/high`. Este campo NO esta documentado en QwenCloud; podria ser un no-op o ser interpretado por el binario de forma no documentada.
- **Recomendado (pendiente de verificar on-the-wire)**: migrar a `reasoning_effort: low/medium/xhigh` para qwen3.8-flash/max. Para qwen3.7-plus, usar `thinking_budget: <entero>`.
- **Incognita pendiente**: falta verificar si OpenCode pasa el campo como `reasoning_effort` (snake_case, compatible con Qwen) o `reasoningEffort` (camelCase, incompatible). Prueba en progreso con `3-analista.md` + logging del proxy `token-plan-proxy.mjs`.

### Ejemplo de uso (una vez verificado)

```yaml
---
description: Analista de solo lectura
mode: all
model: alibaba-token-plan/qwen3.8-flash
reasoning_effort: medium  # low/medium/xhigh para qwen3.8
permission:
  read: allow
  edit: deny
  bash: deny
---
```

Para `qwen3.7-plus` (no soporta `reasoning_effort`):
```yaml
---
description: Orquestador
mode: primary
model: alibaba-token-plan/qwen3.7-plus
enable_thinking: true
thinking_budget: 8000  # entero de tokens
permission:
  read: allow
  edit: deny
  bash: deny
---
```

### Validador

El script `validar_agentes.py` marca `reasoning_effort` como "campo no documentado en la doc estable" (warning), pero esto es esperado: es un campo de provider, no de OpenCode. El validador no puede distinguir entre campos desconocidos invalidos y opciones de provider validas.

## PLANTILLAS

### Estable (doc oficial — subagente solo-lectura)

```markdown
---
description: "Revisa codigo sin modificarlo. Usar para auditorias y dudas del proyecto."
mode: subagent
model: provider/modelo-flash
permission:
  read: allow
  glob: allow
  grep: allow
  webfetch: allow
  edit: deny
  bash: deny
  task: deny
---

Eres REVISOR... (identidad, reglas, formato de reporte con archivo:linea)
```

### Preview v2 — mismo agente (solo si la version instalada lo exige; NO es la doc estable)

```markdown
---
description: Revisa codigo sin modificarlo. Usar para auditorias y dudas del proyecto.
mode: subagent
model: provider/modelo-flash
permissions:
  - { action: "*", resource: "*", effect: deny }
  - { action: read, resource: "**", effect: allow }
  - { action: glob, resource: "*", effect: allow }
  - { action: grep, resource: "*", effect: allow }
  - { action: webfetch, resource: "*", effect: allow }
---

Eres REVISOR... (el cuerpo es el system prompt)
```

### Patron de jerarquia (orquestador → ejecutor → workers; sintaxis estable)

- **Orquestador** (`primary`, modelo fuerte): solo lectura + delegacion: `edit: deny`, `bash: deny`, `task: { "*": allow, "<si-mismo>": deny }`.
- **Ejecutor** (`all`, modelo medio): permisos amplios + `task: { "*": allow, "<si-mismo>": deny, "1-orquestador": deny }` para despachar workers en paralelo sin re-delegar hacia arriba.
- **Workers** (`subagent`, modelo rapido): `task: deny` (no re-delegan). Un worker por dominio: codigo, analisis solo-lectura, documentos.
- Regla de oro: 1 agente por combinacion (permisos × dominio). Si dos agentes se solapan, fusionarlos.

## WORKFLOW — GESTIONAR / ORGANIZAR

1. **Inventariar**: listar `~/.config/opencode/agents/*.md` + `.opencode/agents/*.md`; extraer `description/mode/model/permission` de cada frontmatter.
2. **Detectar solapamientos**: agentes con el mismo perfil permisos+dominio → candidatos a fusion.
3. **Archivar, no borrar**: mover a una carpeta FUERA de `agents/` (el loader escanea los `.md` de la carpeta; un archivo viejo dentro seguira cargandose). Convencion: `~/.config/opencode/agentes-archivo/`.
4. **Validar todo** con el script tras cada reorganizacion.
5. **Registrar** cambios grandes: tabla viejo→nuevo en el resumen al usuario.

## MIGRACION estable ↔ preview v2

Ver tabla completa y ejemplos en `references/migracion-v1-a-v2.md`. Resumen (izquierda = **doc estable**, normativa; derecha = preview v2):

| Estable | Preview v2 |
|---|---|
| `permission:` mapa | `permissions:` lista `{action, resource, effect}` |
| accion `bash` | accion `shell` |
| accion `task` | accion `subagent` |
| claves `lsp`/`doom_loop` (y `list`/`todowrite`/`question` a verificar) | sin esas acciones; anade `execute` (Code Mode) y MCP como `<servidor>_<herramienta>` |
| `disable: true` | `disabled: true` |
| `temperature`/`top_p`/`prompt`/`tools`/`maxSteps` validos (estos dos ultimos deprecados) | **prohibidos**; sustitutos `request.body.*` (aun no enviado por el runner preview), `system`, `steps` |
| `model: provider/model-id` | ademas acepta sufijo `#variante` y forma extendida `{providerID, model, variant}` en JSON |
| default `mode: all` | default `mode: primary` |
| JSON clave `agent:` (singular) | JSON clave `agents:` (plural) |
| built-in `scout` existe | no existe en la preview |
| `color`: hex O tema (`primary/secondary/accent/success/warning/error/info`) | solo hex |

La migracion **preview → estable** (invertir la tabla) es la direccion recomendada hoy: la doc estable es la normativa; la preview puede cambiar. Validar SIEMPRE con el script y probar un agente antes de migrar el lote.

## ESTADO ACTUAL DE ESTA INSTALACION (actualizar al gestionar)

Estado verificado el **02/10/2026**:

- opencode **1.18.34** (paquete npm `opencode-ai`, instalado globalmente). Componentes v2 conviven (cli.json apunta a schema v2, plugin Orca usa eventos `permission.v2.*`), pero el binario en ejecución acepta y aplica la sintaxis estable v1.
- **Alineacion con la doc estable v1 (02/10/2026)**: los **10 agentes del roster YA usan sintaxis estable v1** (`permission:` mapa, acciones `bash`/`task`, `model: provider/model-id` sin sufijo). El validador los clasifica `[estable]` con warnings por el campo `variant:` top-level.
- Roster (10 agentes en `~/.config/opencode/agents/`, sintaxis estable v1):
  - `0-arquitecto` (all, alibaba-token-plan/qwen3.8-max, variant: low, color: accent, temperature 0.3, steps 25) — unico modelo max del roster
  - `1-orquestador` (primary, alibaba-token-plan/qwen3.7-plus, variant: high)
  - `2-ejecutor` (all, qwen3.8-flash, variant: medium, temperature 0.2)
  - `3-analista` (all, qwen3.8-flash, variant: medium, solo lectura)
  - `4-documentos` (subagent, qwen3.8-flash, variant: medium)
  - `5-dev` (subagent, qwen3.8-flash, variant: medium)
  - `6-imagenes` (all, qwen3.8-flash, variant: low)
  - `7-cerrador` (all, qwen3.8-flash, variant: low, edit granular sobre AGENTS.md)
  - `8-videos` (all, qwen3.8-flash, variant: low)
  - `9-audio` (all, qwen3.8-flash, variant: low)
- **Campo `variant:` top-level**: NO documentado en la doc estable v1 ni en la preview v2 (en v2 la variante va en `model: provider/model#variante`). El binario actual lo tolera y aplica (evidencia empírica: `~/.local/state/opencode/model.json` persiste las variantes; esta sesión corre con ellas). Decision pendiente: mantenerlo como extension tolerada, o migrar a `model: ...#variant` (v2-nativo, pero diverge de v1).
- Variantes validas para qwen3.8-max y qwen3.8-flash: `low`, `medium`, `xhigh` (reasoning_options del catalogo; `high` NO existe en ellos).
- Nota de comportamiento: el TUI recuerda el variant por modelo en `~/.local/state/opencode/model.json` (mapa `"provider/model": "variant"`) y lo aplica al abrir, aun en sesiones nuevas. Si un agente "no abre" con su variant asignado: corregir la clave en `model.json`, re-normalizar las filas `session`/`session_v2` de la DB, cerrar TUI+servicio y re-abrir.
- Plugin `plugins/orca-opencode-status.js`: implementacion V1 — NO funciona en V2 (pending porting con /v2/docs/build/plugins/migrate-v1).
- Backup del estado v1 anterior: `%TEMP%\opencode\agentes-archivo-v1\` y git commit `b9e8265` del repo de config.
- **Pendiente de decision (02/10/2026)**: migrar los 10 agentes de `variant:` a `reasoning_effort:` (para qwen3.8) o `thinking_budget` (para qwen3.7-plus). Requiere verificar primero on-the-wire como OpenCode pasa el campo al provider (snake_case vs camelCase). Prueba en progreso.

## ERRORES COMUNES

- Frontmatter sin cerrar (`---` faltante) → el cuerpo se filtra al YAML y el agente queda inservible (pasó con 4-operario: 1300 lineas de registro dentro del frontmatter).
- Dejar `.md` de respaldo dentro de `agents/` → se cargan como agentes fantasma.
- Usar `tools:` (deprecado desde v1.1.1) en agentes nuevos → usar `permission:`.
- Escribir `"*"` al FINAL del mapa de patrones: pisa todas las excepciones (la ultima regla coincide gana; `"*"` va PRIMERO).
- Mezclar `permission:` y `permissions:` en el mismo frontmatter → el validador lo marca como error.
- Campos desconocidos en la sintaxis estable NO fallan: se pasan al provider como opciones (p. ej. `reasoningEffort`) — util solo si el modelo los soporta. En preview v2 el comportamiento puede ser distinto (campos prohibidos).
- No reiniciar opencode tras editar → la sesion sigue con la config vieja.
- Usar `variant:` con QwenCloud → no documentado en QwenCloud; usar `reasoning_effort` (qwen3.8) o `thinking_budget` (qwen3.7-plus) en su lugar.

## VALIDADOR

```
py "<ruta-skill>/scripts/validar_agentes.py"            # valida ~/.config/opencode/agents
py "<ruta-skill>/scripts/validar_agentes.py" <dir>      # valida otro directorio
```

Valida contra el esquema de la **doc estable en espanol**: YAML, campos permitidos (desconocidos → aviso passthrough), `description` obligatoria, `mode` (primary/subagent/all), formato de `model`, claves y efectos de `permission` (shorthand, mapa patron→accion, `"*"`), `steps` entero positivo (`maxSteps` → aviso de desuso), `disable`/`hidden` booleanos, `hidden` solo con `mode: subagent`, `color` hex o tema, `tools:` → aviso de deprecacion. Los archivos con `permissions:` (lista, preview v2) se marcan como **no conformes a la doc estable** (error con indicacion de conversion) y se listan como candidatos a migrar. Salida: `ALL_OK` (exit 0) o `HAY_ERRORES` (exit 1).
