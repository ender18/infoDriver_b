import re

SPECIAL_RE = re.compile(r"[áéíóúüñÁÉÍÓÚÜÑ]")


def run(drivers: list[dict], authorizations: list[dict]) -> list[dict]:
    results = []
    for d in drivers:
        for field in ("forename", "surname"):
            value = d.get(field, "") or ""
            for error in _check(value):
                results.append({
                    "driver_id": d.get("id"),
                    "callsign":  d.get("callsign"),
                    "full_name": d.get("fullName"),
                    "field":     field,
                    "value":     value or "(vacío)",
                    "error":     error,
                })
    return results


def _check(value: str) -> list[str]:
    errors = []
    if not value or not value.strip():
        return ["campo vacío"]
    if value.startswith((" ", "\t")):
        errors.append("espacio al inicio")
    if value.endswith((" ", "\t")):
        errors.append("espacio al final")
    chars = sorted(set(SPECIAL_RE.findall(value)))
    if chars:
        errors.append(f"caracteres especiales: {', '.join(chars)}")
    bad = [w for w in value.strip().split() if w and w != w[0].upper() + w[1:].lower()]
    if bad:
        errors.append(f"capitalización incorrecta: {', '.join(bad)}")
    return errors
