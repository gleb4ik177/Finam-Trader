# Finam-Trader
## About
Цель проекта - создание AI-ассистента трейдера на базе Finam TradeAPI.<br>
Ассистент доступен по ссылке: https://finam-trader-bot.streamlit.app/
### Project architecture
<p align="center">
  <img width="700" height="450" src="https://sun9-56.userapi.com/s/v1/if2/uCxwHN9Db_Eivijb1-eM7vtFV79eREr8YXKjrFIdyJTO9IIojkjL2_sEhLIHRuxcOYjbuonCKIy8M2Zn-a4byMkD.jpg?quality=95&as=32x18,48x27,72x40,108x60,160x89,240x134,360x201,480x268,540x301,640x357,720x402,1080x603,1278x713&from=bu&cs=1278x0">
</p>

## How to run locally
1. Установить необходимые зависимости
```bash
  pip install -r requirements.txt
```
2. Получить необходимые ключи. Создать файл ~/.env со следующим содержимым:
```[default]
  FINAM_ACCESS_TOKEN = <finam-access-token>
  OPENROUTER_API_KEY = <openrouter-api-key>
```
3. Запустить mcp-сервер
```bash
  python mcp_trade
```
4. Запустить Streamlit приложение
```bash
  streamlit run chat_page.py
```

## Researches
