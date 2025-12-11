"""Инструмент для добавления рекламного креатива."""
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
    name="add_advertising",
    description="""Создание текстового рекламного креатива в ORD.
    
Инструмент создает текстовый рекламный креатив с указанными параметрами.

"""
)
async def add_advertising(
    kktus: List[constr(pattern=r'^\d+\.\d+\.\d+$')] = Field(
        ...,
        description="""Список кодов ККТУ рекламируемых товаров или услуг.
        Для обычных креативов требуется 1 элемент, для кобрендинговых от 1 до 16.
        Формат: 'X.X.X' (например, '1.1.1')""",
        min_length=1,
        max_length=16
    ),
    
    texts: List[constr(min_length=1, max_length=65000)] = Field(
        ...,
        description="""Список текстов креатива.
        Общая максимальная длина всех текстов - 65,000 символов.
        Требуется хотя бы один текст.""",
        min_length=1
    ),
    
    contract_external_ids: List[str] = Field(
        ...,
        description="""Список внешних идентификаторов договоров, для которых создается креатив.""",
        min_length=1
    ),
    
    ctx: Context = None
) -> ToolResult:
    """
    Создание текстового рекламного креатива в ORD.
    
    Инструмент создает текстового рекламный креатив.

    Args:
        kktus: Список кодов ККТУ креатива. Для обычных креативов требуется 1 элемент, для кобрендинговых от 1 до 16. Например, List [ "1.1.1", "1.1.2" ].
        texts: Список текстов креатива.
        contract_external_ids: Список внешних идентификаторов изначальных договоров, для которых создается креатив.
        ctx: Контекст для логирования и прогресс-отчетов.

    Returns:
        ToolResult: Результат создания креатива с creative_id, erid и статусом ответа сервера.

    Raises:
        McpError: При неверных параметрах или ошибках API.
    """
    tool_name = "add_advertising"
    
    with tracer.start_as_current_span(tool_name) as span:
        span.set_attribute("kktus", kktus)
        span.set_attribute("texts", texts)
        span.set_attribute("contract_external_ids", contract_external_ids)
        
        if ctx:
            await ctx.info(f"🎨 Создаем рекламный креатив: "
                          f"{kktus =}, {texts =}, "
                          f"{contract_external_ids =}")
            await ctx.report_progress(progress=0, total=100)
        
        API_CALLS.labels(
            service="mcp",
            endpoint=tool_name,
            status="started"
        ).inc()
        
        try:

            if ctx:
                await ctx.report_progress(progress=30, total=100)
            
            # Получаем провайдера и создаем креатив
            ord_provider = get_ord_provider()
            
            if ctx:
                await ctx.report_progress(progress=60, total=100)
            
            result = await ord_provider.add_advertising(
                kktus=kktus,
                form="text_block",
                texts=texts,
                contract_external_ids=contract_external_ids
            )
            
            if ctx:
                await ctx.report_progress(progress=100, total=100)
                await ctx.info(f"✅ Креатив успешно создан! ID: {result.get('creative_id', 'N/A')}, ERID: {result.get('erid', 'N/A')}")
            
            # Логируем успех
            span.set_attribute("success", True)
            span.set_attribute("creative_id", result.get("creative_id", ""))
            span.set_attribute("erid", result.get("erid", ""))
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
                    "kktus": kktus,
                    "texts": texts,
                    "contract_external_ids": contract_external_ids
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
                await ctx.error(f"❌ Ошибка валидации при создании креатива: {e}")
            
            raise McpError(
                ErrorData(
                    code=-32602,  # Invalid params
                    message=f"Ошибка валидации при создании креатива: {e}"
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
                await ctx.error(f"❌ Ошибка при создании креатива: {e}")
            
            raise McpError(
                ErrorData(
                    code=-32603, 
                    message=f"Ошибка при создании креатива: {e}"
                )
            )