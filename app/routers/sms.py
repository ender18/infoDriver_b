import httpx
from fastapi import APIRouter, HTTPException
from urllib.parse import unquote

router = APIRouter(prefix="/sms", tags=["sms"])

LABSMOBILE_URL = "https://api.labsmobile.com/json/send"
LABSMOBILE_USER = "prensa@radiotaxirtc.com.co"
LABSMOBILE_PASSWORD = "8Y03gXgrKabmQmolkPGXnFz4neF0hFpe"


@router.get("/send")
async def send_sms(numero: str, mensaje: str):
    mensaje_decoded = unquote(mensaje)
    numero_decoded = unquote(numero)

    payload = {
        "message": mensaje_decoded,
        "tpoa": "Sender",
        "recipient": [{"msisdn": numero_decoded}]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            LABSMOBILE_URL,
            json=payload,
            auth=(LABSMOBILE_USER, LABSMOBILE_PASSWORD),
            headers={"Content-Type": "application/json"}
        )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return {"status": "enviado", "numero": numero_decoded, "mensaje": mensaje_decoded, "respuesta": response.json()}
