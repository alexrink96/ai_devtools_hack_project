from datetime import datetime, timezone
from datetime import date as date_type
from typing import List

from src.config import (
    MAX_COUNTERPARTY_LENGTH_NAME
)


def check_counterparty_name(name: str) -> None:
    if len(name) > MAX_COUNTERPARTY_LENGTH_NAME:
        raise ValueError(f"Название контрагента слишком длинное (максимум {MAX_COUNTERPARTY_LENGTH_NAME} символов).")
        
def check_format_date_in_contract(date: str) -> None:
    try:
        contract_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Дата должна быть в формате YYYY-MM-DD.")
        
def check_external_ids_of_client_and_contractor(client_external_id: str, contractor_external_id: str) -> None:
    if client_external_id == contractor_external_id:
        raise ValueError("Поля client_external_id и contractor_external_id должны быть разными.")
        
def check_texts_length_in_advertising(texts: List) -> None:
    total_text_length = sum(len(text) for text in texts)
    if total_text_length > 65000:
        raise ValueError(f"Общая длина текстов ({total_text_length}) превышает 65,000 символов")
        
        
def check_dates_in_act(date_act: str, date_start: str, date_end: str, ) -> None:
    try:
        date_obj = datetime.strptime(date_act, "%Y-%m-%d").date()
        start_obj = datetime.strptime(date_start, "%Y-%m-%d").date()
        end_obj = datetime.strptime(date_end, "%Y-%m-%d").date()
        
        # Проверка минимальной даты
        min_date = date_type(1991, 1, 1)
        if date_obj < min_date or start_obj < min_date or end_obj < min_date:
            raise ValueError("Дата не может быть раньше 1991-01-01")
        
        # Проверка что date_start <= date_end
        if start_obj > end_obj:
            raise ValueError("date_start не может быть позже date_end")
        
        # Проверка что date не в будущем (относительно UTC)
        today = datetime.now(timezone.utc).date()
        if date_obj > today:
            raise ValueError("Дата акта не может быть в будущем")
            
    except ValueError as e:
        if "does not match format" in str(e):
            raise ValueError("Неверный формат даты. Используйте YYYY-MM-DD")
        raise
        
        
def check_roles_in_act(client_role: str, contractor_role: str) -> None:
    if client_role == 'advertiser':
        raise ValueError("К сожалению, на данный момент не поддерживается создание акта, в котором роль заказчика выполняет рекламодатель.")
        
