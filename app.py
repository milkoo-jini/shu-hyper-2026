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

# [핵심] 메뉴 이동을 위한 콜백 함수 (사용자님 코드 그대로 유지)
def reset_tool(): st.session_state.tool_menu = None
def reset_main(): st.session_state.main_menu = None

with st.sidebar:
    st.title("🚀 QA1 업무 대시보드")
    st.markdown("---")
    
    # 1. 상단 메뉴 (모든 메뉴가 예전처럼 항상 보입니다)
    menu_main = st.radio("메뉴 선택", [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장"
    ], index=1, key="main_menu", on_change=reset_tool)
    
    st.markdown("---")
    
    # 2. 하단 도구 메뉴 (예전처럼 제목 없이 항상 노출됩니다)
    menu_tool = st.radio("도구", ["단어 조합 생성기"], 
                         index=None, key="tool_menu", on_change=reset_main, label_visibility="collapsed")
    
    st.markdown("---")
    
    # [원본 유지] 중단 버튼 로직 (기존 코드와 100% 일치)
    if menu_main == "클로드 분석용 언론 수집":
        if st.button("⛔ 분석 중단", use_container_width=True, type="primary"):
            st.session_state.stop_flag = True
            st.session_state.is_collecting = False
            st.rerun()
        st.markdown("---")

    st.caption("v2.1 Hybrid Engine (AI + Local)")

# --- 보안 인증 함수 (본문에서 사용) ---
def check_password():
    if not st.session_state.combiner_authenticated:
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            st.subheader("🔐 보안 메뉴 액세스")
            pw_input = st.text_input("비밀번호를 입력하세요", type="password")
            if st.button("인증하기", use_container_width=True):
                if pw_input == st.secrets["COMBINER_PW"]:
                    st.session_state.combiner_authenticated = True
                    st.rerun()
                else:
                    st.error("비밀번호가 틀렸습니다.")
        return False
    return True

# --- 실행 로직 (사용자님 원본 구조 유지) ---
current_tool = st.session_state.get("tool_menu")

if current_tool == "단어 조합 생성기":
    if check_password(): # 비번 통과해야 실행
        run_combiner()
elif menu_main == "리스크 키워드 확장":
    if check_password(): # 비번 통과해야 실행
        run_keyword()
elif menu_main == "실시간 이슈 모니터링":
    run_monitor() # 즉시 실행
elif menu_main == "클로드 분석용 언론 수집":
    run_claude_collector() # 즉시 실행
