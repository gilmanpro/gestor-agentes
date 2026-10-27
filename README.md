# gestor-agentes

Crear, editar, validar, organizar y migrar **agentes y subagentes de OpenCode** y otros arneses: frontmatter estable (permisos, modelo, actions), sintaxis preview v2, validador oficial y guia de migracion v1 -> v2.

Skill para [OpenCode](https://opencode.ai) bajo el estandar [Agent Skills](https://agentskills.io) (compatible con `.opencode/skills/`, `.claude/skills/` y `.agents/skills/`). Documentacion y cuerpo completos en `SKILL.md`; este repo es un espejo publico de la skill.

## Instalacion

```bash
cmdc skills add gilmanpro/gestor-agentes -g      # Command Code
```

Manual (OpenCode u otro arnes): copia esta carpeta a `~/.agents/skills/gestor-agentes/` (global) o `<proyecto>/.opencode/skills/gestor-agentes/`.

## Contenido

- `SKILL.md` — normativa de agentes contra la doc estable en espanol
- `references/` — `formato-v1.md`, `formato-v2.md` (preview) y `migracion-v1-a-v2.md`
- `scripts/validar_agentes.py` — validador de los agentes reales (ALL_OK)

## Verificacion

```bash
python skill-creator/scripts/quick_validate.py gestor-agentes
python skill-creator/scripts/auditar_seguridad.py gestor-agentes
```

Issues y PRs de mejora bienvenidos.
