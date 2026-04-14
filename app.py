import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  # 새 파일 연결

st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# [추가] 분석 중단을 위한 상태 제어 변수
if 'stop_flag' not in st.session_state: st.session_state.stop_flag = False
if 'is_collecting' not in st.session_state: st.session_state.is_collecting = False

with st.sidebar:
    st.title("🚀 업무 제어 센터")
    # 메뉴에 클로드 분석용 수집 추가
    menu = st.radio("메뉴 선택", [
        "🔍 실시간 이슈 모니터링", 
        "🛠️ 리스크 키워드 확장",
        "🤖 클로드 분석용 수집"
    ])
    st.markdown("---")
    
    # [추가] 분석 중단 버튼 - 사이드바 하단에 상시 노출
    if menu == "🤖 클로드 분석용 수집":
        if st.button("⛔ 분석 중단", use_container_width=True):
            st.session_state.stop_flag = True
            st.session_state.is_collecting = False
            st.rerun()
        st.markdown("---")
        
    st.caption("v2.1 Hybrid Engine (AI + Local)")

if menu == "🔍 실시간 이슈 모니터링":
    run_monitor()
elif menu == "🛠️ 리스크 키워드 확장":
    run_keyword()
else:
    run_claude_collector()  # 세 번째 메뉴 실행
