"""Инструмент для создания акта в ORD."""

from fastmcp import Context
from mcp.types import TextContent
from mcp.shared.exceptions import McpError, ErrorData
from opentelemetry import trace
from pydantic import Field, constr
from typing import Any, Dict, Literal

from src.mcp_instance import mcp
from src.api_ord import get_ord_provider
from src.validators import check_dates_in_act, check_roles_in_act
from src.metrics import TOOL_CALLS, EXECUTION_ERRORS, API_CALLS
from src.tools.utils import ToolResult
from src.utils import create_amount

tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="add_act",
    description="""Создание акта по договору в VK ORD.

Инструмент создает акт (invoice).
"""
)
async def add_act(
    contract_external_id: str = Field(
        ...,
        description="Внешний идентификатор договора, к которому добавляется акт."
    ),

    date_act: constr(pattern=r"^\d{4}-\d{2}-\d{2}$") = Field(
        ...,
        description="Дата выставления акта в формате YYYY-MM-DD."
    ),

    date_start: constr(pattern=r"^\d{4}-\d{2}-\d{2}$") = Field(
        ...,
        description="Дата начала периода акта (дата запуска рекламной кампании) в формате YYYY-MM-DD."
    ),

    date_end: constr(pattern=r"^\d{4}-\d{2}-\d{2}$") = Field(
        ...,
        description="Дата окончания периода акта (дата получения чека или формирования бухгалтерского акта) в формате YYYY-MM-DD."
    ),

    excluding_vat: float = Field(
        ...,
        ge=0,
        description="Неотрицательная сумма в рублях с копейками без учета налогов."
    ),

    vat_rate: Literal[0, 5, 7, 10, 20] = Field(
        ...,
        description="Ставка НДС в процентах. Допустимые значения: 0, 5, 7, 10, 20."
    ),

    client_role: Literal["advertiser", "agency", "ors", "publisher"] = Field(
        ...,
        description="Роль клиента (заказчика) в договоре, к которому добавляется акт."
    ),

    contractor_role: Literal["advertiser", "agency", "ors", "publisher"] = Field(
        ...,
        description="Роль подрядчика (исполнителя) в договоре, к которому добавляется акт."
    ),

    ctx: Context = None
) -> ToolResult:
    """
    Создание акта в ORD-провайдере (VK ORD).

    Args:
        contract_external_id: Внешний идентификатор договора, к которому добавляется акт.
        date_act: Дата выставления акта в формате YYYY-MM-DD.
        date_start: Дата начала периода акта (дата запуска рекламной кампании) в формате YYYY-MM-DD.
        date_end: Дата окончания периода акта (дата получения чека или формирования бухгалтерского акта) в формате YYYY-MM-DD.
        excluding_vat: Неотрицательная сумма в рублях с копейками без учета налогов.
        vat_rate: Ставка НДС в процентах.
        client_role: Роль клиента (заказчика) в договоре, к которому добавляется акт.
        contractor_role: Роль подрядчика (исполнителя) в договоре, к которому добавляется акт.
        ctx: Контекст для логирования и прогресс-отчетов.

    Returns:
        ToolResult: результат с act_id и status_code.

    Raises:
        McpError: При ошибках в данных.
    """

    tool_name = "add_act"

    with tracer.start_as_current_span(tool_name) as span:
        span.set_attribute("contract_external_id", contract_external_id)
        span.set_attribute("date_act", date_act)
        span.set_attribute("date_start", date_start)
        span.set_attribute("date_end", date_end)
        span.set_attribute("excluding_vat", excluding_vat)
        span.set_attribute("vat_rate", vat_rate)
        span.set_attribute("client_role", client_role)
        span.set_attribute("contractor_role", contractor_role)

        if ctx:
            await ctx.info(f"🧾 Создаем акт для договора: "
                          f"{contract_external_id =}, {date_act =}, "
                          f"{date_start =}, {date_end =}, "
                          f"{excluding_vat =}, {vat_rate =}, "
                          f"{client_role =}, {contractor_role =}")
            await ctx.report_progress(progress=0, total=100)

        API_CALLS.labels(service="mcp", endpoint=tool_name, status="started").inc()

        try:

            check_dates_in_act(date_act, date_start, date_end)
            check_roles_in_act(client_role, contractor_role)

            if ctx:
                await ctx.debug("🔢 Формируем структуру суммы amount")
            amount = create_amount(excluding_vat=excluding_vat, vat_rate=vat_rate)

            if ctx:
                await ctx.report_progress(40, 100)
                await ctx.info("📡 Отправляем акт в ORD...")

            result = await get_ord_provider().add_act(
                contract_external_id=contract_external_id,
                date_act=date_act,
                date_start=date_start,
                date_end=date_end,
                amount=amount,
                client_role=client_role,
                contractor_role=contractor_role,
            )

            if ctx:
                await ctx.report_progress(100, 100)
                await ctx.info("✅ Акт успешно создан!")

            TOOL_CALLS.labels(tool_name=tool_name, status="success").inc()
            API_CALLS.labels(service="mcp", endpoint=tool_name, status="success").inc()

            span.set_attribute("success", True)
            span.set_attribute("act_id", result.get("act_id"))
            span.set_attribute("status_code", result.get("status_code"))

            return ToolResult(
                content=[TextContent(type="text", text=str(result))],
                structured_content=result,
                meta={
                    "tool_name": tool_name,
                    "contract_external_id": contract_external_id,
                    "date_act": date_act,
                    "date_start": date_start,
                    "date_end": date_end,
                    "excluding_vat": excluding_vat,
                    "vat_rate": vat_rate,
                    "client_role": client_role,
                    "contractor_role": contractor_role,
                }
            )

        except ValueError as e:
            # Ошибки валидации / ошибки 400 от ORD
            span.set_attribute("error", "validation_error")
            span.set_attribute("error_message", str(e))

            TOOL_CALLS.labels(tool_name=tool_name, status="validation_error").inc()
            EXECUTION_ERRORS.labels(tool_name=tool_name, error_type="validation").inc()
            API_CALLS.labels(service="mcp", endpoint=tool_name, status="error").inc()

            if ctx:
                await ctx.error(f"❌ Ошибка при создании акта: {e}")

            raise McpError(
                ErrorData(code=-32602, message=f"Ошибка при создании акта: {e}")
            )

        except Exception as e:
            # Любые неожиданные ошибки
            span.set_attribute("error", "execution_error")
            span.set_attribute("error_message", str(e))

            TOOL_CALLS.labels(tool_name=tool_name, status="error").inc()
            EXECUTION_ERRORS.labels(tool_name=tool_name, error_type="execution").inc()
            API_CALLS.labels(service="mcp", endpoint=tool_name, status="error").inc()

            if ctx:
                await ctx.error(f"💥 Неожиданная ошибка при создании акта: {e}")

            raise McpError(
                ErrorData(code=-32603, message=f"Ошибка при создании акта: {e}")
            )
