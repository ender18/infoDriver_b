from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import requests as http_requests

from app.database import get_db
from app.models.company import Company
from app.utils.dependencies import require_permission
from app.services.tools import drivers_client
from app.services.tools import (
    authorization_validator,
    curp_validator,
    email_validator,
    name_validator,
    phone_validator,
    city_validator,
)

router = APIRouter(prefix="/tools", tags=["tools"])

# Para agregar un nuevo validador: importarlo arriba y añadirlo aquí.
VALIDATORS = [
    authorization_validator,
    email_validator,
    curp_validator,
    name_validator,
    phone_validator,
    city_validator,
]


@router.get("/drivers/validate")
def validate_drivers(
    company_id: int = Query(..., description="ID de la compañía con la que trabajar"),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("tools:run")),
):
    company = db.query(Company).filter(
        Company.id == company_id,
        Company.is_active == True
    ).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    try:
        # Un único bloque de requests — todos los validadores usan estos datos
        data = drivers_client.fetch_all(company.api_subscription_key)
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="No se pudo conectar a la API externa")
    except http_requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Tiempo de espera agotado al conectar con la API externa")
    except http_requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Error de la API externa: {e}")

    drivers        = data["drivers"]
    authorizations = data["authorizations"]

    all_results = []
    for validator in VALIDATORS:
        all_results.extend(validator.run(drivers, authorizations))

    return {
        "company":       {"id": company.id, "name": company.name},
        "total_drivers": len(drivers),
        "total_errors":  len(all_results),
        "results":       all_results,
    }
