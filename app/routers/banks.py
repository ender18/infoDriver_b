from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.bank import Bank
from app.utils.dependencies import get_current_active_user, require_permission

router = APIRouter(prefix="/banks", tags=["banks"])


class BankCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=100)


class BankUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


@router.get("/")
def list_banks(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return db.query(Bank).order_by(Bank.name).all()


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_bank(
    body: BankCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("companies:update")),
):
    if db.query(Bank).filter(Bank.code == body.code).first():
        raise HTTPException(status_code=400, detail="El código ya existe")
    bank = Bank(code=body.code, name=body.name)
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank


@router.patch("/{code}")
def update_bank(
    code: str,
    body: BankUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("companies:update")),
):
    bank = db.query(Bank).filter(Bank.code == code).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Banco no encontrado")
    bank.name = body.name
    db.commit()
    db.refresh(bank)
    return bank


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bank(
    code: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("companies:update")),
):
    bank = db.query(Bank).filter(Bank.code == code).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Banco no encontrado")
    db.delete(bank)
    db.commit()
