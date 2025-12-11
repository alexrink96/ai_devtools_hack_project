"""Инструмент для добавления контрагента."""
import re
from fastmcp import Context
from mcp.types import TextContent
from opentelemetry import trace
from pydantic import Field, constr
from typing import List, Dict, Any, Literal
from mcp.shared.exceptions import McpError, ErrorData
from src.mcp_instance import mcp
from src.api_ord import get_ord_provider
from src.validators import check_counterparty_name
from src.metrics import TOOL_CALLS, EXECUTION_ERRORS, API_CALLS
from src.tools.utils import ToolResult

tracer = trace.get_tracer(__name__)


@mcp.tool(
    name="add_counterparty",
    description="""Добавление контрагента.
    
Инструмент добавляет контрагента. 
"""
)
async def add_counterparty(
    name: str = Field(
    ..., 
    description="ФИО (например, Иванов Иван Иванович) или юридическое наименование (например, ООО «Север»"
    ),
    
    roles: List[Literal["advertiser", "agency", "ors", "publisher"]] = Field(
    ..., 
    description="Список ролей (advertiser — рекламодатель, agency — рекламное агентство, ors — оператор рекламной системы, publisher — издатель, рекламораспространитель). Можно выбрать несколько."),
    
    type: Literal["physical", "juridical", "ip", "foreign_physical", "foreign_juridical"] = Field(
    ...,
    description="Тип контрагента (physical — физическое лицо, juridical — юридическое лицо, ip — индивидуальный предприниматель, foreign_physical — иностранное физическое лицо, foreign_juridical — иностранное юридическое лицо)."
    ),
    
    inn: constr(pattern=r'^\d{10,12}$') = Field(
    ...,
    description="ИНН контрагента (10 цифр для юридического лица, 12 цифр для физического лица)."
    ),
    
    ctx: Context = None
) -> ToolResult:
    """
    Добавление контрагента.
    
    Инструмент добавляет контрагента.

    Args:
    
        name: ФИО (например, Иванов Иван Иванович) или юридическое наименование (например, ООО «Север»).
        roles: список ролей (advertiser — рекламодатель, agency — рекламное агентство, ors — оператор рекламной системы, publisher — издатель, рекламораспространитель). Можно выбрать несколько.
        type: Тип контрагента (physical — физическое лицо, juridical — юридическое лицо, ip — индивидуальный предприниматель, foreign_physical — иностранное физическое лицо, foreign_juridical — иностранное юридическое лицо).
        inn: ИНН контрагента (10 цифр для юридического лица, 12 цифр для физического лица).
        ctx: контекст для логирования и прогресс-отчетов.

    Returns:
        ToolResult: Результат добавления контрагента с уникальным идентификатором контрагента (counterparty_id) и ответом сервера (status_code).

    Raises:
        McpError: При неверных/слишком больших значениях.
    Note:
        Денежные величины округляются до 2 знаков. В последний месяц — коррекция, чтобы остаток стал 0.00.
    """
    tool_name = "add_counterparty"
    
    with tracer.start_as_current_span(tool_name) as span:
        span.set_attribute("name", name)
        span.set_attribute("roles", roles)
        span.set_attribute("type", type)
        span.set_attribute("inn", inn)
        
        if ctx:
            await ctx.info(f"💼 Добавляем контрагента: {name =}, {roles =}, {type =}, {inn =}")
            await ctx.report_progress(progress=0, total=100)
        
        API_CALLS.labels(
            service="mcp",
            endpoint=tool_name,
            status="started"
        ).inc()
        
        try:
            # Валидация параметров
            check_counterparty_name(name)
            
            ord_provider = get_ord_provider()

            result = await ord_provider.add_counterparty(
                name=name,
                roles=roles,
                juridical_details={
                    "type": type,
                    "inn": inn,
                }
            )
            
            if ctx:
                await ctx.report_progress(progress=100, total=100)
                await ctx.info("✅ Контрагент успешно добавлен!")
            
            span.set_attribute("success", True)
            span.set_attribute("counterparty_id", result.get("counterparty_id", 0))
            span.set_attribute("status_code", result.get("status_code", 0))

            
            TOOL_CALLS.labels(tool_name=tool_name, status="success").inc()
            API_CALLS.labels(
                service="mcp",
                endpoint=tool_name,
                status="success"
            ).inc()
            
            return ToolResult(
                content=[TextContent(type="text", text=str(result))],
                structured_content=result,
                meta={
                    "tool_name": tool_name,
                    "name": name,
                    "roles": roles,
                    "type": type,
                    "inn": inn
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
                await ctx.error(f"❌ Ошибка при добавлении контрагента: {e}")
            
            
            raise McpError(
                ErrorData(
                    code=-32602,  # Invalid params
                    message=f"Ошибка при добавлении контрагента: {e}"
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
                await ctx.error(f"❌ Ошибка при добавлении контрагента: {e}")
            
            
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Ошибка при добавлении контрагента: {e}"
                )
            )