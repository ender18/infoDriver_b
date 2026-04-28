import requests

BASE_URL = "https://autocab-api.azure-api.net/driver/v1"


def fetch_all(subscription_key: str) -> dict:
    """
    Ejecuta exactamente DOS requests a la API de Autocab y retorna los datos crudos.
    Todos los validadores trabajan sobre estos datos — no se vuelve a llamar a la API.
    """
    headers = {
        "User-Agent": "python-requests",
        "Accept": "*/*",
        "Ocp-Apim-Subscription-Key": subscription_key,
    }

    drivers_resp = requests.get(f"{BASE_URL}/drivers", headers=headers, timeout=30)
    drivers_resp.raise_for_status()
    drivers_data = drivers_resp.json()

    auths_resp = requests.get(f"{BASE_URL}/driverauthorisations", headers=headers, timeout=30)
    auths_resp.raise_for_status()
    auths_data = auths_resp.json()

    return {
        "drivers":       _extract_list(drivers_data),
        "authorizations": _extract_list(auths_data),
    }


def _extract_list(data) -> list[dict]:
    if isinstance(data, list):
        return data
    for key in ("drivers", "authorisations", "data", "results", "items"):
        if key in data:
            return data[key]
    return [data]
