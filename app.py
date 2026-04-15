import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner  

st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 상태 변수 초기화 (기존 로직 유지)
if 'stop_flag' not in st.session_state: st.session_state.stop_flag = False
if 'is_collecting' not in st.session_state: st.session_state.is_collecting = False
if 'combiner_authenticated' not in st.session_state: st.session_state.combiner_authenticated = False

# [핵심] 메뉴 이동을 위한 콜백 함수 (사용자님 코드 유지)
def reset_tool(): st.session_state.tool_menu = None
def reset_main(): st.session_state.main_menu = None

with st.sidebar:
    st.title("🚀 QA1 업무 대시보드")
    st.markdown("---")
    
    # 1. 상단 메뉴 (기존과 동일)
    menu_main = st.radio("메뉴 선택", [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장"
    ], index=1, key="main_menu", on_change=reset_tool)
    
    # 2. 기존 실선과 100% 똑같은 진짜 실선
    st.markdown("---")
    
    # 3. 하단 메뉴 (인증 전후로 구성)
    if not st.session_state.combiner_authenticated:
        # 인증 전에는 비밀번호 입력창이 실선 사이에 위치
        st.write("🔐 도구 액세스")
        pw_input = st.text_input("PW", type="password", label_visibility="collapsed", key="pw_sidebar")
        if st.button("인증하기", use_container_width=True):
            if pw_input == st.secrets["COMBINER_PW"]:
                st.session_state.combiner_authenticated = True
                st.rerun()
            else:
                st.error("비밀번호 불일치")
    else:
        # 인증 후에는 사용자님 코드의 라디오 버튼이 그대로 노출
        menu_tool = st.radio("도구", ["단어 조합 생성기"], 
                             index=None, key="tool_menu", on_change=reset_main, label_visibility="collapsed")
        if st.button("잠금", use_container_width=True):
            st.session_state.combiner_authenticated = False
            st.rerun()
    
    st.markdown("---")
    
    # [원본 유지] 중단 버튼 로직 (사용자님 코드와 100% 일치)
    if menu_main == "클로드 분석용 언론 수집":
        if st.button("⛔ 분석 중단", use_container_width=True, type="primary"):
            st.session_state.stop_flag = True
            st.session_state.is_collecting = False
            st.rerun()
        st.markdown("---")

    st.caption("v2.1 Hybrid Engine (AI + Local)")

# --- 실행 로직 (사용자님 코드 기반) ---
current_tool = st.session_state.get("tool_menu")

if current_tool == "단어 조합 생성기":
    run_combiner()
elif menu_main == "실시간 이슈 모니터링":
    run_monitor()
elif menu_main == "리스크 키워드 확장":
    run_keyword()
elif menu_main == "클로드 분석용 언론 수집":
    run_claude_collector()
