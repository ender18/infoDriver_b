import httpx
from fastapi import APIRouter, HTTPException
from urllib.parse import unquote

router = APIRouter(prefix="/sms", tags=["sms"])

HABLAME_URL = "https://www.hablame.co/api/sms/v5/send"
HABLAME_KEY = "qGHawx0oAOVUlyb6tPG9kNzQMGgu4T3eXQD8jOnQW9NCF0Ah9jorhaTUn7RKbKXJw4jtsdImSp1LNDMc6mnBYJT3rWRuDZa5w6fWBq3m0eMqkZExEdHi1zJz72tdAggv"


@router.get("/send")
async def send_sms(numero: str, mensaje: str):
    mensaje_decoded = unquote(mensaje)
    numero_decoded = unquote(numero)

    payload = {
        "priority": True,
        "messages": [
            {"to": numero_decoded, "text": mensaje_decoded}
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            HABLAME_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-Hablame-Key": HABLAME_KEY
            }
        )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return {"status": "enviado", "numero": numero_decoded, "mensaje": mensaje_decoded, "respuesta": response.json()}
