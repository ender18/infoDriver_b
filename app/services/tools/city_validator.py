ALLOWED_TOWNS   = {"Mexico City", "Xalapa", "EDOMEX", "Veracruz"}
ALLOWED_REGIONS = {"CDMX", "EDOMEX", "Veracruz"}


def run(drivers: list[dict], authorizations: list[dict]) -> list[dict]:
    results = []
    for d in drivers:
        addr   = d.get("postalAddress") or {}
        town   = addr.get("town",   "") or ""
        region = addr.get("region", "") or ""
        errors = _check(town, ALLOWED_TOWNS, "town") + _check(region, ALLOWED_REGIONS, "region")
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


def _check(value: str, allowed: set, campo: str) -> list[str]:
    if not value or not value.strip():
        return [f"{campo}: campo vacío"]
    if value in allowed:
        return []
    lower_map = {v.lower(): v for v in allowed}
    stripped = value.strip()
    if stripped.lower() in lower_map:
        return [f"{campo}: capitalización incorrecta → {value!r} (esperado: {lower_map[stripped.lower()]!r})"]
    if stripped in allowed:
        return [f"{campo}: tiene espacios extra"]
    allowed_str = ", ".join(sorted(allowed))
    return [f"{campo}: valor no permitido → {value!r} (permitidos: {allowed_str})"]
