import re

CURP_RE = re.compile(
    r"^[A-Z][AEIOUX][A-Z]{2}"
    r"\d{2}(0[1-9]|1[0-2])"
    r"(0[1-9]|[12]\d|3[01])"
    r"[HM]"
    r"(AS|BC|BS|CC|CL|CM|CS|CH|DF|DG"
    r"|GT|GR|HG|JC|MC|MN|MS|NT|NL|OC"
    r"|PL|QT|QR|SP|SL|SR|TC|TS|TL|VZ"
    r"|YN|ZS|NE)"
    r"[A-Z]{3}"
    r"[A-Z0-9]"
    r"\d$"
)

ESTADOS = {
    "AS","BC","BS","CC","CL","CM","CS","CH","DF","DG","GT","GR","HG","JC",
    "MC","MN","MS","NT","NL","OC","PL","QT","QR","SP","SL","SR","TC","TS",
    "TL","VZ","YN","ZS","NE",
}


def run(drivers: list[dict], authorizations: list[dict]) -> list[dict]:
    results = []
    for d in drivers:
        badge    = d.get("badgeNumber", "") or ""
        national = d.get("nationalId",  "") or ""
        for error in _check(badge, national):
            results.append({
                "driver_id": d.get("id"),
                "callsign":  d.get("callsign"),
                "full_name": d.get("fullName"),
                "field":     "curp",
                "value":     badge or "(vacío)",
                "error":     error,
            })
    return results


def _check(badge: str, national: str) -> list[str]:
    errors = []
    if not badge.strip():
        errors.append("badgeNumber vacío")
    if not national.strip():
        errors.append("nationalId vacío")
    if errors:
        return errors
    if badge.strip() != national.strip():
        errors.append(f"no coinciden: badge={badge!r} / national={national!r}")
    curp = badge.strip().upper()
    if len(curp) != 18:
        errors.append(f"longitud incorrecta: {len(curp)} caracteres (se esperan 18)")
    elif not CURP_RE.match(curp):
        if not re.match(r"^[A-Z][AEIOUX][A-Z]{2}", curp):
            errors.append("posiciones 1-4 inválidas")
        elif not re.match(r"^.{4}\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])", curp):
            errors.append(f"fecha inválida: '{curp[4:10]}'")
        elif curp[10] not in ("H", "M"):
            errors.append(f"sexo inválido: '{curp[10]}' (debe ser H o M)")
        elif curp[11:13] not in ESTADOS:
            errors.append(f"clave de estado inválida: '{curp[11:13]}'")
        else:
            errors.append("consonantes internas o homoclave inválidas (pos 14-18)")
    return errors
