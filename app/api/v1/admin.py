"""Endpoints de administración — uso LLM, fallos de validación, acceso de Ana."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.persistence.llm_usage_orm import LLMUsageLogORM
from app.api.dependencies.auth import verify_ana_api_key
from app.database import get_db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(verify_ana_api_key)],
)


class LLMUsageSummary(BaseModel):
    period: str
    total_requests: int
    total_tokens_input: int
    total_tokens_output: int
    total_tokens: int
    success_rate: float
    by_model: list[dict]
    circuit_breaker_status: dict


@router.get("/llm-usage", response_model=LLMUsageSummary, summary="Consumo de LLMs")
async def get_llm_usage(
    period: str = Query("24h", pattern=r"^(24h|7d|30d)$"),
    db: AsyncSession = Depends(get_db),
) -> LLMUsageSummary:
    """Retorna el consumo de tokens por modelo en las últimas 24h, 7d o 30d."""
    days_map = {"24h": 1, "7d": 7, "30d": 30}
    since = datetime.utcnow() - timedelta(days=days_map[period])

    result = await db.execute(
        select(LLMUsageLogORM).where(LLMUsageLogORM.timestamp >= since)
    )
    logs = result.scalars().all()

    if not logs:
        return LLMUsageSummary(
            period=period, total_requests=0, total_tokens_input=0,
            total_tokens_output=0, total_tokens=0, success_rate=1.0,
            by_model=[], circuit_breaker_status={},
        )

    total = len(logs)
    successes = sum(1 for l in logs if l.success)
    tokens_in = sum(l.tokens_input for l in logs)
    tokens_out = sum(l.tokens_output for l in logs)

    # Agrupar por modelo
    by_model: dict[str, dict] = {}
    for log in logs:
        if log.model not in by_model:
            by_model[log.model] = {"model": log.model, "requests": 0, "tokens": 0, "errors": 0}
        by_model[log.model]["requests"] += 1
        by_model[log.model]["tokens"] += log.tokens_input + log.tokens_output
        if not log.success:
            by_model[log.model]["errors"] += 1

    # Circuit breaker status desde el router singleton (si existe)
    cb_status: dict = {}
    try:
        from app.adapters.llm.llm_router import LLMRouter
        # No tenemos instancia global, reportamos desde logs recientes
        recent_failures: dict[str, int] = {}
        for log in logs:
            if not log.success:
                recent_failures[log.model] = recent_failures.get(log.model, 0) + 1
        for model, failures in recent_failures.items():
            cb_status[model] = "potentially_open" if failures >= 3 else "closed"
    except Exception:
        pass

    return LLMUsageSummary(
        period=period,
        total_requests=total,
        total_tokens_input=tokens_in,
        total_tokens_output=tokens_out,
        total_tokens=tokens_in + tokens_out,
        success_rate=round(successes / total, 3),
        by_model=list(by_model.values()),
        circuit_breaker_status=cb_status,
    )


from app.adapters.persistence.ana_access_log_orm import AnaAccessLogORM


class AnaAccessEntry(BaseModel):
    id: int
    timestamp: str
    endpoint: str
    method: str
    response_code: int
    response_time_ms: int
    ip_address: str | None
    user_agent: str | None


@router.get(
    '/ana-access-log',
    response_model=list[AnaAccessEntry],
    summary='Últimos accesos de Ana a SGAI',
)
async def get_ana_access_log(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[AnaAccessEntry]:
    '''Retorna los últimos accesos de Ana ordenados por timestamp descendente.'''
    result = await db.execute(
        select(AnaAccessLogORM).order_by(AnaAccessLogORM.timestamp.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        AnaAccessEntry(
            id=l.id,
            timestamp=l.timestamp.isoformat(),
            endpoint=l.endpoint,
            method=l.method,
            response_code=l.response_code,
            response_time_ms=l.response_time_ms,
            ip_address=l.ip_address,
            user_agent=l.user_agent,
        )
        for l in logs
    ]
