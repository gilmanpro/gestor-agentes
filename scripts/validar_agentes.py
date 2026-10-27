# -*- coding: utf-8 -*-
"""Validador de agentes opencode contra la DOCUMENTACION OFICIAL ESTABLE en espanol
(https://opencode.ai/docs/es/agents/ y https://opencode.ai/docs/es/permissions/,
verificado 30/09/2026).

Uso:
  py validar_agentes.py [directorio]   # default: ~/.config/opencode/agents

Por archivo:
  - `permission:` (mapa) o sin bloque de permisos -> se valida contra el esquema ESTABLE.
  - `permissions:` (lista) -> sintaxis de la PREVIEW v2 (opencode.ai/v2/docs): se marca
    como NO Conforme a la doc estable (error con indicacion de conversion) y ademas se
    revisa su estructura interna. Candidato a migrar (ver references/migracion-v1-a-v2.md).

Valida (estable): YAML, description obligatoria, mode (primary/subagent/all; default all),
model (provider/model-id; sufijo #variante = preview, aviso), permission (shorthand, mapa
patron->accion, clave global "*"), claves/effects documentados, steps entero positivo
(maxSteps en desuso), disable/hidden booleanos, hidden solo con mode subagent, color hex
o tema, temperature/top_p numericos 0-1, tools deprecado desde v1.1.1, campos desconocidos
-> aviso (passthrough al provider segun la doc).

Exit code 0 si todo OK, 1 si hay errores.
"""
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("ERROR: falta PyYAML (py -m pip install pyyaml)")
    sys.exit(2)

# --- Esquema de la doc estable (opencode.ai/docs/es/agents) ---
ESTABLE_FM = {
    "description", "mode", "model", "temperature", "top_p", "steps", "maxSteps",
    "disable", "hidden", "color", "prompt", "tools", "permission",
}
# Campos que solo existen en la preview v2: en estable son error/aviso fuerte.
PREVIEW_ONLY_ERR = {
    "disabled": "usa 'disable' (la doc estable); 'disabled' es preview v2",
    "permissions": None,  # se trata aparte (lista de reglas)
    "system": "en .md el cuerpo es el prompt; 'system:' es preview v2",
    "request": "overlay de request es preview v2; en estable usa temperature/top_p directos",
}
PREVIEW_ONLY_WARN = {
    "variant": "campo 'variant' no documentado en la doc estable (preview v2 / passthrough al provider: verificar)",
    "name": "el nombre del agente viene del archivo; campo 'name' no documentado en la doc estable",
}
# Claves de permission listadas por la doc estable (permisos page) + comodin global.
ESTABLE_PERM_KEYS = {
    "read", "edit", "glob", "grep", "bash", "task", "skill", "lsp",
    "webfetch", "websearch", "external_directory", "doom_loop", "*",
}
# Claves de docs 1.x anteriores que YA no figuran en la doc estable actual.
SIN_LISTA_ESTABLE = {"list", "todowrite", "question"}
# Claves explicitamente NO granulares segun la doc estable.
SHORTHAND_ONLY = {"lsp", "doom_loop"}
MODES = {"primary", "subagent", "all"}
EFFECTS = {"allow", "ask", "deny"}
THEME_COLORS = {"primary", "secondary", "accent", "success", "warning", "error", "info"}
HEX_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")
MODEL_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
MODEL_VAR_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+#[A-Za-z0-9._-]+$")

# --- Acciones preview v2 (solo para revisar estructura de archivos preview) ---
V2_ACTIONS = {"shell", "edit", "subagent", "read", "glob", "grep", "question",
              "webfetch", "websearch", "skill", "external_directory",
              "execute", "*"}


def _revisa_permiso_estable(fm, errs, warns):
    perm = fm.get("permission")
    if isinstance(perm, str):
        if perm not in EFFECTS:
            errs.append(f"permission shorthand invalido: {perm!r} (esperado allow|ask|deny)")
        else:
            warns.append("permission como string uniforme esta documentado para la config "
                         "global; en un .md la doc usa siempre el mapa")
        return
    if not isinstance(perm, dict):
        errs.append(f"permission debe ser mapa clave->accion o clave->{{patron:accion}}: {perm!r}")
        return
    for k, v in perm.items():
        if k in ESTABLE_PERM_KEYS:
            pass
        elif k in SIN_LISTA_ESTABLE:
            warns.append(f"permission.{k}: ya no figura en la lista de la doc estable "
                         "(era de docs 1.x anteriores) - verificar antes de usar")
        else:
            warns.append(f"permission.{k}: clave no documentada en la doc estable "
                         "(herramienta de plugin/MCP? verificar)")
        if isinstance(v, str):
            if v not in EFFECTS:
                errs.append(f"permission.{k}: efecto invalido {v!r} (esperado allow|ask|deny)")
        elif isinstance(v, dict):
            if k in SHORTHAND_ONLY:
                warns.append(f"permission.{k}: la doc estable lo marca no granular "
                             "(usa shorthand allow|ask|deny)")
            for pat, acc in v.items():
                if acc not in EFFECTS:
                    errs.append(f"permission.{k}['{pat}']: efecto invalido {acc!r}")
        else:
            errs.append(f"permission.{k}: valor invalido {v!r}")


def _revisa_preview(fm, errs, warns):
    """Estructura de la lista `permissions:` (preview v2), ademas del error de esquema."""
    for i, r in enumerate(fm.get("permissions", [])):
        if not isinstance(r, dict) or not {"action", "resource", "effect"} <= set(r):
            errs.append(f"permissions[{i}] (preview) requiere action+resource+effect: {r}")
            continue
        for campo in ("action", "resource", "effect"):
            if not isinstance(r[campo], str):
                errs.append(f"permissions[{i}].{campo} (preview) debe ser string: {r[campo]!r}")
        if r.get("effect") not in EFFECTS:
            errs.append(f"permissions[{i}].effect invalido: {r.get('effect')}")
        if r.get("action") not in V2_ACTIONS:
            warns.append(f"permissions[{i}].action no documentada en preview (plugin/MCP?): {r.get('action')}")


def validar(path):
    errs, warns = [], []
    raw = open(path, encoding="utf-8").read()
    if not raw.startswith("---"):
        return ["no abre con --- (frontmatter ausente)"], [], "?"
    parts = raw.split("\n---", 1)
    if len(parts) < 2:
        return ["frontmatter sin cerrar (falta --- final)"], [], "?"
    try:
        fm = yaml.safe_load(parts[0][3:])
    except Exception as e:
        return [f"YAML invalido: {e}"], [], "?"
    if not isinstance(fm, dict):
        return ["el frontmatter no es un mapa"], [], "?"

    es_preview = fm.get("permissions") is not None
    if isinstance(fm.get("permissions"), list):
        ver = "preview-v2"
        errs.append("NO Conforme a la doc estable: 'permissions:' (lista) es sintaxis de la "
                    "preview v2; la doc estable usa 'permission:' mapa con acciones "
                    "bash/task (ver references/migracion-v1-a-v2.md)")
        _revisa_preview(fm, errs, warns)
    elif fm.get("permissions") is not None:
        ver = "preview-v2?"
        errs.append("'permissions' debe ser una lista (preview v2); "
                    "en la doc estable la clave es 'permission' (mapa)")
    else:
        ver = "estable"
    if es_preview and fm.get("permission") is not None:
        errs.append("mezcla 'permission' (estable) y 'permissions' (preview) en el mismo frontmatter")

    # --- Checks comunes / esquema estable ---
    if not fm.get("description"):
        errs.append("falta 'description': la doc estable la marca como obligatoria")

    desconocidos = set(fm) - ESTABLE_FM - set(PREVIEW_ONLY_ERR) - set(PREVIEW_ONLY_WARN)
    if desconocidos:
        warns.append(f"campos no documentados en la doc estable (se pasan al provider como "
                     f"opcion de modelo, o son error si la version es preview): {sorted(desconocidos)}")
    for k, msg in PREVIEW_ONLY_ERR.items():
        if k in fm and msg:
            errs.append(f"'{k}': {msg}")
    for k, msg in PREVIEW_ONLY_WARN.items():
        if k in fm:
            warns.append(msg)

    if fm.get("mode") is not None and fm["mode"] not in MODES:
        errs.append(f"mode invalido: {fm['mode']!r} (esperado primary|subagent|all; default estable: all)")
    if fm.get("model") is not None:
        m = fm["model"]
        if isinstance(m, dict):
            warns.append("forma extendida {providerID, model, variant} es de la preview v2; "
                         "la doc estable usa el string provider/model-id (verificar)")
        else:
            m = str(m)
            if MODEL_VAR_RE.match(m):
                warns.append(f"model con sufijo '#variante' no documentado en la doc estable "
                             f"(preview v2): {m} - verificar contra el binario")
            elif not MODEL_RE.match(m):
                errs.append(f"model con formato invalido (esperado provider/model-id): {m}")

    if fm.get("steps") is not None and (not isinstance(fm["steps"], int)
                                          or isinstance(fm["steps"], bool) or fm["steps"] <= 0):
        errs.append(f"steps debe ser un entero positivo: {fm['steps']!r}")
    if "maxSteps" in fm:
        warns.append("maxSteps esta EN DESUSO segun la doc estable; usa 'steps'")

    if "disable" in fm and not isinstance(fm["disable"], bool):
        errs.append(f"disable debe ser booleano: {fm['disable']!r}")

    if "hidden" in fm:
        if not isinstance(fm["hidden"], bool):
            errs.append(f"hidden debe ser booleano: {fm['hidden']!r}")
        elif fm.get("mode") is not None and fm["mode"] != "subagent":
            errs.append("hidden solo aplica a agentes mode: subagent (doc estable)")

    if fm.get("color") is not None:
        c = fm["color"]
        if not (isinstance(c, str) and (HEX_RE.match(c) or c in THEME_COLORS)):
            warns.append(f"color no documentado en la doc estable (hex tipo #FF5733 o tema "
                         f"primary|secondary|accent|success|warning|error|info): {c!r}")

    for k in ("temperature", "top_p"):
        if k in fm:
            v = fm[k]
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not (0.0 <= float(v) <= 1.0):
                warns.append(f"{k} fuera del rango documentado 0.0-1.0: {v!r}")

    if "prompt" in fm and not isinstance(fm["prompt"], str):
        errs.append("prompt debe ser un string (ruta {file:...} o texto): "
                    + str(type(fm["prompt"])))

    if "tools" in fm:
        warns.append("tools: DEPRECADO desde v1.1.1 (fusionado en permission; sigue "
                     "funcionando por compatibilidad); usar permission:")
        if isinstance(fm.get("tools"), dict):
            for k, v in fm["tools"].items():
                if not isinstance(v, bool):
                    errs.append(f"tools.{k} debe ser true/false: {v!r}")

    if ver == "estable" and fm.get("permission") is not None:
        _revisa_permiso_estable(fm, errs, warns)

    return errs, warns, ver


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.expandvars(
        r"%USERPROFILE%\.config\opencode\agents")
    if not os.path.isdir(base):
        print(f"No existe el directorio: {base}")
        sys.exit(2)
    print(f"Validando {base} contra la doc estable ES "
          f"(opencode.ai/docs/es/agents) - preview v2 se marca como no conforme")
    ok = True
    archivos = sorted(f for f in os.listdir(base) if f.endswith(".md"))
    if not archivos:
        print(f"Sin agentes .md en {base}")
    for f in archivos:
        errs, warns, ver = validar(os.path.join(base, f))
        estado = "ERROR" if errs else ("WARN " if warns else "OK   ")
        if errs:
            ok = False
        print(f"[{ver}] {estado} {f}")
        for e in errs:
            print(f"        x {e}")
        for w in warns:
            print(f"        ! {w}")
    print("ALL_OK" if ok else "HAY_ERRORES")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
