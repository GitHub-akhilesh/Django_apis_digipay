import logging
from fastapi import APIRouter
from core.responses import ApiResponse
from observability.dashboard import dashboard_engine
from observability.cost import cost_analytics_engine

logger = logging.getLogger("ai_platform.api.routers.observability")
router = APIRouter(prefix="/api/v1/observability", tags=["Enterprise Observability"])

@router.get("/summary")
async def get_observability_summary():
    """Returns operational dashboard telemetry summary."""
    summary = dashboard_engine.assemble_dashboard_summary()
    return ApiResponse.respond_success(
        data=summary,
        message="Observability dashboard summary retrieved successfully."
    )

@router.get("/costs")
async def get_cost_breakdown():
    """Returns LLM cost accounting breakdowns."""
    costs = cost_analytics_engine.get_cost_summary()
    return ApiResponse.respond_success(
        data=costs,
        message="Cost breakdown metrics retrieved successfully."
    )
