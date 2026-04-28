def run(drivers: list[dict], authorizations: list[dict]) -> list[dict]:
    auth_ids = {a["driverID"] for a in authorizations if "driverID" in a}
    results = []
    for d in drivers:
        if d.get("id") not in auth_ids:
            results.append({
                "driver_id": d.get("id"),
                "callsign":  d.get("callsign"),
                "full_name": d.get("fullName"),
                "field":     "authorization",
                "value":     d.get("id"),
                "error":     "sin autorización registrada",
            })
    return results
