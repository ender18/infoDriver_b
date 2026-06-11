DEFAULT_SORT_CODE_LENGTHS = [16, 18]


def run(drivers: list[dict], authorizations: list[dict],
        known_banks: set[str] | None = None, config: dict | None = None) -> list[dict]:
    lengths = set(config.get("bank_sort_code_lengths", DEFAULT_SORT_CODE_LENGTHS)) if config else set(DEFAULT_SORT_CODE_LENGTHS)

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
        for error in _check_sort_code(d.get("bankSortCode", "") or "", lengths):
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
        needle = value.strip().lower()
        suggestion = next(
            (b for b in known_banks if needle in b.lower() or b.lower() in needle),
            None
        )
        msg = f"'{value}' no existe en el catálogo de bancos SPEI — el pago fallará"
        if suggestion:
            msg += f" | ¿Quisiste decir: '{suggestion}'?"
        return [msg]
    return []


def _check_sort_code(value: str, lengths: set[int]) -> list[str]:
    errors = []
    if not value or not value.strip():
        return ["campo vacío"]
    v = value.strip()
    if not v.isdigit():
        errors.append("contiene caracteres no numéricos")
        return errors
    if len(v) not in lengths:
        expected = " o ".join(str(l) for l in sorted(lengths))
        errors.append(f"longitud incorrecta: {len(v)} dígitos (se esperan {expected})")
    return errors
