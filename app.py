import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  

st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 상태 변수 초기화
if 'stop_flag' not in st.session_state: st.session_state.stop_flag = False
if 'is_collecting' not in st.session_state: st.session_state.is_collecting = False

with st.sidebar:
    st.title("🚀 QA1 업무 대시보드")
    menu = st.radio("메뉴 선택", [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장"
    ])
    st.markdown("---")
    
    # [수정] 중단 버튼이 실시간으로 신호를 보내도록 개선
    if menu == "클로드 분석용 언론 수집":
        if st.button("⛔ 분석 중단", use_container_width=True, type="primary"):
            st.session_state.stop_flag = True
            st.session_state.is_collecting = False
            st.rerun()
        st.markdown("---")

    st.caption("v2.1 Hybrid Engine (AI + Local)")

if menu == "실시간 이슈 모니터링":
    run_monitor()
elif menu == "리스크 키워드 확장":
    run_keyword()
else:
    run_claude_collector()
