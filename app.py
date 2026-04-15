import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner  

st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 상태 변수 초기화
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False

# [원본 로직] 엔터 키 입력 시 바로 인증 처리하기 위한 함수
def check_password():
    if st.session_state.admin_pw_input == st.secrets["COMBINER_PW"]:
        st.session_state.admin_mode = True
        st.session_state.admin_pw_input = "" # 입력칸 비우기
    else:
        st.error("비밀번호 불일치")

# 메뉴 이동 콜백
def reset_tool(): st.session_state.tool_menu = None
def reset_main(): st.session_state.main_menu = None

with st.sidebar:
    st.title("🚀 QA1 업무 대시보드")
    st.markdown("---")
    
    # 1. 상단 메뉴
    menu_main = st.radio("메뉴 선택", [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장"
    ], index=1, key="main_menu", on_change=reset_tool)
    
    st.markdown("---")
    
    # 2. 하단 도구 메뉴
    menu_tool = st.radio("도구", ["단어 조합 생성기"], 
                         index=None, key="tool_menu", on_change=reset_main, label_visibility="collapsed")
    
    st.markdown("---")

    # 3. [원본 복구] 관리자 인증 (엔터 입력 가능)
    with st.sidebar.expander("🔐 관리자 인증"):
        if not st.session_state.admin_mode:
            # on_change를 사용하여 엔터키 입력 시 즉시 check_password 실행
            st.text_input("Password", type="password", key="admin_pw_input", on_change=check_password)
            st.button("로그인", use_container_width=True, on_click=check_password)
        else:
            st.success("인증 완료")
            if st.button("로그아웃", use_container_width=True):
                st.session_state.admin_mode = False
                st.rerun()
    
    st.markdown("---")
    
    # 중단 버튼 및 캡션 (원본 유지)
    if menu_main == "클로드 분석용 언론 수집":
        if st.button("⛔ 분석 중단", use_container_width=True, type="primary"):
            st.session_state.stop_flag = True
            st.session_state.is_collecting = False
            st.rerun()
        st.markdown("---")

    st.caption("v2.1 Hybrid Engine (AI + Local)")

# --- 실행 로직 ---
current_tool = st.session_state.get("tool_menu")

if current_tool == "단어 조합 생성기":
    if st.session_state.admin_mode:
        run_combiner()
    else:
        st.warning("🔐 '단어 조합 생성기'는 관리자 인증이 필요합니다.")
elif menu_main == "리스크 키워드 확장":
    if st.session_state.admin_mode:
        run_keyword()
    else:
        st.warning("🔐 '리스크 키워드 확장'은 관리자 인증이 필요합니다.")
elif menu_main == "실시간 이슈 모니터링":
    run_monitor()
elif menu_main == "클로드 분석용 언론 수집":
    run_claude_collector()
