import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner  

# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 2. 관리자 인증 로직 (엔터 입력 및 버튼 클릭 공용)
def check_admin_pw():
    # secrets에 설정된 비밀번호와 비교
    if st.session_state.admin_pw_entry == st.secrets["COMBINER_PW"]:
        st.session_state.admin_mode = True
        st.session_state.admin_pw_entry = "" # 입력 성공 시 칸 비우기
    else:
        st.error("비밀번호 불일치")

# 3. 상태 변수 초기화
if 'admin_mode' not in st.session_state: 
    st.session_state.admin_mode = False

# 메뉴 이동 시 상태 초기화 콜백
def reset_tool(): 
    st.session_state.tool_menu = None
def reset_main(): 
    st.session_state.main_menu = None

# --- 사이드바 영역 ---
with st.sidebar:
    st.title("🚀 QA1 AI 업무 대시보드")
    st.markdown("---")
    
    # 메인 메뉴 (라디오)
    menu_main = st.radio("메뉴 선택", [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장"
    ], index=1, key="main_menu", on_change=reset_tool)
    
    st.markdown("---")
    
    # 하단 도구 메뉴
    menu_tool = st.radio("도구", ["단어 조합 생성기"], 
                         index=None, key="tool_menu", on_change=reset_main, label_visibility="collapsed")
    
    st.markdown("---")

    # [조건부 노출 체크] 인증이 필요한 메뉴인지 확인
    is_secure_selected = (menu_main == "리스크 키워드 확장") or (st.session_state.get("tool_menu") == "단어 조합 생성기")

    # 4. [사용자 원본 디자인 완벽 복구]
    if is_secure_selected:
        if not st.session_state.admin_mode:
            # 사용자님이 주신 마크다운 제목과 입력창 설정 그대로 적용
            st.markdown("### 🔐 관리자 인증")
            st.text_input("접속 비밀번호", type="password", 
                         label_visibility="collapsed", placeholder="비밀번호 입력",
                         key="admin_pw_entry", on_change=check_admin_pw)
            
            if st.button("인증", use_container_width=True):
                check_admin_pw()
        else:
            # 인증 완료 시 디자인
            st.markdown("### ✅ 인증 완료")
            if st.button("잠금", use_container_width=True):
                st.session_state.admin_mode = False
                st.rerun()
        st.markdown("---")

    st.caption("v2.1 Hybrid Engine (AI + Local)")

# --- 본문 실행 영역 ---
current_tool = st.session_state.get("tool_menu")

# 1. 단어 조합 생성기 (보안)
if current_tool == "단어 조합 생성기":
    if st.session_state.admin_mode:
        run_combiner()
    else:
        st.info("👈 사이드바에서 관리자 인증을 진행해 주세요.")

# 2. 리스크 키워드 확장 (보안)
elif menu_main == "리스크 키워드 확장":
    if st.session_state.admin_mode:
        run_keyword()
    else:
        st.info("👈 사이드바에서 관리자 인증을 진행해 주세요.")

# 3. 실시간 이슈 모니터링
elif menu_main == "실시간 이슈 모니터링":
    run_monitor()

# 4. 클로드 분석용 언론 수집
elif menu_main == "클로드 분석용 언론 수집":
    run_claude_collector()
