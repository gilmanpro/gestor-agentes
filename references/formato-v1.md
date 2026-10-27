# Formato de agentes — DOCUMENTACION OFICIAL ESTABLE (espanol)

Fuente NORMATIVA: https://opencode.ai/docs/es/agents/ + https://opencode.ai/docs/es/permissions/ (ultima actualizacion declarada de las paginas: 29 sept 2026; verificado 30/09/2026). Este es el esquema que valida `scripts/validar_agentes.py`. La serie 1.x usa este esquema; la **preview v2** (https://opencode.ai/v2/docs/...) usa campos distintos — ver `references/formato-v2.md`, claramente marcada como no estable.

## Estructura del archivo

```markdown
---
description: "Obligatoria segun la doc. Que hace y cuando usarlo (el modelo la lee para decidir si lanza el subagente)."
mode: primary | subagent | all        # default si se omite: all
model: provider/model-id              # opcional; sin el: primary usa el global, subagente hereda del padre que lo invoco
temperature: 0.1                      # opcional (0.0-1.0; default por modelo: ~0 la mayoria, 0.55 Qwen)
top_p: 0.9                            # opcional (0.0-1.0)
steps: 8                              # opcional; maximo de iteraciones agenticas (campo heredado maxSteps EN DESUSO)
disable: true                         # opcional; desactiva el agente
hidden: true                          # opcional; SOLO mode: subagent; oculta del autocomplete @
color: "#ff5733"                      # opcional; hex o color de tema: primary|secondary|accent|success|warning|error|info
permission:                           # preferido (tools: DEPRECADO desde v1.1.1, fusionado aqui)
  edit: deny                          # shorthand: allow | ask | deny
  "*": ask                            # clave global para todas las acciones
  bash:                               # granular: mapa patron -> accion (ultima regla que coincide gana)
    "*": ask
    "git status *": allow
tools:                                # DEPRECADO; solo compatibilidad: booleans, comodines ("mymcp_*": false)
  write: false
---

El cuerpo markdown = prompt del agente. (En JSON el prompt va en `prompt: "{file:./prompts/x.txt}"`, ruta relativa al archivo de configuracion.)
```

En JSON (`opencode.json`): clave top-level **`agent:` (singular)**, mismo esquema. Ejemplo de la doc: override de `build`/`plan` y agente custom `code-reviewer` con `description`, `mode`, `model`, `prompt`, `tools`.

## Uso e invocacion (doc estable)

- Primarios: tecla **Tab** (combinacion `switch_agent`) para alternar en sesion.
- Subagentes: automaticos por el primario segun su `description`, o manuales con `@mencion`.
- Navegar sesiones hijas: `Líder+Right` (`session_child_cycle`) / `Líder+Left` (reverse), ciclo padre → hijos → padre.

## Claves de `permission` (doc estable)

La doc actual lista estas claves ("codificadas por el nombre de la herramienta", ademas de dos medidas de seguridad):

| Clave | Que casa | Granular (mapa patron→accion) |
|---|---|---|
| `read` | ruta del archivo | si (doc da ejemplo `.env`) |
| `edit` | TODAS las modificaciones (cubre `edit`, `write`, `patch`) | si (ejemplo con rutas) |
| `glob` | patron glob solicitado | la doc dice "la mayoria"; verificar |
| `grep` | **expresion regular** solicitada (no la ruta) | la doc dice "la mayoria"; verificar |
| `bash` | comandos de shell analizados (p. ej. `git status --porcelain`) | si |
| `task` | lanzamiento de subagentes (casa el **tipo de subagente**) | si (ejemplos con IDs) |
| `skill` | nombre de la skill | la doc dice "la mayoria"; verificar |
| `lsp` | consultas LSP | **NO — "actualmente no granulares"** |
| `webfetch` | URL obtenida | la doc dice "la mayoria"; verificar |
| `websearch` | consulta de busqueda | la doc dice "la mayoria"; verificar |
| `external_directory` | rutas fuera del directorio de trabajo | si (ejemplo con `~/.../**`) |
| `doom_loop` | misma llamada de herramienta 3 veces con entrada identica | shorthand (no documentada granular) |
| `*` | comodin sobre todas las acciones | si (ejemplo global) |

**Ya NO aparecen** en la lista actual de la doc estable: `list`, `todowrite`, `question` (figuraban en docs 1.x anteriores). Verificar contra el binario antes de usarlas; el validador las marca como aviso.

Reglas:

- **La ultima regla que coincide gana** → `"*"` PRIMERO, excepciones despues.
- Comodines: `*` casa cero o mas de cualquier caracter; `?` casa exactamente uno; resto literal.
- Matices de patron citados por la doc: `"grep *"` permite `grep patron archivo`, `"grep"` a secas solo casa el comando pelado; `git status` funciona por default pero con argumentos hace falta `"git status *"`.
- `~` y `$HOME` se expanden al INICIO de un patron. La expansion NO convierte una ruta externa en workspace: lo que quede fuera del directorio de trabajo sigue necesitando `external_directory`.
- `external_directory` aplica a toda herramienta que reciba ruta (`read`, `edit`, `glob`, `grep` y muchos `bash`). Las rutas permitidas heredan los defaults del workspace (anula con reglas explicitas, p. ej. `edit: {"~/projects/personal/**": deny}`).
- Defaults si no especificas nada: mayoria `allow`; `doom_loop` y `external_directory` → `ask`; `read` → `allow` con `*.env` y `*.env.*` en `deny` (`*.env.example` permitido).
- Respuestas cuando pregunta (`ask`): `once` (solo esta vez), `always` (aprueba los patrones que sugiere la herramienta, resto de la sesion), `reject`.
- Permisos del agente se combinan con los globales y **las reglas del agente tienen prioridad** (`agent.<id>.permission` en JSON; `permission:` en el frontmatter .md).
- `task` granular ("Permisos de tarea" en la doc de agentes): `permission.task` con glob de IDs de subagente. `deny` **elimina al subagente de la descripcion de la herramienta Task** (el modelo no intenta invocarlo). El usuario SIEMPRE puede invocar cualquier subagente via `@`, aun denegado por task.
- MCP: la doc estable documenta comodines por nombre de herramienta en `tools:` (`"mymcp_*": false`). En `permission:` con claves de herramienta MCP: verificar (no hay ejemplo explicito).

## `tools:` (DEPRECADO desde v1.1.1)

La configuracion booleana heredada `tools` esta obsoleta y se fusiono en `permission`; sigue admitida por compatibilidad (`true` ≈ allow, `false` ≈ deny). Ejemplos en la doc de agentes todavia la muestran (`write: false`, `"mymcp_*": false`). En agentes nuevos usar `permission:`.

## Campos adicionales (passthrough)

Cualquier OTRA opcion en la config del agente se **pasa directamente al provider** como opcion de modelo (doc, seccion "Adicional"): p. ej. `reasoningEffort: high`, `textVerbosity: low` con `openai/gpt-5`. Especifica del proveedor; no inventar.

## Built-ins (doc estable)

| Agente | Modo | Notas |
|---|---|---|
| `build` | primary | default; todas las herramientas habilitadas |
| `plan` | primary | restringido por permisos: `file edits` (escrituras/parches/ediciones) y `bash` en `ask` por defecto |
| `general` | subagent | uso general, multi-paso, acceso completo **excepto tareas pendientes**; cambios a archivos permitidos; parallelizable |
| `explore` | subagent | rapido y SOLO lectura (busqueda por patron/palabras clave) |
| `scout` | subagent | SOLO lectura; docs externas/deps: clona repos al cache gestionado de opencode, inspecciona fuente upstream |
| `compaction` | primary oculto | compacta contexto largo a resumen; automatico, no seleccionable |
| `title` | primary oculto | genera titulos de sesion; automatico |
| `summary` | primary oculto | resimenes de sesion; automatico |

Override: mismo ID en `agent:` (JSON) o archivo `<id>.md`.

## CLI

- `opencode agent create` — asistente interactivo: pregunta ubicacion (global/proyecto), descripcion, genera prompt e identificador, seleccion de herramientas; crea el .md.
- `opencode models` — lista de modelos disponibles.

## Formatos de config

- Markdown: frontmatter YAML + cuerpo = prompt. Nombre de archivo = nombre del agente.
- JSON: `opencode.json` bajo `agent:`; `prompt` admite `{file:./ruta}` relativo al archivo de config (funciona global y por proyecto).

## Nota sobre `#variante` y subcarpetas

- El sufijo `model: provider/id#variante`, la forma extendida `{providerID, model, variant}` y los IDs con subcarpeta (`team/reviewer.md` → `team/reviewer`) son de la **preview v2**; la doc estable NO los lista. Verificar contra el binario antes de usarlos; el validador los marca como aviso.
