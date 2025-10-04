import streamlit as st
import asyncio
import time
from langchain_core.messages import HumanMessage, AIMessage
from llm_agent import ChatBot

st.set_page_config(page_title="Финансовый ассистент", page_icon="💹")

st.title("Финансовый ассистент Finam API")

if st.button("🗑️ Сбросить чат"):
    st.session_state.dialog = []
    st.session_state.waiting = False
    st.rerun()

bot = ChatBot()

if "dialog" not in st.session_state:
    st.session_state.dialog = []

if not st.session_state.dialog:
    st.info(
        "👋 Привет! Я ваш финансовый ассистент. Могу помочь работать с Finam API: "
        "проверять счета, находить акции, выполнять торговые операции (с подтверждением). "
        "Задайте вопрос!"
    )

for role, text in st.session_state.dialog:
    with st.chat_message(role):
        st.markdown(text)


user_input = st.chat_input("Введите ваш запрос")

if user_input:
    st.session_state.dialog.append(("user", user_input))
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()

        with st.spinner("Думаю..."):
            response = asyncio.run(bot.send_message(user_input))

    st.session_state.dialog.append(("assistant", response.strip()))
