from fastapi import APIRouter, HTTPException
from api.core.dependencies import CurrentUser
from api.schemas.calculators import SeverancePayRequest, NoticePeriodRequest, NetSalaryRequest
from processing.calculators import calculate_severance_pay, calculate_notice_period, calculate_net_salary

router = APIRouter(prefix="/calculators", tags=["Calculateurs"])


@router.post("/severance-pay")
async def severance_pay(request: SeverancePayRequest, current_user: CurrentUser):
    try:
        return calculate_severance_pay(request.monthly_salary, request.years_of_service)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/notice-period")
async def notice_period(request: NoticePeriodRequest, current_user: CurrentUser):
    try:
        return calculate_notice_period(request.category, request.years_of_service)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/net-salary")
async def net_salary(request: NetSalaryRequest, current_user: CurrentUser):
    try:
        return calculate_net_salary(request.gross_salary)
    except ValueError as e:
        raise HTTPException(400, str(e))
