from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
import pandas as pd
import asyncio
from langchain.memory import ConversationBufferWindowMemory
import os
from dotenv import load_dotenv
import warnings
import re

warnings.filterwarnings('ignore')

class ChatBot:
    def __init__(self):
        load_dotenv()

        client = MultiServerMCPClient({'trade': {'url': 'http://127.0.0.1:8000/mcp',
                                                "transport": "streamable_http"}})

        tools = asyncio.run(client.get_tools())

        #model = ChatOllama(model='qwen3:4b', temperature=0) для локальной модели
        model = ChatOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            model="x-ai/grok-4-fast"
        )

        self.memory = ConversationBufferWindowMemory(
            k=10,
            return_messages=True
        )

        self.llm = create_react_agent(
                model = model,
                tools = tools
        )

        system_prompt = ("""
        Роль и назначение
        Вы — профессиональный финансовый ассистент для биржевой торговли через Finam Trade API. Ваша задача — помогать клиентам получать рыночные данные, управлять портфелем и выполнять торговые операции, используя полный набор инструментов MCP сервера.

        Ключевые принципы работы
        1. Активное использование инструментов

        Всегда используй соответствующие инструменты MCP для ответов на запросы

        Не предполагай информацию — запрашивай актуальные данные через API

        Для поиска тикеров используй ресурс get_company_ticker или get_assets

        2. Безопасность и проверка

        При критических действий (особенно выставление заявок), обязательно спрашивай подтверждение пользователя, чтобы защитить его от случайных сделок

        При работе с заявками всегда уточняй account_id если он не указан

        Перед созданием ордера проверяй торговые параметры инструмента через get_asset_params

        При отмене ордеров подтверждай идентификаторы заявок

        3. Контекст и полнота ответов

        Предоставляй не только сырые данные, но и их интерпретацию

        Связывай информацию из разных источников (стакан + свечи + позиции)

        Предлагай смежные данные, которые могут быть полезны пользователю

        Типовые сценарии и инструменты
        Для рыночных данных:

        get_orderbook() — стакан котировок

        get_candles() — исторические данные

        get_last_quote() — последние котировки

        get_latest_trades() — лента сделок

        Для информации об инструментах:

        get_assets() — поиск инструментов

        get_asset() — детали инструмента

        get_asset_params() — торговые параметры

        get_schedule() — расписание торгов

        Для управления портфелем:

        get_account() / get_positions() — позиции и баланс

        get_orders() — активные заявки

        get_trades() — история сделок

        get_transactions() — денежные движения

        Для торговых операций:

        create_order() — выставление заявок

        cancel_order() — отмена заявок

        get_order() — статус конкретной заявки

        Формат ответов
        Для данных:

        text
        [Инструмент] - [Тип данных]
        • Ключевая метрика 1: значение
        • Ключевая метрика 2: значение
        Дополнительные инсайты...
        Для торговых операций:

        text
        [Операция выполнена]
        • Order ID: [идентификатор]
        • Статус: [статус]
        • Детали: [краткое описание]
        При ошибках:

        text
        [Проблема]
        • Причина: [объяснение]
        • Рекомендация: [что делать]
        Примеры обработки запросов
        Запрос: "Какая текущая ситуация с Сбербанком?"
        Действия:

        get_company_ticker("сбербанк") → SBER@MISX

        get_last_quote("SBER@MISX") → текущие цены

        get_orderbook("SBER@MISX") → стакан

        Объединенный анализ

        Запрос: "Покажи мои позиции на счете 12345"
        Действия:

        get_positions("12345") → все позиции

        Анализ рисков и доходности

        Сводка по портфелю

        Запрос: "Купи 100 акций Лукойла по 7000"
        Действия:

        get_company_ticker("лукойл") → LKOH@MISX

        get_asset_params("LKOH@MISX", "12345") → проверка доступности

        create_order() → выставление заявки

        Подтверждение исполнения

        Важные замечания
        Всегда уточняй недостающие параметры (account_id, даты, тикеры)

        Предупреждай о рисках при торговых операциях

        Для сложных запросов разбивай на несколько API вызовов

        Отвечай на русском языке
        """)
        self.memory.chat_memory.add_message(SystemMessage(content=system_prompt))

        self.prompt = ChatPromptTemplate(
            [MessagesPlaceholder("history"),
            MessagesPlaceholder("msgs")]
        )

    async def send_message(self, text):
            self.memory.chat_memory.add_user_message(text)

            msg = await self.llm.ainvoke(self.prompt.invoke({"msgs": [HumanMessage(content=text)],
                                                "history": self.memory.chat_memory.messages,
                                                "account_id": "account_id"}))
        
            assistant_reply = msg["messages"][-1].content
            self.memory.chat_memory.add_ai_message(assistant_reply)

            print(msg['messages'])
            return re.sub(r"<think>.*?</think>", "", assistant_reply, flags=re.DOTALL)

async def get_submission():
    load_dotenv()

    df = pd.read_csv('.data/train.csv', delimiter=';')
    df_test = pd.read_csv('.data/test.csv', delimiter=';')
    ans = {}

    client = MultiServerMCPClient({'trade': {'url': 'http://127.0.0.1:8000/mcp',
                                                "transport": "streamable_http"}})

    tools = await client.get_tools()
    #model = ChatOllama(model='qwen3:4b', temperature=0) для использования локальной модели
    model = ChatOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-4.1-mini"
    )

    llm = create_react_agent(
            model = model,
            tools = tools
    )
    examples = '\n'.join(['Вопрос:' + row.question + '- Функция: ' + row.request.replace('{', '{{').replace('}', '}}') for index, row in df.iterrows()])
              
    prompt = ChatPromptTemplate(
        [('system', """
            Роль
            Ты - профессиональный финансовый ассистент для работы с Finam Trade API. Твоя задача - помогать пользователям с биржевой торговлей, анализом рынка и управлением портфелем.
            Можешь пользоваться всеми доступными инструментами Finam Trade API. В ответ на вопрос пользователя тебе необходимо всего лишь отправить ему необходимый метод (GET, PUT, DELETE и др.) и эндпоинт для вызова API.

            Примеры запросов и ответов""" + examples + 
            """Формат ответа
            Отвечай на русском языке. Твой ответ должен быть ТОЛЬКО строкой с методом(GET, PUT, DELETE и др.) и эндепоинтом в точном формате как в примерах выше. Не добавляй пояснений, не описывай процесс - просто верни готовый API путь.
            """),
        MessagesPlaceholder("msgs")]
    )

    tokens_input = 0
    tokens_output = 0
    pricing_input = 0.4 / (10 ** 6)
    pricing_output = 1.6 / (10 ** 6)

    for index, row in df_test.iterrows():
        text = row.question
        msg = await llm.ainvoke(prompt.invoke({"msgs": [HumanMessage(content=text)]}))

        msg = msg['messages'][-1]
        tokens_input += msg.usage_metadata['input_tokens']
        tokens_output += msg.usage_metadata['output_tokens']
        answer = msg.content


        answer_parts = answer.split(' ')
        method = None
        url = None
        for part in answer_parts:
            for m in ['GET', 'PUT', 'POST', 'DELETE']:
                if part.startswith(m):
                    if method is None:
                        method = m
                    part = part[len(m):]
                    break
                    
            if part.startswith('/'):
                if url is None:
                    url = part
        
        if method is None:
            method = 'GET'
        if url is None:
            url = "/v1/assets"


        ans[row.uid] = [method, url]
    
    subm = pd.DataFrame(ans).T
    subm.reset_index(inplace = True)
    subm.columns = ['uid', 'type', 'request']
    subm.to_csv('.data/subm.csv', index=False, sep = ';')
    
    avg_price = ((tokens_input * pricing_input) + (tokens_output * pricing_output)) / len(df_test)
    print(f'{avg_price} $ в среднем на запрос')
    return avg_price




if __name__ == '__main__':

    asyncio.run(get_submission())