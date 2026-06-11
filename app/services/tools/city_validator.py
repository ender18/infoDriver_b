import re

DEFAULT_ALLOWED_TOWNS   = {"Mexico City", "Xalapa", "EDOMEX", "Veracruz"}
DEFAULT_ALLOWED_REGIONS = {"CDMX", "EDOMEX", "Veracruz"}

REF_RE = re.compile(r"^REF: \S+$")


def run(drivers: list[dict], authorizations: list[dict], config: dict | None = None) -> list[dict]:
    allowed_towns   = set(config.get("allowed_towns",   list(DEFAULT_ALLOWED_TOWNS)))   if config else DEFAULT_ALLOWED_TOWNS
    allowed_regions = set(config.get("allowed_regions", list(DEFAULT_ALLOWED_REGIONS))) if config else DEFAULT_ALLOWED_REGIONS

    results = []
    for d in drivers:
        addr        = d.get("postalAddress") or {}
        town        = addr.get("town",     "") or ""
        region      = addr.get("region",   "") or ""
        postcode    = addr.get("postcode", "") or ""
        referral_id = d.get("referralId",  "") or ""

        for error in _check(town, allowed_towns, "town") + _check(region, allowed_regions, "region"):
            results.append({
                "driver_id": d.get("id"),
                "callsign":  d.get("callsign"),
                "full_name": d.get("fullName"),
                "field":     "city/region",
                "value":     f"town={town or '(vacío)'} | region={region or '(vacío)'}",
                "postcode":  postcode,
                "error":     error,
            })

        for error in _check_postcode(postcode):
            results.append({
                "driver_id": d.get("id"),
                "callsign":  d.get("callsign"),
                "full_name": d.get("fullName"),
                "field":     "postcode",
                "value":     postcode,
                "error":     error,
            })

        for error in _check_referral_id(referral_id):
            results.append({
                "driver_id": d.get("id"),
                "callsign":  d.get("callsign"),
                "full_name": d.get("fullName"),
                "field":     "referralId",
                "value":     referral_id or "(vacío)",
                "error":     error,
            })

    return results


def _check_postcode(value: str) -> list[str]:
    if not value or not value.strip():
        return []
    if value.endswith((" ", "\t")):
        return ["tiene espacios al final"]
    if not REF_RE.match(value):
        return ["formato inválido (debe ser: REF: seguido del código, ej. REF: FSRUber)"]
    return []


def _check_referral_id(value: str) -> list[str]:
    if not value or not value.strip():
        return []
    if value.endswith((" ", "\t")):
        return ["tiene espacios al final"]
    if not REF_RE.match(value):
        return ["formato inválido (debe ser: REF: seguido del código, ej. REF: FSRUber)"]
    return []


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
