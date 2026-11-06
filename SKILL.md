---
name: gestor-agentes
description: "Crear, editar, validar, organizar y migrar agentes y subagentes de OpenCode V2, alineado a la DOCUMENTACION OFICIAL V2 (opencode.ai/v2/docs/agents, /v2/docs/permissions y /v2/docs/migrate-v1), verificada 06/11/2026 con binario opencode v2.2.5. Sintaxis nativa: permissions lista ordenada de reglas action/resource/effect, acciones shell/subagent/edit, model provider/model#variante, disabled/steps/hidden/color/request. La sintaxis V1 (permission mapa, bash/task) es LEGACY deprecado que V2 traduce. Usar SIEMPRE que el usuario pida: crear un agente, nuevo subagente, orquestador, ejecutor, workers, editar frontmatter de agentes, configurar permisos de agente, cambiar modelo/variante, mode primary/subagent/all, ocultar o deshabilitar agentes, organizar el inventario, o migrar agentes de V1 a V2. Incluye plantillas V2, validador y patron de jerarquia orquestador-ejecutor-workers."
license: MIT
metadata:
  version: "2.0"
  scope: project
---

# GESTOR-AGENTES — Creacion y Gestion de Agentes OpenCode V2

La referencia **NORMATIVA** es la doc V2: `https://opencode.ai/v2/docs/agents/`, `https://opencode.ai/v2/docs/permissions/` y `https://opencode.ai/v2/docs/migrate-v1` (verificada 06/11/2026; binario local `opencode v2.2.5`). La sintaxis V1 (`permission:` mapa, acciones `bash`/`task`, `disable:`, `prompt:`) esta **DEPRECADA**: V2 la sigue traduciendo automaticamente, pero los archivos nuevos se escriben SIEMPRE en V2 nativo y los existentes se convierten. SIEMPRE responde en espanol.

## PASO 0 — DETECTAR FORMATO (obligatorio antes de tocar nada)

```
opencode --version
```

| Version | Formato a escribir | Referencia |
|---|---|---|
| 2.x (actual) | **V2 nativo**: `permissions:` lista `{action, resource, effect}`, `model: provider/model#variante`, `disabled`, `steps` | `references/formato-v2.md` |
| 1.x (legado) | V1: `permission:` mapa, `bash`/`task` | `references/formato-v1.md` |

**Regla de oro del formato mixto**: cada archivo se lee como UN solo formato. En cuanto el frontmatter contiene cualquiera de `permissions`, `system`, `request` o `disabled`, OpenCode lo lee como V2 e **IGNORA con warning los campos V1 restantes** (`permission`, `tools`, `temperature`, `name`...) — silencioso y traicionero. Convierte la frontmatter COMPLETA de una vez, nunca a medias.

## UBICACIONES

| Scope | Ruta V2 preferida |
|---|---|
| Global | `~/.config/opencode/agents/<nombre>.md` |
| Proyecto | `.opencode/agents/<nombre>.md` (descubierto subiendo desde el CWD hasta el root git) |
| Config JSON | clave `agents:` (PLURAL; V1 `agent:` sigue leído) en `opencode.json(c)` |

- Nombre del archivo sin `.md` = ID del agente. Subcarpetas forman parte del ID: `.opencode/agents/team/reviewer.md` → `team/reviewer`.
- V2 todavía descubre los directorios V1 `agent/`, `mode/`, `modes/`; los archivos bajo `mode/`/`modes/` son primary y al moverlos a `agents/` hay que añadir `mode: primary`. No mezcles: usa `agents/`.
- Cambios NO se recargan en caliente: tras crear/editar, reinicia opencode.

## CAMPOS V2 NATIVOS

```yaml
description: Revisa migraciones de BD         # lo que ve el modelo para elegir subagente
mode: subagent                                # primary | subagent | all — DEFAULT V2: primary (V1 era all)
model: anthropic/claude-sonnet-5-5#high       # provider/model + variante tras # (forma extendida dict solo en JSON)
permissions:                                  # lista ORDENADA; la ULTIMA regla que coincide gana
  - action: "*"
    resource: "*"
    effect: deny                              # broad primero, excepciones despues
  - action: read
    resource: "src/**"
    effect: allow
steps: 8                                      # maxSteps esta prohibido en V2
hidden: true                                  # visibilidad, NO seguridad
color: "#ff6b6b"                              # solo hex (los colores de tema V1 no)
disabled: true                                # antes: disable
request: {headers: {...}, body: {...}}        # conservado pero AUN no enviado al modelo: las opciones activas van en variant
```

El **cuerpo del .md es el system prompt** (no existe `system:` en frontmatter de archivos; `system` solo en JSONC; `prompt:` es V1 prohibido). Campos V1 **prohibidos** en archivos V2: `temperature`, `top_p`, `prompt`, `permission`, `tools`, `disable`, `maxSteps`, `variant` suelto, `name`.

## PERMISOS V2 (el cambio grande)

- Un solo array `permissions` de reglas `{action, resource, effect}`; `effect` = allow/ask/deny; **la ultima regla coincidente gana** → escribe la amplia `"*"` PRIMERO y las excepciones despues.
- Acciones renombradas: `bash`→**`shell`**, `task`→**`subagent`**, `write`/`patch`→**`edit`**. Restantes: `read`, `glob`, `grep`, `webfetch`, `websearch`, `skill`, `external_directory`, `doom_loop`, `question`, `lsp`, `*`, y MCP como `<servidor>_<herramienta>`.
- `resource`: patron segun accion — rutas para read/edit/external_directory (expande `~` y `$HOME`), texto RAW del comando para shell (NO expande), ID de agente para subagent, nombre de skill para skill.
- **`external_directory` es ALLOW por defecto en V2** (V1 preguntaba). Para conservar el old behavior añade `{action: external_directory, resource: "*", effect: ask}` antes de tus allow especificos.
- Los padres controlan que lanzar: reglas `subagent` en el agente padre (el hijo usa sus propios permisos). `deny` en `subagent` saca al agente del catalogo que ve el modelo.
- Merge de config: scalares reemplazan, mapas se fusionan por clave, **las reglas de permissions se ANADEN** (globales antes, las del agente pueden refinar). Built-ins sobrescribibles por ID: `build`, `plan`, `general`, `explore` (ocultos: `compaction`, `title`, `summary`); en V2 **no existe `scout`**.
- `default_agent` en `opencode.jsonc` (V2) elige el primary de sesion nueva.

## RAZONAMIENTO Y VARIANTES (qwen3.8-flash / mimo)

En V2 el nivel de razonamiento NO es campo de agente: se declara como **variant del modelo** en el config y se referencia con `#`:

```jsonc
"providers": {
  "alibaba-token-plan": { "models": { "qwen3.8-flash": { "variants": [
    { "id": "low",    "settings": { "reasoningEffort": "low" } },
    { "id": "medium", "settings": { "reasoningEffort": "medium" } },
    { "id": "xhigh",  "settings": { "reasoningEffort": "xhigh" } } ] } } },
  "mimo": { "models": {
    "mimo-v2.6-pro":   { "variants": [ { "id": "medium", "body": { "thinking": { "type": "enabled" } } },
                                       { "id": "xhigh",  "body": { "thinking": { "type": "enabled" } } } ] },
    "mimo-v2.6-flash": { "variants": [ { "id": "low",    "body": { "thinking": { "type": "disabled" } } },
                                       { "id": "medium", "body": { "thinking": { "type": "enabled" } } } ] } } }
}
```

- `settings` = opciones del paquete provider (p. ej. `reasoningEffort`); `body` = JSON crudo del provider (p. ej. MiMo `thinking.type`). En MiMo solo hay dos estados reales: enabled/disabled — `xhigh` es alias de enabled.
- Agente: `model: alibaba-token-plan/qwen3.8-flash#low`.
- `temperature`/`top_p` van EN LA VARIANT (`body`), nunca en el agente.
- **Estado local (06/11/2026)**: estas variants ya estan declaradas en `~/.config/opencode/opencode.jsonc` → `providers` (clave V2 plural; el bloque `provider` V1 de `newapi` sigue conviviente, V2 lo normaliza).

## PLANTILLA V2 — subagente solo-lectura

```markdown
---
description: "Revisa codigo sin modificarlo. Usar para auditorias y dudas del proyecto."
mode: subagent
model: alibaba-token-plan/qwen3.8-flash#low
permissions:
  - action: read
    resource: "*"
    effect: allow
  - action: glob
    resource: "*"
    effect: allow
  - action: grep
    resource: "*"
    effect: allow
  - action: webfetch
    resource: "*"
    effect: allow
  - action: edit
    resource: "*"
    effect: deny
  - action: shell
    resource: "*"
    effect: deny
  - action: subagent
    resource: "*"
    effect: deny
  - action: external_directory
    resource: "*"
    effect: ask
---

Eres REVISOR... (identidad, reglas, formato de reporte con archivo:linea)
```

## PATRON DE JERARQUIA (orquestador → ejecutor → workers)

- **Orquestador** (`primary`): `shell` deny, `edit` deny, y `subagent`: deny `"*"` + allow explícitos de su roster (los 8 reviewers + workers). El padre controla que se puede lanzar.
- **Ejecutor** (`all`): permisos amplios de `edit`/`shell`; `subagent` allow roster propio (`2-ejecutor` para si mismo NO).
- **Workers** (`subagent`): `subagent` deny `"*"` (no re-delegan; tope de profundidad por config experimental).
- 1 agente por combinacion permisos × dominio; si dos se solapan, fusionar.

## WORKFLOWS

**Crear**: 1) proposito en una frase → `description`; 2) `mode` (default omitido = primary); 3) `model` con `#variante` si aplica; 4) minimo privilegio en `permissions` (broad→excepciones); 5) cuerpo denso 40-80 lineas; 6) `py scripts/validar_agentes.py <dir>`; 7) reiniciar y probar.

**Gestionar/organizar**: inventariar `agents/*.md` + `.opencode/agents/` (incluye subcarpetas-ID) → detectar solapamientos → archivar FUERA de `agents/` (convencion local: `agentes-archivo/`) → validar todo → registrar viejo→nuevo.

**Migrar V1→V2** (recomendado en 2.x): convierte cada frontmatter COMPLETA:

| V1 (legacy) | V2 nativo |
|---|---|
| `permission:` mapa clave→accion/patron | `permissions:` lista ordenada `{action, resource, effect}` |
| `bash:` | `action: shell` |
| `task:` | `action: subagent` |
| `write`/`patch` | `action: edit` |
| `disable: true` | `disabled: true` |
| `model:` + `variant:` | `model: provider/model#variante` |
| `maxSteps` | `steps` |
| `temperature`/`top_p` | variant del modelo (en `providers`) |
| `prompt:` / JSON `prompt` | cuerpo del .md / JSON `system` |
| `tools:` booleans | reglas `{action, resource: "*", effect: allow|deny}` |
| default `mode: all` | default `mode: primary` |
| JSON `agent:` | JSON `agents:` |
| ask fuera de proyecto implicito | anadir `external_directory "*" ask` explicito |
| built-in `scout` | no existe |
| `color` tema | solo hex |

Tabla extendida y ejemplos: `references/migracion-v1-a-v2.md`. Migracion inversa (V2→V1) solo si binario 1.x confirmado. **Un agente por vez, valida, prueba, sigue el lote.**

## ESTADO DE ESTA INSTALACION (06/11/2026)

- opencode **v2.2.5**. Los **14 agentes** de `~/.config/opencode/agents/` estan **V2-nativos** (convertidos el 06/11/2026 con `.tmp/conv_v2.py`; backup V1 en `.tmp/agentes-v1-backup/`).
- Todos conservan `external_directory "*": ask` + allow-list (comportamiento V1 preservado) y su roster `subagent`.
- Models: `mimo/mimo-v2.6-pro#xhigh` (orquestador), `alibaba-token-plan/qwen3.8-flash#medium|#low`, `mimo/mimo-v2.6-flash#low`.
- El plugin `orca-opencode-status` es V1 (no corre en V2; portar con /v2/docs/build/plugins/migrate-v1).

## ERRORES COMUNES

- Frontmatter **mixta**: tener `permissions` (V2) y ademas `permission`/`tools`/`temperature` (V1) → los V1 se ignoran en silencio. Un formato por archivo.
- `"*"` al FINAL: pisa todas las excepciones (la ultima coincidente gana → `"*"` va PRIMERO).
- Omitir `mode` creyendo el default V1 `all`: en V2 el default es **`primary`**.
- `reasoning_effort`/`variant` sueltos en V2: sin efecto; usa `#variante` con la variant declarada en `providers`.
- Dejar `.md` de respaldo dentro de `agents/` → agentes fantasma (el loader escanea TODOS los .md).
- Frontmatter sin cerrar → el cuerpo se filtra al YAML (pasó con 4-operario: 1300 lineas dentro del frontmatter).
- Confiar en `hidden` para seguridad: es visibilidad; la seguridad son `permissions`.
- No reiniciar tras editar.

## Auditoria de si misma (skill-creator)

`auditar_seguridad.py` marca 5 FPs nivel error propios de una skill de gestion de agentes; justificados y eximibles con `--allow override --allow archivar --allow "Fuentes:" --allow "pip install" --allow "Frontmatter **mixta**"` → ✅ PASA: (1) "override de built-in" = termino de config de la doc OpenCode, no ejecucion encubierta; (2) "archivar/migrar en lote" = proposito DECLARADO de la skill (edita archivos de agentes del propio usuario, nunca de terceros); (3) "Fuentes: https://opencode.ai/..." = citas de documentacion oficial, no egress — la skill no hace red; (4) el `pip install pyyaml` esta en un mensaje de error legible, no se ejecuta.

## VALIDADOR

```
py "<ruta-skill>/scripts/validar_agentes.py"            # ~/.config/opencode/agents
py "<ruta-skill>/scripts/validar_agentes.py" <dir>      # otro directorio
```

Clasifica `[v2]` nativo (normativo) vs `[v1]` legacy (warning "pendiente de conversion"). Errores V2: reglas sin action+resource+effect, actions V1 (`bash`/`task`), efecto invalido, campos V1 en archivo V2, `model` mal formado, `steps` no positivo, `color` no hex-6, `request.body` (warning: aun no enviado). Heuristicas: duplicados de regla, falta de `external_directory` (default allow V2). Salida `ALL_OK`/`HAY_ERRORES`.
