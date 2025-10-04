from fastmcp import FastMCP
from typing import Any
import requests
import os
import numpy
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
import pickle
import dateutil.parser
import random

load_dotenv()

mcp = FastMCP(
    name="Finam API MCP",
    instructions="""Ассистент для работы с Finam Trade API - полный доступ к биржевой торговле через Finam.
Используй соответствующие инструменты для анализа рынка, управления портфелем и выполнения торговых операций через Finam API."""
)

access_token = os.getenv("FINAM_ACCESS_TOKEN", "")
session = requests.Session()


async def get_jwt_token() -> str:
    """
    Аутентификация в Finam Trade API и получение JWT токена.

    Выполняет POST запрос к эндпоинту /v1/sessions для получения временного JWT токена
    по постоянному access token.

    Returns:
        str: JWT токен для авторизации запросов к API

    Example:
        >>> get_jwt_token()
        {"token": "jwt_token"}
    """
    return requests.post("https://api.finam.ru/v1/sessions", json={'secret': access_token}).json()['token']


async def execute_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
    """
    Универсальная функция для выполнения HTTP запросов к Finam Trade API.

    Args:
        method (str): HTTP метод запроса ('GET', 'POST', 'PUT', 'DELETE', 'PATCH')
        path (str): Путь к эндпоинту API
        **kwargs: Дополнительные параметры для передачи в requests

    Returns:
        dict[str, Any]: Ответ API в формате JSON
    """
    url = f"https://api.finam.ru{path}"
    jwt_token = await get_jwt_token()
    session.headers.update({
        "Authorization": f"{jwt_token}",
        "Content-Type": "application/json",
    })
    try:
        response = session.request(method, url, timeout=30, **kwargs)
        response.raise_for_status()
        print(response.text)

        if not response.content:
            return {"status": "success", "message": "Operation completed"}

        return response.json()

    except requests.exceptions.HTTPError as e:
        error_detail = {"error": str(e), "status_code": e.response.status_code if e.response else None}

        try:
            if e.response and e.response.content:
                error_detail["details"] = e.response.json()
        except Exception:
            error_detail["details"] = e.response.text if e.response else None

        return error_detail

    except Exception as e:
        return {"error": str(e), "type": type(e).__name__}


@mcp.tool
async def get_orderbook(symbol: str) -> dict[str, Any]:
    """
    Получить текущий стакан котировок по инструменту.

    Args:
        symbol (str): Тикер инструмента в формате "<TICKER>@<EXCHANGE>"

    Returns:
        dict[str, Any]: JSON объект с биржевым стаканом:
            - symbol (str): Символ инструмента
            - orderbook (dict): Стакан котировок
            - rows (list): Список уровней стакана, каждый уровень содержит:
                - price (dict): Цена с value в строковом формате
                - sell_size (dict): Объем продажи с value в строковом формате
                - action (str): Действие (ACTION_ADD, etc.)
                - mpid (str): Идентификатор маркет-мейкера
                - timestamp (str): Время обновления

    Example:
        >>> get_orderbook("YDEX@MISX")
        {
            "symbol": "YDEX@MISX",
            "orderbook": {
                "rows": [
                    {
                        "price": {"value": "4354.5"},
                        "sell_size": {"value": "18.0"},
                        "action": "ACTION_ADD",
                        "mpid": "",
                        "timestamp": "2025-07-24T08:43:04.573168Z"
                    }
                ]
            }
        }
    """
    return await execute_request("GET", f"/v1/instruments/{symbol}/orderbook")


@mcp.tool
async def get_candles(
        symbol: str, timeframe: str = "TIME_FRAME_D", start: str | None = None, end: str | None = None
) -> dict[str, Any]:
    """
    Получить исторические данные по инструменту (агрегированные свечи).

    Args:
        symbol (str): Тикер инструмента в формате "<TICKER>@<EXCHANGE>"
        timeframe (str): Таймфрейм свечей:
            - "TIME_FRAME_M1" → 1 минута
            - "TIME_FRAME_H1" → 1 час
            - "TIME_FRAME_D" → 1 день
        start (str | None): Начало периода в формате ISO 8601
        end (str | None): Конец периода в формате ISO 8601

    Returns:
        dict[str, Any]: JSON объект со списком свечей:
            - symbol (str): Символ инструмента
            - bars (list): Список свечей, каждая свеча содержит:
                - timestamp (str): Метка времени открытия свечи
                - open (dict): Цена открытия с value в строковом формате
                - high (dict): Максимальная цена с value в строковом формате
                - low (dict): Минимальная цена с value в строковом формате
                - close (dict): Цена закрытия с value в строковом формате
                - volume (dict): Объем торгов с value в строковом формате

    Example:
        >>> get_candles("YDEX@MISX", "TIME_FRAME_D", "2025-03-01T00:00:00Z", "2025-03-02T00:00:00Z")
        {
            "symbol": "YDEX@MISX",
            "bars": [
                {
                    "timestamp": "2025-03-01T05:00:00Z",
                    "open": {"value": "4450.0"},
                    "high": {"value": "4455.0"},
                    "low": {"value": "4427.0"},
                    "close": {"value": "4438.0"},
                    "volume": {"value": "13967.0"}
                }
            ]
        }
    """
    params = {"timeframe": timeframe}
    if start:
        params["interval.start_time"] = start
    else:
        params["interval.start_time"] = "2025-03-01T00:00:00Z"
    if end:
        params["interval.end_time"] = end
    else:
        params["interval.end_time"] = "2025-03-15T00:00:00Z"
    return await execute_request("GET", f"/v1/instruments/{symbol}/bars", params=params)


@mcp.tool
async def get_account(account_id: str) -> dict[str, Any]:
    """
    Получить информацию по конкретному аккаунту.

    Args:
        account_id (str): Идентификатор счёта.

    Returns:
        dict[str, Any]: JSON объект с информацией об аккаунте:
            - account_id (str): Идентификатор счёта
            - type (str): Тип аккаунта (UNION, etc.)
            - status (str): Статус аккаунта (ACCOUNT_ACTIVE, etc.)
            - equity (dict): Доступные средства плюс стоимость открытых позиций
            - unrealized_profit (dict): Нереализованная прибыль
            - positions (list): Список открытых позиций, каждая позиция содержит:
                - symbol (str): Символ инструмента
                - quantity (dict): Количество со знаком (long/short)
                - average_price (dict): Средняя цена открытия
                - current_price (dict): Текущая цена
                - daily_pnl (dict): Прибыль/убыток за день
                - unrealized_pnl (dict): Нереализованная прибыль/убыток
            - cash (list): Денежные средства по валютам
            - portfolio_mc (dict): Портфель Московской Биржи:
                - available_cash (dict): Доступные денежные средства
                - initial_margin (dict): Начальная маржа
                - maintenance_margin (dict): Поддерживающая маржа

    Example:
        >>> get_account("TRQD05:989213")
        {
            "account_id": "TRQD05:989213",
            "type": "UNION",
            "status": "ACCOUNT_ACTIVE",
            "equity": {"value": "989.38"},
            "unrealized_profit": {"value": "0.4"},
            "positions": [
                {
                    "symbol": "AFLT@MISX",
                    "quantity": {"value": "10.0"},
                    "average_price": {"value": "62.72"},
                    "current_price": {"value": "62.76"},
                    "daily_pnl": {"value": "0.4"},
                    "unrealized_pnl": {"value": "0.4"}
                }
            ],
            "cash": [
                {
                    "currency_code": "RUB",
                    "units": "361",
                    "nanos": 7800000
                }
            ],
            "portfolio_mc": {
                "available_cash": {"value": "361.78"},
                "initial_margin": {"value": "627.6"},
                "maintenance_margin": {"value": "313.8"}
            }
        }
    """
    return await execute_request("GET", f"/v1/accounts/{account_id}")


@mcp.tool
async def get_orders(account_id: str) -> dict[str, Any]:
    """
    Получить список заявок для аккаунта.

    Args:
        account_id (str): Идентификатор счёта.

    Returns:
        dict[str, Any]: JSON объект со списком заявок:
            - orders (list): Список заявок, каждая заявка содержит:
                - order_id (str): Идентификатор заявки
                - exec_id (str): Идентификатор исполнения
                - status (str): Статус заявки (ORDER_STATUS_FILLED, etc.)
                - order (dict): Данные заявки:
                    - account_id (str): Идентификатор счёта
                    - symbol (str): Символ инструмента
                    - quantity (dict): Количество в штуках
                    - side (str): Сторона (SIDE_BUY, SIDE_SELL)
                    - type (str): Тип заявки (ORDER_TYPE_MARKET, etc.)
                    - time_in_force (str): Срок действия
                    - stop_condition (str): Условие стопа
                    - legs (list): Ноги для мульти-лег заявок
                    - client_order_id (str): Клиентский идентификатор
                    - valid_before (str): Срок действия
                - transact_at (str): Дата и время выставления заявки

    Example:
        >>> get_orders("TRQD05:989213")
        {
            "orders": [
                {
                    "order_id": "71218204651",
                    "exec_id": "trd.14352127845.1759374704214077",
                    "status": "ORDER_STATUS_FILLED",
                    "order": {
                        "account_id": "TRQD05:989213",
                        "symbol": "AFLT@MISX",
                        "quantity": {"value": "10.0"},
                        "side": "SIDE_BUY",
                        "type": "ORDER_TYPE_MARKET",
                        "time_in_force": "TIME_IN_FORCE_UNSPECIFIED",
                        "stop_condition": "STOP_CONDITION_UNSPECIFIED",
                        "legs": [],
                        "client_order_id": "",
                        "valid_before": "VALID_BEFORE_UNSPECIFIED"
                    },
                    "transact_at": "2025-10-02T13:16:04.338Z"
                }
            ]
        }
    """
    return await execute_request("GET", f"/v1/accounts/{account_id}/orders")


@mcp.tool
async def get_order(order_id: str, account_id: str) -> dict[str, Any]:
    """
    Получить информацию о конкретном ордере.

    Args:
        account_id (str): Идентификатор счёта.
        order_id (str): Идентификатор заявки

    Returns:
        dict[str, Any]: JSON объект с деталями заявки:
            - order_id (str): Идентификатор заявки
            - exec_id (str): Идентификатор исполнения
            - status (str): Статус заявки
            - order (dict): Данные заявки (аналогично get_orders)
            - transact_at (str): Дата и время выставления
            - accept_at (str): Дата и время принятия
            - withdraw_at (str): Дата и время отмены

    Example:
        >>> get_order("71218204651", "TRQD05:989213")
        {
            "order_id": "71218204651",
            "exec_id": "trd.14352127845.1759374704214077",
            "status": "ORDER_STATUS_FILLED",
            "order": {
                "account_id": "TRQD05:989213",
                "symbol": "AFLT@MISX",
                "quantity": {"value": "10.0"},
                "side": "SIDE_BUY",
                "type": "ORDER_TYPE_MARKET",
                "time_in_force": "TIME_IN_FORCE_UNSPECIFIED",
                "stop_condition": "STOP_CONDITION_UNSPECIFIED",
                "legs": [],
                "client_order_id": "",
                "valid_before": "VALID_BEFORE_UNSPECIFIED"
            },
            "transact_at": "2025-10-02T13:16:04.338Z"
        }
    """
    return await execute_request("GET", f"/v1/accounts/{account_id}/orders/{order_id}")


@mcp.tool
async def create_order(order_data: dict[str, Any], account_id: str) -> dict[str, Any]:
    """
    Выставить биржевую заявку.

    Args:
        account_id (str): Идентификатор счёта.
        order_data (dict[str, Any]): Параметры заявки:
            - symbol (str): Символ инструмента
            - quantity (str): Количество в штуках (строковое значение)
            - side (str): Сторона (SIDE_BUY, SIDE_SELL)
            - type (str): Тип заявки (ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET, etc.)
            - time_in_force (str): Срок действия
            - limit_price (str): Цена для лимитной заявки (опционально)
            - stop_price (str): Стоп-цена (опционально)
            - stop_condition (str): Условие стопа (опционально)
            - legs (list): Ноги для мульти-лег заявок (опционально)
            - client_order_id (str): Клиентский идентификатор (опционально)
            - valid_before (str): Срок действия условной заявки (опционально)
            - comment (str): Метка заявки (опционально)

    Returns:
        dict[str, Any]: JSON объект с подтверждением создания заявки

    Example:
        >>> create_order({
        ...     "symbol": "AFLT@MISX",
        ...     "quantity": "10.0",
        ...     "side": "SIDE_BUY",
        ...     "type": "ORDER_TYPE_LIMIT",
        ...     "time_in_force": "TIME_IN_FORCE_DAY",
        ...     "limit_price": "50.0",
        ...     "client_order_id": "test020"
        ... }, "TRQD05:989213")
        {
            "order_id": "71218896129",
            "exec_id": "ord.71218896129.1759374649567648",
            "status": "ORDER_STATUS_NEW",
            "order": {
                "account_id": "TRQD05:989213",
                "symbol": "AFLT@MISX",
                "quantity": {"value": "10.0"},
                "side": "SIDE_BUY",
                "type": "ORDER_TYPE_LIMIT",
                "time_in_force": "TIME_IN_FORCE_DAY",
                "limit_price": {"value": "50.0"},
                "stop_condition": "STOP_CONDITION_UNSPECIFIED",
                "legs": [],
                "client_order_id": "test020",
                "valid_before": "VALID_BEFORE_UNSPECIFIED"
            },
            "transact_at": "2025-10-02T13:31:07.417Z"
        }
    """
    return await execute_request("POST", f"/v1/accounts/{account_id}/orders", json=order_data)


@mcp.tool
async def cancel_order(order_id: str, account_id: str) -> dict[str, Any]:
    """
    Отменить биржевую заявку.

    Args:
        account_id (str): Идентификатор счёта.
        order_id (str): Идентификатор заявки

    Returns:
        dict[str, Any]: JSON объект с подтверждением отмены заявки

    Example:
        >>> cancel_order("71218896129", "TRQD05:989213")
        {
            "order_id": "71218896129",
            "exec_id": "ord.71218896129.1759374649627058",
            "status": "ORDER_STATUS_CANCELED",
            "order": {
                "account_id": "TRQD05:989213",
                "symbol": "AFLT@MISX",
                "quantity": {"value": "10.0"},
                "side": "SIDE_BUY",
                "type": "ORDER_TYPE_LIMIT",
                "time_in_force": "TIME_IN_FORCE_DAY",
                "limit_price": {"value": "50.0"},
                "stop_condition": "STOP_CONDITION_UNSPECIFIED",
                "legs": [],
                "client_order_id": "01K6JHX3R11GNGN88TP6A411B0",
                "valid_before": "VALID_BEFORE_UNSPECIFIED"
            },
            "transact_at": "2025-10-02T13:33:56.188Z"
        }
    """
    return await execute_request("DELETE", f"/v1/accounts/{account_id}/orders/{order_id}")


@mcp.tool
async def get_trades(account_id: str, start: str | None = None, end: str | None = None) -> dict[str, Any]:
    """
    Получить историю по сделкам аккаунта.

    Args:
        account_id (str): Идентификатор счёта.
        start (str | None): Начало периода в формате ISO 8601
        end (str | None): Конец периода в формате ISO 8601

    Returns:
        dict[str, Any]: JSON объект со списком сделок:
            - trades (list): Список сделок, каждая сделка содержит:
                - trade_id (str): Идентификатор сделки
                - symbol (str): Символ инструмента
                - price (dict): Цена исполнения
                - size (dict): Размер сделки
                - side (str): Сторона (SIDE_BUY, SIDE_SELL)
                - timestamp (str): Время исполнения
                - order_id (str): Идентификатор заявки
                - account_id (str): Идентификатор счёта

    Example:
        >>> get_trades("TRQD05:989213", "2025-07-25T00:00:00Z", "2025-07-26T00:00:00Z")
        {
            "trades": [
                {
                    "trade_id": "13771435993",
                    "symbol": "AFLT@MISX",
                    "price": {"value": "58.74"},
                    "size": {"value": "10.0"},
                    "side": "SIDE_SELL",
                    "timestamp": "2025-07-25T07:58:13Z",
                    "order_id": "68675036456",
                    "account_id": "TRQD05:989213"
                }
            ]
        }
    """
    params = {}
    if start:
        params["interval.start_time"] = start
    else:
        params["interval.start_time"] = "2025-03-01T00:00:00Z"
    if end:
        params["interval.end_time"] = end
    else:
        params["interval.end_time"] = "2025-03-15T00:00:00Z"
    return await execute_request("GET", f"/v1/accounts/{account_id}/trades", params=params)


@mcp.tool
async def get_positions(account_id: str) -> dict[str, Any]:
    """
    Получить открытые позиции по счету.
    Основной интерес представляет поле 'positions' в ответе API, содержащее список открытых позиций.
    Но при необходимости при формировании ответа пользователю можешь пользоваться и другими полями.

    Args:
        account_id (str): Идентификатор счёта.

    Returns:
        dict[str, Any]: JSON объект с информацией об аккаунте:
            - account_id (str): Идентификатор счёта
            - type (str): Тип аккаунта (UNION, etc.)
            - status (str): Статус аккаунта (ACCOUNT_ACTIVE, etc.)
            - equity (dict): Доступные средства плюс стоимость открытых позиций
            - unrealized_profit (dict): Нереализованная прибыль
            - positions (list): Список открытых позиций, каждая позиция содержит:
                - symbol (str): Символ инструмента
                - quantity (dict): Количество со знаком (long/short)
                - average_price (dict): Средняя цена открытия
                - current_price (dict): Текущая цена
                - daily_pnl (dict): Прибыль/убыток за день
                - unrealized_pnl (dict): Нереализованная прибыль/убыток
            - cash (list): Денежные средства по валютам
            - portfolio_mc (dict): Портфель Московской Биржи:
                - available_cash (dict): Доступные денежные средства
                - initial_margin (dict): Начальная маржа
                - maintenance_margin (dict): Поддерживающая маржа

    Example:
        >>> get_positions("TRQD05:989213")
        {
            "account_id": "TRQD05:989213",
            "type": "UNION",
            "status": "ACCOUNT_ACTIVE",
            "equity": {"value": "989.38"},
            "unrealized_profit": {"value": "0.4"},
            "positions": [
                {
                    "symbol": "AFLT@MISX",
                    "quantity": {"value": "10.0"},
                    "average_price": {"value": "62.72"},
                    "current_price": {"value": "62.76"},
                    "daily_pnl": {"value": "0.4"},
                    "unrealized_pnl": {"value": "0.4"}
                }
            ],
            "cash": [
                {
                    "currency_code": "RUB",
                    "units": "361",
                    "nanos": 7800000
                }
            ],
            "portfolio_mc": {
                "available_cash": {"value": "361.78"},
                "initial_margin": {"value": "627.6"},
                "maintenance_margin": {"value": "313.8"}
            }
        }
    """
    return await execute_request("GET", f"/v1/accounts/{account_id}")


@mcp.tool
async def get_session_details() -> dict[str, Any]:
    """
    Получить информацию о токене сессии.

    Returns:
        dict[str, Any]: JSON объект с деталями сессии:
            - created_at (str): Дата и время создания токена
            - expires_at (str): Дата и время экспирации токена
            - md_permissions (list): Доступ к рыночным данным:
                - quote_level (str): Уровень котировок
                - delay_minutes (int): Задержка в минутах
                - mic (str): Идентификатор биржи
                - country (str): Страна
                - continent (str): Континент
                - worldwide (bool): Весь мир
            - account_ids (list): Идентификаторы доступных аккаунтов
            - readonly (bool): Режим только для чтения

    Example:
        >>> get_session_details()
        {
            "created_at": "2025-07-24T07:51:27Z",
            "expires_at": "2025-07-24T08:06:30Z",
            "md_permissions": [
                {
                    "quote_level": "QUOTE_LEVEL_DEPTH_OF_MARKET",
                    "delay_minutes": 0,
                    "mic": "#RBRD"
                }
            ],
            "account_ids": ["TRQD05:989213"],
            "readonly": false
        }
    """
    return await execute_request("POST", "/v1/sessions/details", json={"token": await get_jwt_token()})


@mcp.tool
async def get_assets() -> dict[str, Any]:
    """
    Получить список всех доступных инструментов с их описанием.

    Возвращает полный перечень финансовых инструментов, доступных для торговли
    через Finam API, включая акции, облигации, фьючерсы и другие инструменты.

    Returns:
        dict[str, Any]: JSON объект со списком инструментов:
            - assets (list): Список инструментов, каждый инструмент содержит:
                - symbol (str): Символ инструмента в формате ticker@mic
                - id (str): Внутренний идентификатор инструмента
                - ticker (str): Тикер инструмента
                - mic (str): MIC идентификатор биржи
                - isin (str): ISIN идентификатор инструмента
                - type (str): Тип инструмента (EQUITIES, BONDS, FUTURES, etc.)
                - name (str): Полное наименование инструмента

    Использовать когда:
        - Нужно получить полный список доступных для торговли инструментов
        - Требуется найти инструмент по названию или тикеру
        - Необходимо получить базовую информацию об инструментах

    Example:
        >>> get_assets()
        {
            "assets": [
                {
                    "symbol": "AAPL@XNGS",
                    "id": "75022",
                    "ticker": "AAPL",
                    "mic": "XNGS",
                    "isin": "US0378331005",
                    "type": "EQUITIES",
                    "name": "Apple Inc."
                },
                {
                    "symbol": "SBER@RUSX",
                    "id": "419750",
                    "ticker": "SBER",
                    "mic": "RUSX",
                    "isin": "RU0009029540",
                    "type": "EQUITIES",
                    "name": "ПАО 'Сбербанк России', ао"
                }
            ]
        }
    """
    return await execute_request("GET", "/v1/assets")


@mcp.tool
async def get_exchanges() -> dict[str, Any]:
    """
    Получить список доступных бирж с их названиями и MIC кодами.

    Возвращает информацию о всех биржах, поддерживаемых Finam API,
    включая российские и международные торговые площадки.

    Returns:
        dict[str, Any]: JSON объект со списком бирж:
            - exchanges (list): Список бирж, каждая биржа содержит:
                - mic (str): MIC идентификатор биржи (стандарт ISO 10383)
                - name (str): Полное наименование биржи

    Использовать когда:
        - Нужно получить список доступных бирж
        - Требуется найти MIC код конкретной биржи
        - Необходимо проверить поддержку определенной торговой площадки

    Example:
        >>> get_exchanges()
        {
            "exchanges": [
                {
                    "mic": "XCME",
                    "name": "CHICAGO MERCANTILE EXCHANGE"
                },
                {
                    "mic": "XCBT",
                    "name": "CHICAGO BOARD OF TRADE"
                },
                {
                    "mic": "RTSX",
                    "name": "MOSCOW EXCHANGE - DERIVATIVES MARKET"
                },
                {
                    "mic": "MISX",
                    "name": "MOSCOW EXCHANGE - ALL MARKETS"
                },
                {
                    "mic": "XNYS",
                    "name": "NEW YORK STOCK EXCHANGE, INC."
                }
            ]
        }
    """
    return await execute_request("GET", "/v1/exchanges")


@mcp.tool
async def get_asset(symbol: str, account_id: str = "{account_id}") -> dict[str, Any]:
    """
    Получить детальную информацию по конкретному инструменту.

    Возвращает расширенные данные об инструменте, включая торговые параметры,
    спецификации лота, шаги цены и другую техническую информацию.

    Args:
        symbol (str): Символ инструмента в формате "<TICKER>@<MIC>"
        account_id (str): Идентификатор счёта. Если не задан, используется значение по-умолчанию "{account_id}

    Returns:
        dict[str, Any]: JSON объект с детальной информацией об инструменте:
            - board (str): Код режима торгов на бирже
            - id (str): Внутренний идентификатор инструмента
            - ticker (str): Тикер инструмента
            - mic (str): MIC идентификатор биржи
            - isin (str): ISIN идентификатор инструмента
            - type (str): Тип инструмента
            - name (str): Наименование инструмента
            - decimals (int): Количество десятичных знаков в цене
            - min_step (str): Минимальный шаг цены
            - lot_size (dict): Количество штук в лоте с value в строковом формате
            - expiration_date (dict): Дата экспирации фьючерса (опционально)
            - quote_currency (str): Валюта котировки (опционально)

    Использовать когда:
        - Нужно получить технические параметры инструмента
        - Требуется узнать размер лота и шаг цены
        - Необходимо проверить спецификацию инструмента перед торговлей

    Example:
        >>> get_asset("SBER@MISX", "1899011")
        {
            "board": "TQBR",
            "id": "3",
            "ticker": "SBER",
            "mic": "MISX",
            "isin": "RU0009029540",
            "type": "EQUITIES",
            "name": "Сбербанк",
            "lot_size": {"value": "10.0"},
            "decimals": 2,
            "min_step": "1"
        }
    """
    params = {}
    params["account_id"] = account_id
    return await execute_request("GET", f"/v1/assets/{symbol}", params=params)


@mcp.tool
async def get_asset_params(symbol: str, account_id: str = "{account_id}") -> dict[str, Any]:
    """
    Получить торговые параметры и ограничения по инструменту для конкретного счета.

    Возвращает информацию о доступности операций (лонг/шорт), маржинальных требованиях,
    ставках риска и других торговых ограничениях для указанного счета.

    Args:
        symbol (str): Символ инструмента в формате "<TICKER>@<MIC>"
        account_id (str): Идентификатор счёта.

    Returns:
        dict[str, Any]: JSON объект с торговыми параметрами инструмента:
            - symbol (str): Символ инструмента
            - account_id (str): ID аккаунта
            - tradeable (bool): Доступны ли торговые операции
            - longable (dict): Доступность операций в лонг:
                - value (str): Статус доступности (AVAILABLE, NOT_AVAILABLE)
                - halted_days (int): Дней запрета на операции (если есть)
            - shortable (dict): Доступность операций в шорт:
                - value (str): Статус доступности
                - halted_days (int): Дней запрета на операции
            - long_risk_rate (dict): Ставка риска для лонг операций
            - long_collateral (dict): Сумма обеспечения для лонг позиции
            - short_risk_rate (dict): Ставка риска для шорт операций
            - short_collateral (dict): Сумма обеспечения для шорт позиции
            - long_initial_margin (dict): Начальная маржа для лонг
            - short_initial_margin (dict): Начальная маржа для шорт

    Использовать когда:
        - Нужно проверить доступность лонг/шорт операций
        - Требуется узнать маржинальные требования
        - Необходимо рассчитать необходимый залог для позиции

    Example:
        >>> get_asset_params("SBER@MISX", "1899011")
        {
            "symbol": "SBER@MISX",
            "account_id": "1899011",
            "tradeable": true,
            "longable": {
                "value": "AVAILABLE",
                "halted_days": 0
            },
            "shortable": {
                "value": "NOT_AVAILABLE",
                "halted_days": 0
            },
            "long_risk_rate": {"value": "100.0"},
            "long_collateral": {
                "currency_code": "RUB",
                "units": "285",
                "nanos": 50000000
            },
            "short_risk_rate": {"value": "300.0"},
            "long_initial_margin": {
                "currency_code": "RUB",
                "units": "285",
                "nanos": 50000000
            }
        }
    """
    params = {}
    params["account_id"] = account_id
    return await execute_request("GET", f"/v1/assets/{symbol}/params", params=params)


@mcp.tool
async def get_options_chain(underlying_symbol: str) -> dict[str, Any]:
    """
    Получить цепочку опционов для базового актива.

    Возвращает список всех доступных опционных контрактов для указанного
    базового актива с их основными параметрами и датами экспирации.

    Args:
        underlying_symbol (str): Символ базового актива опциона в формате "<TICKER>@<MIC>"

    Returns:
        dict[str, Any]: JSON объект с цепочкой опционов:
            - symbol (str): Символ базового актива
            - options (list): Список опционных контрактов, каждый содержит:
                - symbol (str): Символ опционного контракта
                - type (str): Тип опциона (TYPE_CALL, TYPE_PUT)
                - contract_size (dict): Лот, количество базового актива
                - trade_first_day (dict): Дата старта торговли
                - trade_last_day (dict): Дата окончания торговли
                - strike (dict): Цена исполнения опциона
                - multiplier (dict): Множитель опциона (опционально)
                - expiration_first_day (dict): Дата начала экспирации
                - expiration_last_day (dict): Дата окончания экспирации

    Использовать когда:
        - Нужно получить список всех опционов по базовому активу
        - Требуется найти опционы с определенным страйком или датой экспирации
        - Необходимо анализировать опционные стратегии

    Example:
        >>> get_options_chain("YDEX@MISX")
        {
            "symbol": "YDEX@MISX",
            "options": [
                {
                    "symbol": "YD4300CU5A@RTSX",
                    "type": "TYPE_PUT",
                    "contract_size": {"value": "1.0"},
                    "trade_last_day": {"year": 2025, "month": 9, "day": 3},
                    "strike": {"value": "4300.0"},
                    "expiration_first_day": {"year": 2025, "month": 9, "day": 3},
                    "expiration_last_day": {"year": 2025, "month": 9, "day": 3}
                },
                {
                    "symbol": "YD4300CI5A@RTSX",
                    "type": "TYPE_CALL",
                    "contract_size": {"value": "1.0"},
                    "trade_last_day": {"year": 2025, "month": 9, "day": 3},
                    "strike": {"value": "4300.0"},
                    "expiration_first_day": {"year": 2025, "month": 9, "day": 3},
                    "expiration_last_day": {"year": 2025, "month": 9, "day": 3}
                }
            ]
        }
    """
    return await execute_request("GET", f"/v1/assets/{underlying_symbol}/options")


@mcp.tool
async def get_schedule(symbol: str) -> dict[str, Any]:
    """
    Получить расписание торгов для инструмента.

    Возвращает график торговых сессий инструмента, включая основные
    и дополнительные сессии, а также периоды закрытия торгов.

    Args:
        symbol (str): Символ инструмента в формате "<TICKER>@<MIC>"

    Returns:
        dict[str, Any]: JSON объект с расписанием торгов:
            - symbol (str): Символ инструмента
            - sessions (list): Список торговых сессий, каждая сессия содержит:
                - type (str): Тип сессии (CLOSED, EARLY_TRADING, CORE_TRADING, LATE_TRADING)
                - interval (dict): Интервал сессии:
                    - start_time (str): Время начала сессии
                    - end_time (str): Время окончания сессии

    Использовать когда:
        - Нужно узнать время работы торговой площадки по инструменту
        - Требуется определить доступные для торговли периоды
        - Необходимо планировать торговые операции по времени

    Example:
        >>> get_schedule("YDEX@MISX")
        {
            "symbol": "YDEX@MISX",
            "sessions": [
                {
                    "type": "CLOSED",
                    "interval": {
                        "start_time": "2025-07-23T21:00:00Z",
                        "end_time": "2025-07-24T03:50:00Z"
                    }
                },
                {
                    "type": "EARLY_TRADING",
                    "interval": {
                        "start_time": "2025-07-24T04:00:00Z",
                        "end_time": "2025-07-24T06:50:00Z"
                    }
                },
                {
                    "type": "CORE_TRADING",
                    "interval": {
                        "start_time": "2025-07-24T06:50:00Z",
                        "end_time": "2025-07-24T15:40:00Z"
                    }
                }
            ]
        }
    """
    return await execute_request("GET", f"/v1/assets/{symbol}/schedule")


@mcp.tool
async def get_last_quote(symbol: str) -> dict[str, Any]:
    """
    Получить последнюю котировку по инструменту.

    Возвращает актуальные рыночные данные по инструменту, включая лучшие цены
    спроса и предложения, цену последней сделки, дневную статистику и изменение цены.

    Args:
        symbol (str): Символ инструмента в формате "<TICKER>@<MIC>"

    Returns:
        dict[str, Any]: JSON объект с последней котировкой:
            - symbol (str): Символ инструмента
            - quote (dict): Данные котировки:
                - symbol (str): Символ инструмента
                - timestamp (str): Метка времени обновления котировки
                - ask (dict): Лучшая цена предложения (аск)
                - ask_size (dict): Объем по лучшей цене предложения
                - bid (dict): Лучшая цена спроса (бид)
                - bid_size (dict): Объем по лучшей цене спроса
                - last (dict): Цена последней сделки
                - last_size (dict): Объем последней сделки
                - volume (dict): Дневной объем сделок
                - turnover (dict): Дневной оборот в деньгах
                - open (dict): Цена открытия дня
                - high (dict): Максимальная цена дня
                - low (dict): Минимальная цена дня
                - close (dict): Цена закрытия предыдущего дня
                - change (dict): Изменение цены относительно закрытия
                - option (dict): Дополнительные данные для опционов (опционально)

    Использовать когда:
        - Нужно получить актуальные рыночные данные
        - Требуется узнать текущие лучшие цены и объемы
        - Необходимо отслеживать изменение цены в реальном времени

    Example:
        >>> get_last_quote("YDEX@MISX")
        {
            "symbol": "YDEX@MISX",
            "quote": {
                "symbol": "YDEX@MISX",
                "timestamp": "2025-07-24T08:40:46.838173Z",
                "ask": {"value": "4345.0"},
                "ask_size": {"value": "438"},
                "bid": {"value": "4344.5"},
                "bid_size": {"value": "37"},
                "last": {"value": "4344.5"},
                "last_size": {"value": "5"},
                "volume": {"value": "131667"},
                "turnover": {"value": "5.75349694E8"},
                "open": {"value": "0.0"},
                "high": {"value": "0.0"},
                "low": {"value": "0.0"},
                "close": {"value": "4372.5"},
                "change": {"value": "-28.0"}
            }
        }
    """
    return await execute_request("GET", f"/v1/instruments/{symbol}/quotes/latest")


@mcp.tool
async def get_latest_trades(symbol: str) -> dict[str, Any]:
    """
    Получить список последних сделок по инструменту.

    Возвращает историю недавних сделок по инструменту с информацией о цене,
    объеме, времени исполнения и участниках торгов.

    Args:
        symbol (str): Символ инструмента в формате "<TICKER>@<MIC>"

    Returns:
        dict[str, Any]: JSON объект со списком последних сделок:
            - symbol (str): Символ инструмента
            - trades (list): Список сделок, каждая сделка содержит:
                - trade_id (str): Уникальный идентификатор сделки от биржи
                - mpid (str): Идентификатор участника рынка (маркет-мейкера)
                - timestamp (str): Метка времени исполнения сделки
                - price (dict): Цена исполнения сделки
                - size (dict): Объем сделки
                - side (str): Сторона сделки (SIDE_BUY, SIDE_SELL)

    Использовать когда:
        - Нужно проанализировать недавнюю торговую активность
        - Требуется отследить исполнение крупных сделок
        - Необходимо определить текущий рыночный тренд

    Example:
        >>> get_latest_trades("YDEX@MISX")
        {
            "symbol": "YDEX@MISX",
            "trades": [
                {
                    "trade_id": "13766276190",
                    "mpid": "",
                    "timestamp": "2025-07-24T08:26:27.314736Z",
                    "price": {"value": "4350.0"},
                    "size": {"value": "5.0"},
                    "side": "SIDE_BUY"
                },
                {
                    "trade_id": "13766276352",
                    "mpid": "",
                    "timestamp": "2025-07-24T08:26:28.674580Z",
                    "price": {"value": "4350.0"},
                    "size": {"value": "7.0"},
                    "side": "SIDE_BUY"
                }
            ]
        }
    """
    return await execute_request("GET", f"/v1/instruments/{symbol}/trades/latest")


@mcp.tool
async def get_transactions(account_id: str, start: str | None = None, end: str | None = None) -> dict[str, Any]:
    """
    Получить историю транзакций по счету за указанный период.

    Возвращает список всех финансовых операций по счету, включая торговые сделки,
    комиссии, пополнения, выводы средств и другие денежные движения.

    Args:
        account_id (str): Идентификатор счёта.
        start (str | None): Начало периода в формате ISO 8601 (опционально)
        end (str | None): Конец периода в формате ISO 8601 (опционально)

    Returns:
        dict[str, Any]: JSON объект со списком транзакций:
            - transactions (list): Список транзакций, каждая транзакция содержит:
                - id (str): Уникальный идентификатор транзакции
                - category (str): Категория транзакции
                - timestamp (str): Метка времени транзакции
                - symbol (str): Символ инструмента (если применимо)
                - change (dict): Изменение денежных средств:
                    - currency_code (str): Код валюты
                    - units (str): Целая часть суммы
                    - nanos (int): Дробная часть суммы в наноединицах
                - transaction_category (str): Категория транзакции из TransactionCategory
                - transaction_name (str): Наименование транзакции
                - trade (dict): Информация о сделке (опционально)

    Использовать когда:
        - Нужно получить полную историю денежных движений по счету
        - Требуется проанализировать комиссии и расходы
        - Необходимо построить отчет о финансовой активности

    Example:
        >>> get_transactions("1899011", "2025-07-01T00:00:00Z", "2025-07-31T23:59:59Z")
        {
            "transactions": [
                {
                    "id": "2556733362",
                    "category": "COMMISSION",
                    "timestamp": "2025-07-25T20:59:59Z",
                    "symbol": "",
                    "change": {
                        "currency_code": "RUB",
                        "units": "-1",
                        "nanos": -6400000
                    },
                    "transaction_category": "COMMISSION",
                    "transaction_name": "Брокерская комиссия"
                },
                {
                    "id": "2259286250",
                    "category": "DEPOSIT",
                    "timestamp": "2025-02-28T11:09:08Z",
                    "symbol": "",
                    "change": {
                        "currency_code": "RUB",
                        "units": "999",
                        "nanos": 0
                    },
                    "transaction_category": "DEPOSIT",
                    "transaction_name": "Ввод денежных средств"
                }
            ]
        }
    """
    params = {}
    if start:
        params["interval.start_time"] = start
    if end:
        params["interval.end_time"] = end
    return await execute_request("GET", f"/v1/accounts/{account_id}/transactions", params=params)

@mcp.tool
async def get_history_plots(time_data: list | None, points: list, label: str) -> str:
    """
    Нарисовать график исторических данных

    По переданным дате и значениям отрисовывает график исторических значений

    Args:
        time_data (list | None): массив дат в формате ISO 8601 (опционально)
        points (list): массив точек временного ряда
        label (str): название показателя

    Returns:
        str: статус отрисовки графика
    """
    try:
        t = np.array([dateutil.parser.parse(t) for t in time_data])
        p = np.array(points)
        
        fig, ax = plt.subplots()
        ax.plot(t, p, label=label)
        ax.set_xticklabels(t, rotation=30)
        ax.legend()
        fig.savefig(f"img/fig{random.randint(0, 1000)}.png", bbox_inches="tight")
        plt.close(fig)

        return 'график успешно нарисован и будет передан клиенту'
    except:
        return 'график не может быть нарисован'

@mcp.tool
async def get_comparision_histograms(points: list, labels: list) -> str:
    """
    Нарисовать график гистограммы сравнения величин

    Args:
        points (list): массив точек
        label (str): массив названий показателей

    Returns:
        str: статус отрисовки графика
    """

    try:
        p = np.array(points)
        l = np.array(labels)
        
        fig, ax = plt.subplots()
        ax.bar(l, p)
        ax.set_xticklabels(l, rotation=30)
        fname = f"img/fig{random.randint(0, 1000)}.png"
        fig.savefig(fname, bbox_inches="tight")
        plt.close(fig)

        return 'график успешно нарисован и будет передан клиенту'
    except:
        return 'график не может быть нарисован'

@mcp.tool
async def get_simple_pie_plot(labels: list, values: list, title: str = "Круговая диаграмма") -> str:
    """
    Нарисовать круговую диаграмму (pie chart)

    По переданным наименованиям и значениям отрисовывает круговую диаграмму

    Args:
        labels (list): массив наименований категорий
        values (list): массив значений для каждой категории
        title (str, optional): заголовок диаграммы. По умолчанию "Круговая диаграмма"

    Returns:
        str: статус отрисовки диаграммы
    """
    try:
        if len(labels) != len(values):
            return 'Ошибка: количество наименований и значений не совпадает'
        
        fig, ax = plt.subplots()
        
        ax.pie(
            values, 
            labels=labels, 
            autopct='%1.1f%%',
            startangle=90,
            colors=plt.cm.Pastel1(np.linspace(0, 1, len(labels)))
        )
        
        fig.title(title, fontsize=12, fontweight='bold')
        fname = f"img/fig{random.randint(0, 1000)}.png"
        fig.savefig(fname, bbox_inches='tight')
        plt.close(fig)

        return 'График успешно нарисован и будет передан клиенту'
    
    except Exception as e:
        return f'Ошибка при создании диаграммы: {str(e)}'

# === РЕСУРСЫ ===
@mcp.resource("ref://moex/tickers/{company}")
def get_company_ticker(company:str) -> str:
    """Возвращает тикер Московской биржи для компании

    Args:
        company (str): Наименование компании

    Returns:
        str: тикер Московской биржи по данной компании
    """
    company = company.lower().replace(" ", "")
    moex_mapping = {
        "мечел": "MTLR@MISX",
        "фосагро": "PHOR@MISX",
        "норникель": "GMKN@MISX",
        "русгидро": "HYDR@MISX",
        "сбербанк": "SBER@MISX",
        "яндекс": "YNDX@MISX",
        "ростелеком": "RTKM@MISX",
        "роснефть": "ROSN@MISX",
        "полюсзолото": "PLZL@MISX",
        "мосбиржа": "MOEX@MISX",
        "аэрофлот": "AFLT@MISX"
    }
    return moex_mapping.get(company, f"Тикер для {company} не найден")

if __name__ == "__main__":
    mcp.run(transport="streamable-http")