TOWN_EXPECTED   = "Mexico City"
REGION_EXPECTED = "CDMX"


def run(drivers: list[dict], authorizations: list[dict]) -> list[dict]:
    results = []
    for d in drivers:
        addr   = d.get("postalAddress") or {}
        town   = addr.get("town",   "") or ""
        region = addr.get("region", "") or ""
        errors = _check(town, TOWN_EXPECTED, "town") + _check(region, REGION_EXPECTED, "region")
        for error in errors:
            results.append({
                "driver_id": d.get("id"),
                "callsign":  d.get("callsign"),
                "full_name": d.get("fullName"),
                "field":     "city/region",
                "value":     f"town={town or '(vacío)'} | region={region or '(vacío)'}",
                "error":     error,
            })
    return results


def _check(value: str, expected: str, campo: str) -> list[str]:
    if not value or not value.strip():
        return [f"{campo}: campo vacío"]
    if value == expected:
        return []
    if value.strip().lower() == expected.lower():
        return [f"{campo}: capitalización incorrecta → {value!r} (esperado: {expected!r})"]
    if value.strip() == expected:
        return [f"{campo}: tiene espacios extra"]
    return [f"{campo}: valor incorrecto → {value!r} (esperado: {expected!r})"]
