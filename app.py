import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner  

# 페이지 설정
st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 관리자 인증 로직
def check_admin_pw():
    if st.session_state.admin_pw_entry == st.secrets["COMBINER_PW"]:
        st.session_state.admin_mode = True
        st.session_state.admin_pw_entry = "" # 입력 후 칸 비우기
    else:
        st.error("비밀번호 불일치")

# 상태 변수 초기화
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False

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

    # [조건부 노출 체크]
    is_secure_selected = (menu_main == "리스크 키워드 확장") or (st.session_state.get("tool_menu") == "단어 조합 생성기")

    # 3. [원본 디자인 100% 복구] 관리자 모드 섹션
    if is_secure_selected:
        if not st.session_state.admin_mode:
            # 원본 방식: text_input의 label을 활용하여 이모지와 폰트 스타일을 일치시킴
            st.text_input("🔒 관리자 모드", type="password", placeholder="비밀번호 입력 후 Enter", 
                         key="admin_pw_entry", on_change=check_admin_pw)
            if st.button("인증", use_container_width=True):
                check_admin_pw()
        else:
            st.write("🔓 관리자 인증 완료")
            if st.button("잠금", use_container_width=True):
                st.session_state.admin_mode = False
                st.rerun()
        st.markdown("---")

    st.caption("v2.1 Hybrid Engine (AI + Local)")

# --- 본문 실행 로직 ---
current_tool = st.session_state.get("tool_menu")

if current_tool == "단어 조합 생성기":
    if st.session_state.admin_mode:
        run_combiner()
    else:
        st.info("👈 사이드바에서 관리자 인증을 진행해 주세요.")

elif menu_main == "리스크 키워드 확장":
    if st.session_state.admin_mode:
        run_keyword()
    else:
        st.info("👈 사이드바에서 관리자 인증을 진행해 주세요.")

elif menu_main == "실시간 이슈 모니터링":
    run_monitor()

elif menu_main == "클로드 분석용 언론 수집":
    run_claude_collector()
