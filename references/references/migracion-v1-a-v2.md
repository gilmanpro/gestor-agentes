# Migracion de agentes: V1 legacy → V2 nativo (direccion NORMATIVA)

Fuentes: doc **V2** https://opencode.ai/v2/docs/agents/, https://opencode.ai/v2/docs/permissions/ y https://opencode.ai/v2/docs/migrate-v1 (NORMATIVAS desde OpenCode 2; verificado 06/11/2026 con binario v2.2.5) y la doc de la serie 1.x https://opencode.ai/docs/es/agents/ (ahora **LEGACY**: "V1 agent frontmatter is deprecated but still translated automatically"). La migracion V1→V2 es la direccion **recomendada en 2.x**; V2 conserva todos los archivos V1 sin reescribirlos, pero un archivo mixto se lee como V2 e ignora sus campos V1 en silencio.

## Cuando migrar

- **V1 → V2**: con binario 2.x, al crear agentes nuevos (SIEMPRE en V2) y al tocar un legacy (convertir la frontmatter COMPLETA de una vez). Opcional pero recomendado: migrar el lote de una vez con script + validador.
- **V2 → V1**: solo si se confirma binario 1.x (invertir la tabla).
- Antes de cualquier migracion en lote: archivar copia de los agentes fuera de `agents/` (p. ej. `~/.config/opencode/agentes-archivo-v1/` o `.tmp/agentes-v1-backup/`).

## Tabla de correspondencias (izquierda = V1 LEGACY; derecha = V2 NATIVO / normativo)

| V1 legacy | V2 nativo | Nota |
|---|---|---|
| `permission:` (mapa clave→accion o clave→{patron:accion}, y `"*"` global) | `permissions:` (lista ordenada de `{action, resource, effect}`) | Ultima regla gana en ambos |
| accion `bash` | accion `shell` | En preview el recurso es texto de comando crudo; patron `cmd *` casa tambien el comando sin argumentos |
| accion `task` | accion `subagent` | recurso = ID de agente |
| accion `edit` (cubre write/edit/patch) | accion `edit` | igual |
| `read/glob/grep/webfetch/websearch/skill/external_directory` | mismos nombres | `list` no aparece en la tabla de acciones preview |
| `question` | `question` (recurso `*`) | `question` ya NO figura en la lista actual de la doc estable (verificar en el binario) |
| `todowrite` | sin accion documentada | no aparece en ninguna de las dos docs actuales (verificar) |
| `lsp` (no granular), `doom_loop` | sin equivalente | la doc de permisos preview los excluye explicitamente |
| (n/a) | `execute` (recurso `*`) | nueva accion preview: habilita/deshabilita Code Mode |
| MCP via comodines en `tools:` (`"mymcp_*": false`) | MCP como acciones `<servidor>_<herramienta>` (recurso `*`) | en estable, MCP dentro de `permission:` no esta ejemplificado (verificar) |
| `disable: true` | `disabled: true` | |
| `temperature: 0.2` (valido) | `request: { body: { temperature: 0.2 } }` | el runner preview AUN no envia `request`; en estable va directo en el frontmatter |
| `top_p` (valido) | `request.body.top_p` | idem |
| `prompt: "{file:...}"` (JSON; en .md el cuerpo es el prompt) | `system:` (JSON) o cuerpo del .md | |
| `tools:` (DEPRECADO desde v1.1.1, sigue funcionando) | prohibido | convertir primero a `permission:` y luego a `permissions:` |
| `steps` (valido; `maxSteps` en desuso) | `steps` | |
| `model: provider/model-id` | ademas sufijo `#variante` y forma extendida `{providerID, model, variant}` en JSON | el sufijo NO esta en la doc estable (verificar) |
| `hidden` (solo subagent; oculta de @; el modelo aun puede lanzarlo via task) | `hidden` (oculta de listings, descubrimiento y catalogo) | misma clave, alcance distinto |
| `color`: hex **o** tema (`primary/secondary/accent/success/warning/error/info`) | solo hex 6 digitos | |
| default `mode: all` | default `mode: primary` | declarar `mode` SIEMPRE |
| clave JSON `agent:` (singular) | clave JSON `agents:` (plural) | |
| default model subagente: hereda del primario que lo invoca; primario sin model: modelo global | idem | igual |
| built-in `scout` existe | no existe en preview | eliminar referencias al migrar a preview |

## Conversion de permisos (ejemplo completo)

Estable (doc oficial):

```yaml
permission:
  read: allow
  glob: allow
  grep: allow
  edit: deny
  bash:
    "*": ask
    "git status *": allow
  task:
    "*": allow
    "1-orquestador": deny
```

Preview v2 equivalente:

```yaml
permissions:
  - { action: "*", resource: "*", effect: deny }
  - { action: read, resource: "**", effect: allow }
  - { action: glob, resource: "*", effect: allow }
  - { action: grep, resource: "*", effect: allow }
  - { action: shell, resource: "*", effect: ask }
  - { action: shell, resource: "git status *", effect: allow }
  - { action: subagent, resource: "*", effect: allow }
  - { action: subagent, resource: "1-orquestador", effect: deny }
```

Receta (preview): 1) deny total de base; 2) re-allow de lecturas; 3) shell/task con sus patrones (amplios primero); 4) excepciones al final. `edit: deny` queda cubierto por el deny de base.

Receta (estable, vuelta): 1) por clave, shorthand si es uniforme (`read: allow`); 2) si hay excepciones por patron, mapa con `"*"` primero y excepciones despues; 3) no hace falta deny total de base porque los defaults estables ya son permisivos con `external_directory`/`doom_loop` en ask y `.env` denegado en read.

## Procedimiento

1. `opencode --version` y consultar la doc que corresponde: estable = https://opencode.ai/docs/es/agents/.
2. Archivar los agentes actuales completos (fuera de `agents/`).
3. Migrar **UN agente de prueba** segun la tabla; reiniciar opencode; verificar que carga, que el `mode`/`model` aplican y que un `deny` bloquea de verdad.
4. Si el piloto funciona: migrar el resto. Declarar `mode` explicito siempre.
5. Validar con `scripts/validar_agentes.py` (valida contra la doc estable; los archivos con `permissions:` lista se reportan como no conformes).
6. Reiniciar opencode; probar cada agente (`@nombre`, Tab, delegacion del orquestador, permisos deny).
7. Actualizar la seccion "ESTADO ACTUAL" del SKILL.md y cualquier skill/doc que cite nombres o sintaxis distintos.
