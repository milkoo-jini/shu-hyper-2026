import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword

st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

with st.sidebar:
    st.title("🚀 업무 제어 센터")
    menu = st.radio("메뉴 선택", ["🔍 실시간 이슈 모니터링", "🛠️ 리스크 키워드 확장"])
    st.markdown("---")
    st.caption("v2.0 Hybrid Engine (AI + Local)")

if menu == "🔍 실시간 이슈 모니터링":
    run_monitor()
else:
    run_keyword()
