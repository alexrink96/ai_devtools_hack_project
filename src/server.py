"""MCP сервер для создания рекламной отчетности с HTTP транспортом."""


import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPHTTPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
OPENTELEMETRY_AVAILABLE = True

PORT = int(os.getenv("PORT", "8000"))

from src.mcp_instance import mcp

import fastmcp
fastmcp.settings.port = PORT
fastmcp.settings.host = "0.0.0.0"

"""Инициализация OpenTelemetry для трейсинга.

Если задан OTEL_ENDPOINT, настраивается OTLP экспорт через OpenTelemetry SDK.
"""
def init_tracing():
    """Инициализация чистого OpenTelemetry для трейсинга."""
    if not OPENTELEMETRY_AVAILABLE:
        print("⚠️ OpenTelemetry недоступен, пропускаем инициализацию")
        return
        
    try:
        otel_endpoint = os.getenv("OTEL_ENDPOINT", "").strip()
        otel_service_name = os.getenv("OTEL_SERVICE_NAME", "mcp-ad-reporting-server")
        
        tracer_provider = TracerProvider(
            resource=Resource.create({
                "service.name": otel_service_name,
                "service.version": "1.0.0",
            })
        )
        
        if otel_endpoint:
            if otel_endpoint.startswith("http"):
                otlp_exporter = OTLPHTTPSpanExporter(endpoint=otel_endpoint)
            else:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                otlp_exporter = OTLPSpanExporter(endpoint=otel_endpoint)
            
            span_processor = BatchSpanProcessor(otlp_exporter)
            tracer_provider.add_span_processor(span_processor)
            print(f"✅ OpenTelemetry настроен для OTLP экспорта: {otel_endpoint}")
        else:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)
            tracer_provider.add_span_processor(span_processor)
            print("✅ OpenTelemetry настроен для консольного вывода")
        
        trace.set_tracer_provider(tracer_provider)
        
        print("✅ OpenTelemetry инициализирован")
        
    except Exception as e:
        print(f"⚠️ Не удалось инициализировать OpenTelemetry: {e}")
        print("ℹ️ Продолжаем работу без трейсинга")

init_tracing()

print("🔧 Загружаем инструменты...")
try:
    from src.tools.add_counterparty import add_counterparty
    print("✅ add_counterparty загружен")
except Exception as e:
    print(f"❌ Ошибка импорта add_counterparty: {e}")
    import traceback
    traceback.print_exc()
    
try:
    from src.tools.add_contract import add_contract
    print("✅ add_contract загружен")
except Exception as e:
    print(f"❌ Ошибка импорта add_contract: {e}")
    import traceback
    traceback.print_exc()
    
try:
    from src.tools.add_advertising import add_advertising
    print("✅ add_advertising загружен")
except Exception as e:
    print(f"❌ Ошибка импорта add_advertising: {e}")
    import traceback
    traceback.print_exc()
    
try:
    from src.tools.add_act import add_act
    print("✅ add_advertising загружен")
except Exception as e:
    print(f"❌ Ошибка импорта add_act: {e}")
    import traceback
    traceback.print_exc()

print("✅ Все инструменты загружены:")
print("  - add_counterparty (добавление контрагента)")
print("  - add_contract (добавление договора)")
print("  - add_advertising (добавление рекламного креатива)")
print("  - add_act (создание акта)")


def main():
    """Запуск MCP сервера с HTTP транспортом."""
    print("=" * 60)
    print("🌐 ЗАПУСК MCP СЕРВЕРА")
    print("=" * 60)
    print(f"🚀 MCP Server: http://0.0.0.0:{PORT}/mcp")
    print("=" * 60)
    print("⏳ Запускаем сервер...")

    # Запускаем MCP сервер с streamable-http транспортом
    try:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=PORT)
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки (Ctrl+C)")
        print("🔄 Выполняем graceful shutdown...")
        print("✅ Сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()