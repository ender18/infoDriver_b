from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime


class DailyTripLevel(BaseModel):
    trips: int = Field(..., gt=0, description="Mínimo de viajes completados en el día")
    bonus: int = Field(..., gt=0, description="Bono adicional en MXN al alcanzar este nivel")


class BonusConfig(BaseModel):
    daily_trips: list[DailyTripLevel] = [
        DailyTripLevel(trips=10, bonus=200),
        DailyTripLevel(trips=15, bonus=100),
    ]
    first_trips_count: int = Field(default=5,    gt=0, description="Número de primeros viajes para ganar el bono inicial")
    first_trips_bonus: int = Field(default=1000, gt=0, description="Bono por completar los primeros N viajes ever (MXN)")


class ValidationConfig(BaseModel):
    allowed_towns: list[str]          = ["Mexico City", "Xalapa", "EDOMEX", "Veracruz"]
    allowed_regions: list[str]        = ["CDMX", "EDOMEX", "Veracruz"]
    phone_digits: int                 = 10
    bank_sort_code_lengths: list[int] = [16, 18]


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    address: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=30)
    api_base_url: str = Field(..., min_length=5)
    api_subscription_key: str = Field(..., min_length=1, max_length=255)
    peibo_customer_key: Optional[str] = Field(None, max_length=255)
    peibo_api_key: Optional[str] = Field(None, max_length=255)
    peibo_originator_account: Optional[str] = Field(None, max_length=30)


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    address: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=30)
    api_base_url: Optional[str] = Field(None, min_length=5)
    api_subscription_key: Optional[str] = Field(None, min_length=1, max_length=255)
    peibo_customer_key: Optional[str] = Field(None, max_length=255)
    peibo_api_key: Optional[str] = Field(None, max_length=255)
    peibo_originator_account: Optional[str] = Field(None, max_length=30)
    is_active: Optional[bool] = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    country: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    api_base_url: str
    api_subscription_key: str
    peibo_customer_key: Optional[str] = None
    peibo_api_key: Optional[str] = None
    peibo_originator_account: Optional[str] = None
    validation_config: Optional[ValidationConfig] = None
    bonus_config: Optional[BonusConfig] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
