import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner  

st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 상태 변수 초기화
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False

# [원본 로직] 엔터키 입력 시 즉시 인증
def check_admin_pw():
    if st.session_state.admin_pw_entry == st.secrets["COMBINER_PW"]:
        st.session_state.admin_mode = True
    else:
        st.error("비밀번호 불일치")

# 메뉴 이동 콜백
def reset_tool(): st.session_state.tool_menu = None
def reset_main(): st.session_state.main_menu = None

with st.sidebar:
    st.title("🚀 QA1 업무 대시보드")
    st.markdown("---")
    
    # 1. 메인 메뉴
    menu_main = st.radio("메뉴 선택", [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장"
    ], index=1, key="main_menu", on_change=reset_tool)
    
    st.markdown("---")
    
    # 2. 도구 메뉴
    menu_tool = st.radio("도구", ["단어 조합 생성기"], 
                         index=None, key="tool_menu", on_change=reset_main, label_visibility="collapsed")
    
    st.markdown("---")

    # [핵심] 현재 선택된 메뉴가 보안 메뉴인지 체크
    # 상단 라디오에서 '리스크 키워드 확장'을 골랐거나, 하단 '도구'에서 '단어 조합 생성기'를 골랐을 때만 True
    is_secure_selected = (menu_main == "리스크 키워드 확장") or (st.session_state.get("tool_menu") == "단어 조합 생성기")

    # 3. [디자인 & 조건부 노출 복구] 보안 메뉴일 때만 인증창 등장
    if is_secure_selected:
        with st.sidebar.expander("🔐 관리자 모드"):
            if not st.session_state.admin_mode:
                st.text_input("PW", type="password", placeholder="비밀번호 입력 후 Enter", 
                             key="admin_pw_entry", on_change=check_admin_pw, label_visibility="collapsed")
                if st.button("인증", use_container_width=True):
                    check_admin_pw()
            else:
                st.success("인증 완료")
                if st.button("잠금", use_container_width=True):
                    st.session_state.admin_mode = False
                    st.rerun()
        st.markdown("---")
    
    # 중단 버튼 및 캡션
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
        st.info("👈 관리자 인증이 필요한 메뉴입니다.")
elif menu_main == "리스크 키워드 확장":
    if st.session_state.admin_mode:
        run_keyword()
    else:
        st.info("👈 관리자 인증이 필요한 메뉴입니다.")
elif menu_main == "실시간 이슈 모니터링":
    run_monitor()
elif menu_main == "클로드 분석용 언론 수집":
    run_claude_collector()
