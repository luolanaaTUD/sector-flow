from datetime import date as DateType

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.fund_flow_service import get_intraday_series, get_ranking

router = APIRouter(prefix="/api/fund_flow", tags=["fund_flow"])


class IntradayRequest(BaseModel):
    trade_date: DateType = Field(..., alias="date", description="Trading date, e.g. 2026-05-09")
    sectors: list[str] = Field(..., description="Sector names to query (1-20 items)")

    model_config = {"populate_by_name": True}

    @field_validator("sectors")
    @classmethod
    def validate_sectors(cls, v: list[str]) -> list[str]:
        if len(v) < 1:
            raise ValueError("At least one sector is required")
        if len(v) > 20:
            raise ValueError("At most 20 sectors allowed per request")
        return v


@router.post("/intraday")
def intraday(body: IntradayRequest, db: Session = Depends(get_db)):
    """Return minute-level fund-flow time series for the requested sectors."""
    result = get_intraday_series(db, trade_date=body.trade_date, sectors=body.sectors)
    return {"code": 200, **result}


@router.get("/ranking")
def ranking(top_n: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """Return top-N inflow and outflow sectors at the latest available minute."""
    result = get_ranking(db, top_n=top_n)
    return {"code": 200, **result}
