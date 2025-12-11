from decimal import Decimal
from typing import Dict, Any

def format_400_ord_error(error_data: dict) -> str:
    """
    Форматирует 400-ошибку ORD в человекочитаемый вид.

    Args:
        error_data: JSON, полученный от ORD:
        {
          "error": "string",
          "errors": [
            {
              "field": "...",
              "error_code": "...",
              "message": "...",
              "values": [...]
            }
          ]
        }

    Returns:
        Строку с подробным описанием всех ошибок.
    """

    # Основное сообщение (верхний error или общий fallback)
    base = error_data.get("error") or error_data.get("message") or "Ошибка валидации данных."

    # Детали ошибок
    details = []

    for err in error_data.get("errors", []):
        # Определяем, откуда пришло поле
        field = (
            err.get("field") 
            or err.get("query_param") 
            or err.get("path_param") 
            or "unknown_field"
        )

        code = err.get("error_code", "unknown_code")
        message = err.get("message", "")
        values = err.get("values", [])

        value_text = f" Значение: {values[0]}" if values else ""

        details.append(f"• [{field}] {message} ({code}){value_text}")

    # Если деталей нет — вернём только верхнее сообщение
    if not details:
        return base

    return base + ":\n" + "\n".join(details)
    
    
def create_amount(
    excluding_vat: float,
    vat_rate: int = 20, 
) -> Dict[str, Any]:
    """
    Создает структуру amount для акта.
    
    Args:
        excluding_vat: Сумма без НДС.
        vat_rate: Ставка НДС ("0%", "10%", "20%", "no_vat").
        
    Returns:
        Структура amount для использования в add_act.
    """
    # Конвертируем в Decimal для точных вычислений
    excl_vat_decimal = Decimal(str(excluding_vat))
    
    # Рассчитываем НДС и сумму с НДС
    if vat_rate == 0:
        vat_decimal = Decimal('0')
    elif vat_rate == 5:
        vat_decimal = excl_vat_decimal * Decimal('0.05')
    elif vat_rate == 7:
        vat_decimal = excl_vat_decimal * Decimal('0.07')
    elif vat_rate == 10:
        vat_decimal = excl_vat_decimal * Decimal('0.10')
    elif vat_rate == 20:
        vat_decimal = excl_vat_decimal * Decimal('0.20')
    else:
        raise ValueError(f"Неподдерживаемая ставка НДС: {vat_rate}")
    
    incl_vat_decimal = excl_vat_decimal + vat_decimal
    
    return {
        "services": {
            "excluding_vat": str(excl_vat_decimal.quantize(Decimal('0.01'))),
            "vat_rate": str(vat_rate),
            "vat": str(vat_decimal.quantize(Decimal('0.01'))),
            "including_vat": str(incl_vat_decimal.quantize(Decimal('0.01'))),
        }
    }
