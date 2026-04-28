import re
from collections import Counter


def run(drivers: list[dict], authorizations: list[dict]) -> list[dict]:
    emails_lower = [(d.get("email") or "").strip().lower() for d in drivers]
    duplicates = {e for e, c in Counter(emails_lower).items() if c > 1 and e}

    results = []
    for d in drivers:
        email = d.get("email", "") or ""
        errors = _check(email)
        if email.strip().lower() in duplicates:
            errors.append("email duplicado")
        for error in errors:
            results.append(_row(d, "email", email or "(vacío)", error))
    return results


def _check(email: str) -> list[str]:
    errors = []
    if not email or not email.strip():
        return ["campo vacío"]
    if email.startswith((" ", "\t")):
        errors.append("espacio al inicio")
    if email.endswith((" ", "\t")):
        errors.append("espacio al final")
    clean = email.strip()
    if " " in clean or "\t" in clean:
        errors.append("contiene espacios internos")
    if "@" not in clean:
        errors.append("falta el símbolo @")
        return errors
    if clean.count("@") > 1:
        errors.append("más de un símbolo @")
        return errors
    usuario, dominio = clean.split("@", 1)
    if not usuario:
        errors.append("falta usuario antes del @")
    else:
        if usuario.startswith("."):
            errors.append("usuario: no puede empezar con punto")
        if usuario.endswith("."):
            errors.append("usuario: no puede terminar con punto")
        if ".." in usuario:
            errors.append("usuario: contiene puntos consecutivos")
        inv = re.findall(r"[^a-zA-Z0-9._%+\-]", usuario)
        if inv:
            errors.append(f"usuario: caracteres no permitidos → {''.join(sorted(set(inv)))!r}")
    if not dominio:
        errors.append("falta dominio después del @")
    elif "." not in dominio:
        errors.append("dominio sin extensión")
    else:
        partes = dominio.split(".")
        nombre = ".".join(partes[:-1])
        ext = partes[-1]
        if dominio.startswith(".") or dominio.endswith("."):
            errors.append("dominio: punto al inicio o al final")
        if ".." in dominio:
            errors.append("dominio: contiene puntos consecutivos")
        if nombre.startswith("-") or nombre.endswith("-"):
            errors.append("dominio: no puede empezar ni terminar con guión")
        inv_dom = re.findall(r"[^a-zA-Z0-9.\-]", dominio)
        if inv_dom:
            errors.append(f"dominio: caracteres no permitidos → {''.join(sorted(set(inv_dom)))!r}")
        if len(ext) < 2:
            errors.append(f"extensión muy corta: '.{ext}'")
        if not ext.isalpha():
            errors.append(f"extensión inválida: '.{ext}' (solo letras)")
    return errors


def _row(d: dict, field: str, value: str, error: str) -> dict:
    return {
        "driver_id": d.get("id"),
        "callsign":  d.get("callsign"),
        "full_name": d.get("fullName"),
        "field":     field,
        "value":     value,
        "error":     error,
    }
