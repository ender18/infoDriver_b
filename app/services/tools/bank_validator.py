def run(drivers: list[dict], authorizations: list[dict],
        known_banks: set[str] | None = None) -> list[dict]:
    results = []
    for d in drivers:
        for error in _check_name(d.get("bankName", "") or "", known_banks):
            results.append({
                "driver_id": d.get("id"),
                "callsign":  d.get("callsign"),
                "full_name": d.get("fullName"),
                "field":     "bankName",
                "value":     d.get("bankName") or "(vacío)",
                "error":     error,
            })
        for error in _check_sort_code(d.get("bankSortCode", "") or ""):
            results.append({
                "driver_id": d.get("id"),
                "callsign":  d.get("callsign"),
                "full_name": d.get("fullName"),
                "field":     "bankSortCode",
                "value":     d.get("bankSortCode") or "(vacío)",
                "error":     error,
            })
    return results


def _check_name(value: str, known_banks: set[str] | None) -> list[str]:
    if not value or not value.strip():
        return ["campo vacío"]
    if known_banks is not None and value.strip().upper() not in known_banks:
        return [f"'{value}' no existe en el catálogo de bancos SPEI — el pago fallará"]
    return []


def _check_sort_code(value: str) -> list[str]:
    errors = []
    if not value or not value.strip():
        return ["campo vacío"]
    v = value.strip()
    if not v.isdigit():
        errors.append("contiene caracteres no numéricos")
        return errors
    if len(v) not in (16, 18):
        errors.append(
            f"longitud incorrecta: {len(v)} dígitos (se esperan 18 para CLABE o 16 para TDD)"
        )
    return errors
