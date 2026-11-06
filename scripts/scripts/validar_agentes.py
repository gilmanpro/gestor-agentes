# -*- coding: utf-8 -*-
"""Validador de agentes opencode V2 NATIVO (documentacion oficial v2:
https://opencode.ai/v2/docs/agents/ y https://opencode.ai/v2/docs/permissions/,
verificado 06/11/2026 contra opencode.ai/v2/docs/migrate-v1).

Uso:
  py validar_agentes.py [directorio]   # default: ~/.config/opencode/agents

Clasificacion por archivo (cada archivo se lee como UN solo formato):
  - [v2]      tiene alguna de permissions|system|request|disabled -> formato nativo V2
              (normativo). Los campos V1 que aparezcan (permission, tools, disable,
              prompt, temperature, top_p, maxSteps, variant, name, reasoning_effort)
              son ERROR: V2 los ignora con warning de log y pisan la intencion.
  - [v1]      usa permission:/tools:/disable: -> LEGACY deprecado. V2 lo traduce
              automaticamente (WARN con receta de conversion). Candidato a migrar.

Checks V2: YAML, frontmatter cerrado, description (obligatoria para subagentes en
practica), mode primary|subagent|all (DEFAULT v2: primary), model provider/model#variante
(o forma extendida dict en JSON; en frontmatter .md se prefiere string con #),
permissions = lista ordenada de reglas {action, resource, effect} con effect
allow|ask|deny y la ULTIMA regla que coincide gana; actions V2: shell, edit,
subagent, read, glob, grep, webfetch, websearch, skill, external_directory,
doom_loop, question, * (bash/task/write/patch son nombres V1 -> ERROR),
steps entero positivo, hidden/disabled bool, color hex de 6 digitos, request dict.

Salida: ALL_OK (exit 0) o HAY_ERRORES (exit 1); los legacy V1 no fallan la corrida,
se listan como pendientes de conversion.
"""
import os
import re
import sys

try:
    import yaml
except ImportError:
    print("ERROR: falta PyYAML (py -m pip install pyyaml)")
    sys.exit(2)

V2_MARKERS = {"permissions", "system", "request", "disabled"}
V1_FIELDS = {"permission": "permissions (lista ordenada de reglas)",
             "tools": "reglas {action, effect} en permissions",
             "disable": "disabled",
             "prompt": "el cuerpo del .md (system implicito)",
             "temperature": "variant del modelo en providers",
             "top_p": "variant del modelo en providers",
             "maxSteps": "steps",
             "variant": "sufijo #variante en model",
             "name": "el nombre viene del archivo",
             "reasoning_effort": "model provider/model#variante (variant con settings.reasoningEffort)"}
ACTIONS_V2 = {"shell", "edit", "subagent", "read", "glob", "grep", "webfetch",
              "websearch", "skill", "external_directory", "doom_loop", "question",
              "lsp", "task", "*", "agent"}
ACTIONS_V1_RENAMED = {"bash": "shell", "task": "subagent", "write": "edit", "patch": "edit"}
EFFECTS = {"allow", "ask", "deny"}
MODES = {"primary", "subagent", "all"}
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
MODEL_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+(#[A-Za-z0-9._-]+)?$")


def _regras_v2(fm, errs, warns):
    perms = fm.get("permissions")
    if perms is None:
        return
    if not isinstance(perms, list):
        errs.append(f"permissions debe ser LISTA ordenada de reglas: {type(perms).__name__}")
        return
    for i, r in enumerate(perms):
        if not isinstance(r, dict) or set(r) != {"action", "resource", "effect"}:
            errs.append(f"permissions[{i}]: exige exactamente action+resource+effect: {r}")
            continue
        a, res, e = r["action"], r["resource"], r["effect"]
        if not (isinstance(a, str) and isinstance(res, str) and isinstance(e, str)):
            errs.append(f"permissions[{i}]: los tres campos deben ser string: {r}")
            continue
        if a not in ACTIONS_V2:
            warns.append(f"permissions[{i}].action no documentada (plugin/MCP?): {a!r}")
        if a in ACTIONS_V1_RENAMED:
            errs.append(f"permissions[{i}].action {a!r} es nombre V1; V2 usa {ACTIONS_V1_RENAMED[a]!r}")
        if e not in EFFECTS:
            errs.append(f"permissions[{i}].effect invalido: {e!r} (allow|ask|deny)")
    # heuristicas de orden: la ultima regla coincidente gana
    vistos = {}
    for i, r in enumerate(perms):
        if not isinstance(r, dict) or "action" not in r or "resource" not in r:
            continue
        clave = (r["action"], r["resource"])
        if clave in vistos:
            warns.append(f"permissions[{i}] duplica la regla {clave} de [{vistos[clave]}] (desambigua el orden)")
        vistos[clave] = i
    # external_directory: en V2 el default es allow; si falta la regla, avisar (comportamiento distinto a V1)
    if not any(isinstance(r, dict) and r.get("action") == "external_directory" for r in perms):
        warns.append("sin reglas external_directory: en V2 el default es ALLOW fuera del workspace "
                     "(V1 preguntaba); anade {action: external_directory, resource: '*', effect: ask} para el old behavior")


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

    es_v2 = bool(V2_MARKERS & set(fm))
    ver = "v2" if es_v2 else ("v1" if fm.get("permission") or fm.get("tools") or fm.get("disable") else "v2")

    if not fm.get("description"):
        (errs if es_v2 and fm.get("mode") == "subagent" else warns).append(
            "falta 'description' (obligatoria en la practica para que el modelo elija el subagente)")

    if es_v2:
        for k, alt in V1_FIELDS.items():
            if k in fm:
                errs.append(f"campo V1 {k!r} en archivo V2-nativo: se IGNORA con warning de log; convierte a {alt}")
        _regras_v2(fm, errs, warns)
        if fm.get("mode") is not None and fm["mode"] not in MODES:
            errs.append(f"mode invalido: {fm['mode']!r} (primary|subagent|all; default v2: primary)")
        if fm.get("model") is not None:
            m = fm["model"]
            if isinstance(m, dict):
                if set(m) - {"providerID", "model", "variant"}:
                    warns.append(f"forma extendida model con claves inesperadas: {sorted(m)}")
            elif not MODEL_RE.match(str(m)):
                errs.append(f"model invalido (esperado provider/model o provider/model#variante): {m!r}")
    else:
        warns.append("LEGACY V1 (deprecated): OpenCode 2 lo traduce automaticamente; convierte la "
                     "frontmatter completa a V2 nativo (ver references/migracion-v1-a-v2.md)")

    if fm.get("steps") is not None and (not isinstance(fm["steps"], int) or isinstance(fm["steps"], bool) or fm["steps"] <= 0):
        errs.append(f"steps debe ser entero positivo: {fm['steps']!r}")
    for k in ("hidden", "disabled"):
        if k in fm and not isinstance(fm[k], bool):
            errs.append(f"{k} debe ser booleano: {fm[k]!r}")
    if fm.get("color") is not None and not (isinstance(fm["color"], str) and HEX_RE.match(fm["color"])):
        errs.append(f"color en V2 es hex de 6 digitos (los colores de tema V1 ya no): {fm['color']!r}")
    if fm.get("request") is not None:
        if not isinstance(fm["request"], dict):
            errs.append(f"request debe ser mapa (headers/body): {fm['request']!r}")
        elif set(fm["request"]) - {"headers", "body"}:
            warns.append(f"request con claves inesperadas: {sorted(set(fm['request']) - {'headers', 'body'})}")
        else:
            warns.append("request.body se conserva pero el runner V2 AUN no lo envia al modelo: "
                         "las opciones activas van en una variant del provider")
    if fm.get("default_agent") is not None:
        warns.append("default_agent es clave de configuracion global, no de frontmatter de agente")
    desconocidos = set(fm) - {"description", "mode", "model", "permissions", "steps", "hidden",
                              "color", "disabled", "request", "system", "permission", "tools",
                              "disable", "prompt", "temperature", "top_p", "maxSteps", "variant",
                              "name", "reasoning_effort", "license", "metadata", "compatibility",
                              "disable", "hidden", "ultrathink"}
    if desconocidos:
        warns.append(f"campos no documentados en V2: {sorted(desconocidos)}")
    return errs, warns, ver


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.expandvars(
        r"%USERPROFILE%\.config\opencode\agents")
    if not os.path.isdir(base):
        print(f"No existe el directorio: {base}")
        sys.exit(2)
    print(f"Validando {base} contra la doc V2 (opencode.ai/v2/docs/agents) - legacy V1 se marca como pendiente")
    ok = True
    v1_pendientes = []
    archivos = sorted(f for f in os.listdir(base) if f.endswith(".md"))
    if not archivos:
        print(f"Sin agentes .md en {base}")
    for f in archivos:
        errs, warns, ver = validar(os.path.join(base, f))
        estado = "ERROR" if errs else ("WARN " if warns else "OK   ")
        if errs:
            ok = False
        if ver == "v1":
            v1_pendientes.append(f)
        print(f"[{ver:2}] {estado} {f}")
        for e in errs:
            print(f"        x {e}")
        for w in warns:
            print(f"        ! {w}")
    if v1_pendientes:
        print("Pendientes de conversion a V2 nativo: " + ", ".join(v1_pendientes))
    print("ALL_OK" if ok else "HAY_ERRORES")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
