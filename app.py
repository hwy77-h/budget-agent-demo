"""Local Streamlit demonstration of the fictional spending Agent."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from agent import AgentError, DEMO_TODAY, answer
from ledger import Ledger

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

st.set_page_config(page_title="收支管理 Agent｜模拟作品", page_icon="💬", layout="centered")
st.title("个人收支管理 Agent")
st.caption("作品演示 · 全部为虚构人民币消费记录 · 模拟日期：2026-10-31")

try:
    ledger = Ledger.from_csv(ROOT / "data" / "sample_transactions.csv", ROOT / "data" / "sample_budgets.csv")
except (OSError, ValueError) as exc:
    st.error(f"模拟数据读取失败：{exc}")
    st.stop()

with st.sidebar:
    st.header("作品说明")
    st.write("可查询月份：" + "、".join(ledger.available_months))
    st.write("类别：餐饮、交通、购物、学习、娱乐、礼物")
    st.info("金额由本地 Python 工具计算；DeepSeek 负责理解问题、调用工具和组织回答。")
    if not os.getenv("DEEPSEEK_API_KEY"):
        st.warning("尚未配置 DEEPSEEK_API_KEY。请参考 README 在本机创建 .env 文件。")
    if st.button("清空对话"):
        st.session_state.messages = []
        st.rerun()

EXAMPLES = [
    "2026 年 10 月餐饮花了多少？",
    "10 月哪类支出最多？",
    "10 月餐饮预算还剩多少？",
    "9 月和 10 月的餐饮支出分别是多少？",
]
st.write("试试这些问题：")
cols = st.columns(2)
for index, question in enumerate(EXAMPLES):
    if cols[index % 2].button(question, key=f"example_{index}", use_container_width=True):
        st.session_state.pending_prompt = question

if "messages" not in st.session_state:
    st.session_state.messages = []
for item in st.session_state.messages:
    with st.chat_message(item["role"]):
        st.markdown(item["content"])
        if item["role"] == "assistant" and item.get("trace"):
            with st.expander("查看计算依据"):
                for step in item["trace"]:
                    st.write(step["tool"])
                    st.json(step["result"], expanded=False)

typed = st.chat_input("例如：10 月娱乐支出是否超出预算？")
prompt = st.session_state.pop("pending_prompt", None) or typed
if prompt:
    previous = list(st.session_state.messages)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("正在查询模拟账本…"):
            trace = []
            try:
                reply = answer(prompt, previous, ledger, api_key=os.getenv("DEEPSEEK_API_KEY"), trace=trace)
            except AgentError as exc:
                reply = str(exc)
        st.markdown(reply)
        if trace:
            with st.expander("查看计算依据"):
                for step in trace:
                    st.write(step["tool"])
                    st.json(step["result"], expanded=False)
    st.session_state.messages.append({"role": "assistant", "content": reply, "trace": trace})

st.divider()
st.caption(
    f"模拟日期 {DEMO_TODAY}。该作品仅演示账单查询与预算问答；"
    "不接入银行账户，也不处理真实个人账单。"
)
