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

load_dotenv()

class ChatBot:
    def __init__(self):
        df = pd.read_csv('.//train.csv', delimiter=';')

        client = MultiServerMCPClient({'trade': {'url': 'http://127.0.0.1:8000/mcp',
                                                "transport": "streamable_http"}})

        tools = asyncio.run(client.get_tools())

        model = ChatOllama(model='qwen3:4b', temperature=0)
        '''model = ChatOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            model="x-ai/grok-4-fast"
        )'''

        self.memory = ConversationBufferWindowMemory(
            k=10,
            return_messages=True
        )

        self.llm = create_react_agent(
                model = model,
                tools = tools
        )

        system_prompt = (f"ты финансовый ассистент, работающий с finam trade api. Для удобства использования функций тебе даны примеры запроса и функции которую пользователь хочет вызвать:" + '\n'.join([f'Вопрос: {row.question} - Функция: {row.request}' for index, row in df.iterrows()]) + 
            ' !!!обрати внимание, что если ты собираешься провести рисковую операцию, например купить или продать что-то, то тебе нужно запросить подтверждение пользователя ' +
            ' при вызове функций могут возникать ошибки (с неправильными параметрами, некоторые функции могут быть невозможны в определенных условиях), пытайся выдать пользователю информацию по ошибке' + 
            ' если будут трудности с поиском названий компании, пытайся найти их в примерах запросов. Отвечай и думай только на русском. account_id пользователя = TRQD05:989213')
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
    df = pd.read_csv('.//train.csv', delimiter=';')
    df_test = pd.read_csv('.//test.csv', delimiter=';')
    ans = {}

    client = MultiServerMCPClient({'trade': {'url': 'http://127.0.0.1:8000/mcp',
                                            "transport": "streamable_http"}})

    tools = await client.get_tools()
    #model = ChatOllama(model='qwen3:4b', temperature=0)
    model = ChatOpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model="x-ai/grok-4-fast"
    )

    '''llm = create_react_agent(
            model = model,
            tools = tools
    )'''
    examples = '\n'.join(['Вопрос:' + row.question + '- Функция: ' + row.request.replace('{', '{{').replace('}', '}}') for index, row in df.iterrows()])
              
    prompt = ChatPromptTemplate(
        [('system', f"ты финансовый ассистент, работающий с finam trade api. Для примера тебе даны примеры запроса и функции которую пользователь хочет вызвать:" + examples + 
          " по запросу пиши только метод запроса и ссылку для обращения к api как в примере, и не используй инструменты. Отвечай на русском. Если не уверен в названии компаниий или инструмента, старайся найти их в примерах. Если пользователь четко не ввел номер счета в ответ пиши {{account_id}}"),
        MessagesPlaceholder("msgs")]
    )

    tokens_input = 0
    tokens_output = 0
    pricing_input = 0.2 / (10 ** 6)
    pricing_output = 0.5 / (10 ** 6)

    for index, row in df_test.iterrows():
        text = row.question
        print(text)
        msg = await model.ainvoke(prompt.invoke({"msgs": [HumanMessage(content=text)]}))
        print(msg)

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
    subm.columns = ['uid', 'type', 'request']
    subm = subm.iloc[1:]
    subm.to_csv('./subm.csv', index=False, sep = ';')
    
    avg_price = ((tokens_input * pricing_input) + (tokens_output * pricing_output)) / len(df_test)
    print(f'{avg_price} $ в среднем на запрос')
    return avg_price




if __name__ == '__main__':

    #asyncio.run(get_chat())

    asyncio.run(get_submission())