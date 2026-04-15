import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner  

# [필수] 페이지 설정 (반드시 맨 위에 위치)
st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# [핵심] 관리자 인증 함수 (에러 방지를 위해 실행 로직 앞에 정의)
def check_admin_pw():
    if st.session_state.admin_pw_entry == st.secrets["COMBINER_PW"]:
        st.session_state.admin_mode = True
        # 인증 성공 시 입력창 초기화는 사용자님 원래 로직에 따라 선택
    else:
        st.error("비밀번호 불일치")

# 상태 변수 초기화
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False

# 메뉴 이동 콜백
def reset_tool(): st.session_state.tool_menu = None
def reset_main(): st.session_state.main_menu = None

# --- 사이드바 시작 ---
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
    
    # 2. 도구 메뉴 (라벨 숨김)
    menu_tool = st.radio("도구", ["단어 조합 생성기"], 
                         index=None, key="tool_menu", on_change=reset_main, label_visibility="collapsed")
    
    st.markdown("---")

    # [조건부 노출 로직]
    is_secure_selected = (menu_main == "리스크 키워드 확장") or (st.session_state.get("tool_menu") == "단어 조합 생성기")

    # 3. [원본 디자인] 접힘 없이 이모지 그대로 노출
    if is_secure_selected:
        if not st.session_state.admin_mode:
            st.write("🔒 관리자 모드")
            # 엔터 연동을 위한 on_change 추가
            st.text_input("PW", type="password", placeholder="비밀번호 입력 후 Enter", 
                         key="admin_pw_entry", on_change=check_admin_pw, label_visibility="collapsed")
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
