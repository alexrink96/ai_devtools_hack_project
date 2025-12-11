"""Инструмент для добавления договора."""
import re
from datetime import datetime
from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field, constr
from typing import List, Dict, Any, Literal
from mcp.shared.exceptions import McpError, ErrorData
from src.mcp_instance import mcp
from src.api_ord import get_ord_provider
from src.metrics import TOOL_CALLS, EXECUTION_ERRORS, API_CALLS
from src.tools.utils import ToolResult


tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="add_contract",
    description="""
    Создание договора между контрагентами.
    Инструмент создает договор в системе ORD.
    """
)
async def add_contract(
    client_external_id: str = Field(..., description="Внешний идентификатор клиента."),
    contractor_external_id: str = Field(..., description="Внешний идентификатор подрядчика."),
    subject_type: Literal["representation", "org_distribution", "mediation", "distribution", "other"] = Field(..., description="Предмет договора. (Возможные значения: representation — представительство; org_distribution — организация распространения рекламы; mediation — посредничество; distribution — распространение рекламы; other — иное.)."),
    date: constr(pattern=r'^\d{4}-\d{2}-\d{2}$') = Field(
        default_factory=lambda: datetime.utcnow().strftime("%Y-%m-%d"),
        description="Дата заключения договора в формате YYYY-MM-DD без привязки к часовому поясу."
    ),
    ctx: Context = None
) -> ToolResult:
    """
    Добавляет договор между контрагентами.
    
    Важно учесть: external_id человека, с которым ты общаешься: my (передавай его как аргумент). External_id другого лица ты получишь при создании контрагента (передавай его как аргумент). 

    Args:
        client_external_id: Внешний идентификатор клиента.
        contractor_external_id: Внешний идентификатор подрядчика.
        subject_type: Предмет договора. (Возможные значения: representation — представительство; org_distribution — организация распространения рекламы; mediation — посредничество; distribution — распространение рекламы; other — иное.).
        date: Дата заключения договора в формате YYYY-MM-DD без привязки к часовому поясу.
        ctx: Контекст для логирования и прогресс-отчетов.

    Returns:
        ToolResult: Содержит contract_id и статус выполнения.

    Raises:
        McpError: При неверных параметрах или ошибках API.
    """
    tool_name = "add_contract"
    
    with tracer.start_as_current_span(tool_name) as span:
        span.set_attribute("client_external_id", client_external_id)
        span.set_attribute("contractor_external_id", contractor_external_id)
        span.set_attribute("date", date)
        span.set_attribute("subject_type", subject_type)

        if ctx:
            await ctx.info(f"📄 Создаем договор: {client_external_id=}, {contractor_external_id=}, {date=}, {subject_type=}")
            await ctx.report_progress(progress=0, total=100)

        API_CALLS.labels(service="mcp", endpoint=tool_name, status="started").inc()

        try:
            
            ord_provider = get_ord_provider()

            result = await ord_provider.add_contract(
                type="service",
                client_external_id=client_external_id,
                contractor_external_id=contractor_external_id,
                date=date,
                subject_type=subject_type
            )
            if ctx:
                await ctx.report_progress(progress=100, total=100)
                await ctx.info("✅ Договор успешно создан!")

            span.set_attribute("success", True)
            span.set_attribute("contract_id", result.get("contract_id", 0))
            span.set_attribute("status_code", result.get("status_code", 0))

            API_CALLS.labels(service="mcp", endpoint=tool_name, status="success").inc()

            return ToolResult(
                content=[TextContent(type="text", text=str(result))],
                structured_content=result,
                meta={
                    "tool_name": tool_name,
                    "client_external_id": client_external_id,
                    "contractor_external_id": contractor_external_id,
                    "subject_type": subject_type,
                    "date": date
                }
            )
            
        except ValueError as e:
            span.set_attribute("error", "validation_error")
            span.set_attribute("error_message", str(e))
            
            TOOL_CALLS.labels(tool_name=tool_name, status="validation_error").inc()
            EXECUTION_ERRORS.labels(tool_name=tool_name, error_type="validation").inc()
            API_CALLS.labels(
                service="mcp",
                endpoint=tool_name,
                status="error"
            ).inc()
            
            if ctx:
                await ctx.error(f"❌ Ошибка при создании договора: {e}")
            
            
            raise McpError(
                ErrorData(
                    code=-32602,  # Invalid params
                    message=f"Ошибка при создании договора: {e}"
                )
            )
        except Exception as e:
            span.set_attribute("error", "execution_error")
            span.set_attribute("error_message", str(e))
            
            TOOL_CALLS.labels(tool_name=tool_name, status="error").inc()
            EXECUTION_ERRORS.labels(tool_name=tool_name, error_type="execution").inc()
            API_CALLS.labels(
                service="mcp",
                endpoint=tool_name,
                status="error"
            ).inc()
            
            if ctx:
                await ctx.error(f"❌ Ошибка при создании договора: {e}")
            
            
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Ошибка при создании договора: {e}"
                )
            )