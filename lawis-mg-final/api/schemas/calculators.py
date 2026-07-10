from pydantic import BaseModel, Field


class SeverancePayRequest(BaseModel):
    monthly_salary: float = Field(..., gt=0, description="Salaire mensuel brut (MAD)")
    years_of_service: float = Field(..., ge=0, description="Ancienneté en années")


class NoticePeriodRequest(BaseModel):
    category: str = Field(..., description="employe | cadre")
    years_of_service: float = Field(..., ge=0)


class NetSalaryRequest(BaseModel):
    gross_salary: float = Field(..., gt=0, description="Salaire mensuel brut (MAD)")
