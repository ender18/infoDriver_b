import re

DEFAULT_PHONE_DIGITS = 10
DEFAULT_PHONE_RE     = re.compile(r"^[2-9]\d{9}$")


def run(drivers: list[dict], authorizations: list[dict], config: dict | None = None) -> list[dict]:
    phone_digits = config.get("phone_digits", DEFAULT_PHONE_DIGITS) if config else DEFAULT_PHONE_DIGITS

    results = []
    for d in drivers:
        for field in ("mobile", "telephone"):
            value = d.get(field, "") or ""
            for error in _check(value, phone_digits):
                results.append({
                    "driver_id": d.get("id"),
                    "callsign":  d.get("callsign"),
                    "full_name": d.get("fullName"),
                    "field":     field,
                    "value":     value or "(vacío)",
                    "error":     error,
                })
    return results


def _check(value: str, phone_digits: int) -> list[str]:
    errors = []
    if not value or not value.strip():
        return ["campo vacío"]
    v = value.strip()
    if not v.isdigit():
        errors.append("contiene caracteres no numéricos")
        return errors
    if len(v) != phone_digits:
        errors.append(f"longitud incorrecta: {len(v)} dígitos (se esperan {phone_digits})")
    elif phone_digits == DEFAULT_PHONE_DIGITS and not DEFAULT_PHONE_RE.match(v):
        errors.append("formato inválido para México (no puede empezar con 0 o 1)")
    return errors
