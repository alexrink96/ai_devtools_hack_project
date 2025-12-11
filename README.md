# Инструкция для жюри

## Описание проекта

Это MCP-сервер, автоматизирующий создание рекламной отчетности в ВК ОРД (оператор рекламных данных).

⚠️ Важно: **необходимо получить ключ доступа API VK ORD**. Для этого необходимо перейти в демо-версию кабинета (созданную для изучения интерфейса) и получить ключ: https://sandbox.ord.vk.com/keys. Ссылка на документацию API VK ORD: https://ord.vk.com/help/api/api.html.

## Структура проекта
```
project/
│── tools.json
│── env_options.json
│── Dockerfile
│── requirements.txt
│── .env        <-- файл с API ключом и указанием ОРД-провайдера
└── src/
```    

## Шаги запуска
1. Клонируйте репозиторий и перейдите в корень проекта
```
git clone https://github.com/alexrink96/ai_devtools_hack_project
cd <project_folder>
```
2. Создайте файл .env в корне проекта. Файл **обязателен**, в него вставляется ORD-провайдер (VK), API ключ (надо получить API-ключ VK ORD), PORT (8000), LOG_LEVEL (INFO):
```
ORD_PROVIDER=VK
ORD_API_KEY=ваш_ключ
PORT=8000
LOG_LEVEL=INFO
```
3. Соберите Docker-образ
```
docker buildx build --platform linux/amd64 -t mcp-ad-reporting .
```
4. Запустите контейнер с пробросом порта и .env
```
docker run -p 8000:8000 --env-file .env mcp-ad-reporting
```
5. MCP-сервер доступе по ссылке:
```
http://localhost:8000/mcp
```
