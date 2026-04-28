import re

MEXICO_RE = re.compile(r"^[2-9]\d{9}$")


def run(drivers: list[dict], authorizations: list[dict]) -> list[dict]:
    results = []
    for d in drivers:
        for field in ("mobile", "telephone"):
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
    v = value.strip()
    if not v.isdigit():
        errors.append("contiene caracteres no numéricos")
        return errors
    if len(v) != 10:
        errors.append(f"longitud incorrecta: {len(v)} dígitos (se esperan 10)")
    elif not MEXICO_RE.match(v):
        errors.append("formato inválido para México (no puede empezar con 0 o 1)")
    return errors
