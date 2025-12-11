from abc import ABC, abstractmethod
from typing import List, Dict, Any
import httpx
import uuid
import os
from datetime import datetime
from dotenv import load_dotenv, find_dotenv
import asyncio
from src.utils import format_400_ord_error, create_amount
from src.validators import check_dates_in_act, check_format_date_in_contract, check_texts_length_in_advertising, check_external_ids_of_client_and_contractor

load_dotenv(find_dotenv())

ORD_PROVIDER = str(os.getenv("ORD_PROVIDER"))
ORD_API_KEY = str(os.getenv("ORD_API_KEY"))

class ORD(ABC):
    """Абстрактный класс для ORD-провайдеров.
    
    Всего 4 функции: 
    - add_counterparty — создать контрагента;
    - add_contract — создать договор;
    - add_advertising — создать креатив;
    - add_act — создать акт.
    
    """

    @abstractmethod
    async def add_counterparty(
        self,
        name: str,
        roles: List[str],
        juridical_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Создание агента в ORD.
        
        """
        pass
        
    @abstractmethod
    async def add_contract(
        self,
        type: str,
        client_external_id: str,
        contractor_external_id: str,
        date: str,
        subject_type: str
    ) -> Dict[str, Any]:
        """Создание договора в ORD.
        
        """
        pass
        
    @abstractmethod
    async def add_advertising(
        self,
        kktus: List[str],
        form: str,
        texts: List[str],
        contract_external_ids: List[str],
    ) -> Dict[str, Any]:
        """Создание рекламного креатива."""
        pass

    @abstractmethod
    async def add_act(
        self,
        contract_external_id: str,
        date_act: str,
        date_start: str,
        date_end: str,
        amount: Dict[str, Any],
        client_role: str,
        contractor_role: str,
    ) -> Dict[str, Any]:
        """Создание акта."""
        pass


class VK(ORD):
    """Реализация ORD-клиента для VK."""

    auth_key: str = ORD_API_KEY
    BASE_URL = "https://api-sandbox.ord.vk.com"

    @staticmethod
    def generate_external_id() -> str:
        """Генерирует уникальный counterparty_id."""
        u = uuid.uuid4()
        part1 = u.hex[:11]        # rajs3fu1698
        part2 = u.hex[11:19]      # 1h5a50m5
        return f"{part1}-{part2}"

    async def add_counterparty(
        self,
        name: str,
        roles: List[str],
        juridical_details: Dict[str, Any],
    ) -> Dict[str, Any]:

        counterparty_id = self.generate_external_id()
        url = f"{self.BASE_URL}/v1/person/{counterparty_id}"

        payload = {
            "name": name,
            "roles": roles,
            "juridical_details": juridical_details,
        }

        headers = {
            "Authorization": f"Bearer {self.auth_key}",
            "Content-Type": "application/json",
        }
           
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, json=payload, headers=headers)

            response.raise_for_status()

        except httpx.HTTPStatusError as e:
            # 🔥 обработка неверного API ключа
            if e.response.status_code == 401:
                raise ValueError(f"Некорректный API-ключ. Проверьте переменную окружения ORD_API_KEY.")
            elif e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    msg = format_400_ord_error(error_data)
                except Exception:
                    msg = "Неверные данные контрагента. Убедитесь, что все данные указаны верно."
                raise ValueError(msg)
            # другие ошибки HTTP
            raise
        
        return {
            "counterparty_id": counterparty_id,
            "status_code": response.status_code,
        }
        
    async def add_contract(
        self,
        type: str,
        client_external_id: str,
        contractor_external_id: str,
        date: str,
        subject_type: str
    ) -> Dict[str, Any]:
        """Создает договор (контракт) в VK ORD."""
            
        check_external_ids_of_client_and_contractor(client_external_id, contractor_external_id)

        check_format_date_in_contract(date)

        contract_id = self.generate_external_id()
        url = f"{self.BASE_URL}/v1/contract/{contract_id}"

        payload = {
            "type": type,
            "client_external_id": client_external_id,
            "contractor_external_id": contractor_external_id,
            "date": date,
            "subject_type": subject_type
        }

        headers = {
            "Authorization": f"Bearer {self.auth_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Некорректный API-ключ. Проверьте переменную окружения ORD_API_KEY.")
            elif e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    msg = format_400_ord_error(error_data)
                except Exception:
                    msg = "Неверные данные договора. Проверьте обязательные поля."
                raise ValueError(msg)
            raise

        return {
            "contract_id": contract_id,
            "status_code": response.status_code,
        }
        
        
    async def add_advertising(
        self,
        kktus: List[str],
        form: str,
        texts: List[str],
        contract_external_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Создает новый рекламный креатив в VK ORD.
            
        """
            
        check_texts_length_in_advertising(texts)

        creative_id = self.generate_external_id()
        url = f"{self.BASE_URL}/v3/creative/{creative_id}"
        
        payload = {
            "kktus": kktus,
            "form": form,
            "texts": texts,
            "contract_external_ids": contract_external_ids,
        }
        
        
        headers = {
            "Authorization": f"Bearer {self.auth_key}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, json=payload, headers=headers)
            
            response.raise_for_status()
            
            response_data = response.json()
            erid = response_data.get("erid", None)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError(
                    "Некорректный API-ключ. Проверьте переменную окружения ORD_API_KEY."
                )
            elif e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    msg = format_400_ord_error(error_data)
                except Exception:
                    msg = "Неверные данные креатива. Убедитесь, что все данные указаны верно."
                raise ValueError(msg)
                
            elif e.response.status_code == 403:
                raise ValueError(
                    "Доступ запрещен. Возможно, переданы недопустимые параметры."
                )

            raise
        
        return {
            "erid": erid,
            "creative_id": creative_id,
            "status_code": response.status_code,
        }
        
    async def add_act(
        self,
        contract_external_id: str,
        date_act: str, 
        date_start: str,
        date_end: str,
        amount: Dict[str, Any],
        client_role: str,
        contractor_role: str,
    ) -> Dict[str, Any]:
        """
        Создает новый акт в VK ORD.
        
        """
        # Генерация внешнего ID для акта
        act_id = self.generate_external_id()
        url = f"{self.BASE_URL}/v4/invoice/{act_id}"
        
        # Формирование payload согласно схеме
        payload = {
            "contract_external_id": contract_external_id,
            "date": date_act,  
            "date_start": date_start,
            "date_end": date_end,
            "amount": amount,
            "client_role": client_role,
            "contractor_role": contractor_role,
        }
        
        # Валидация дат
        check_dates_in_act(date_act, date_start, date_end)
        
        headers = {
            "Authorization": f"Bearer {self.auth_key}",
            "Content-Type": "application/json",
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, json=payload, headers=headers)
            
            response.raise_for_status()
            
        except httpx.HTTPStatusError as e:
            # Обработка ошибок
            if e.response.status_code == 401:
                raise ValueError(
                    "Некорректный API-ключ. Проверьте переменную окружения ORD_API_KEY."
                )
            elif e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    msg = format_400_ord_error(error_data)
                except Exception:
                    msg = "Неверные данные. Убедитесь, что все данные указаны верно."
                raise ValueError(msg)
                
            elif e.response.status_code == 403:
                raise ValueError("Доступ запрещен. Убедитесь в корректности прав доступа.")

            raise
        
        # Успешный ответ
        return {
            "act_id": act_id,
            "status_code": response.status_code,
        }

def get_ord_provider() -> ORD:
    """Возвращает реализацию ORD в зависимости от env."""
    provider = ORD_PROVIDER.lower()

    if provider == "vk":
        return VK()

    raise ValueError(f"Неизвестный ORD-провайдер: {provider}. На данный момент поддерживается только VK ORD провайдер.")
    

    
