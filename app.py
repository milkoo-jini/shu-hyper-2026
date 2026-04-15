import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner  

st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 상태 변수 초기화 (기본 로직 유지)
if 'stop_flag' not in st.session_state: st.session_state.stop_flag = False
if 'is_collecting' not in st.session_state: st.session_state.is_collecting = False
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False

# 메뉴 이동을 위한 콜백 함수 (사용자님 코드 유지)
def reset_tool(): st.session_state.tool_menu = None
def reset_main(): st.session_state.main_menu = None

with st.sidebar:
    st.title("🚀 QA1 업무 대시보드")
    st.markdown("---")
    
    # 1. 상단 메뉴 (항상 모든 메뉴 노출)
    menu_main = st.radio("메뉴 선택", [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장"
    ], index=1, key="main_menu", on_change=reset_tool)
    
    st.markdown("---")
    
    # 2. 하단 관리자 모드 구역 (사이드바 배치)
    if not st.session_state.admin_mode:
        st.write("🔐 관리자 모드")
        pw_input = st.text_input("PW", type="password", label_visibility="collapsed", key="pw_sidebar")
        if st.button("인증", use_container_width=True):
            if pw_input == st.secrets["COMBINER_PW"]:
                st.session_state.admin_mode = True
                st.rerun()
            else:
                st.error("불일치")
    else:
        # 인증 성공 시 관리자 메뉴(단어 조합기) 노출
        st.write("🔓 관리자 모드 활성")
        menu_tool = st.radio("도구", ["단어 조합 생성기"], 
                             index=None, key="tool_menu", on_change=reset_main, label_visibility="collapsed")
        if st.button("관리자 로그아웃", use_container_width=True):
            st.session_state.admin_mode = False
            st.rerun()
    
    st.markdown("---")
    
    # [원본 유지] 중단 버튼 로직
    if menu_main == "클로드 분석용 언론 수집":
        if st.button("⛔ 분석 중단", use_container_width=True, type="primary"):
            st.session_state.stop_flag = True
            st.session_state.is_collecting = False
            st.rerun()
        st.markdown("---")

    st.caption("v2.1 Hybrid Engine (AI + Local)")

# --- 실행 로직 (사용자님 원본 구조 유지 및 보안 적용) ---
current_tool = st.session_state.get("tool_menu")

if current_tool == "단어 조합 생성기":
    if st.session_state.admin_mode:
        run_combiner()
    else:
        st.warning("🔐 해당 기능은 관리자 모드 인증 후 이용 가능합니다.")

elif menu_main == "리스크 키워드 확장":
    if st.session_state.admin_mode:
        run_keyword()
    else:
        st.warning("🔐 해당 기능은 관리자 모드 인증 후 이용 가능합니다.")

elif menu_main == "실시간 이슈 모니터링":
    run_monitor()

elif menu_main == "클로드 분석용 언론 수집":
    run_claude_collector()
