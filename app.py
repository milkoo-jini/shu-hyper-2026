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
    
    # 1. 상단 메뉴 구성 (항시 노출 메뉴와 보안 메뉴 구분)
    main_options = ["클로드 분석용 언론 수집", "실시간 이슈 모니터링"]
    
    # 비밀번호 인증이 완료된 경우에만 '리스크 키워드 확장' 메뉴를 옵션에 추가
    if st.session_state.combiner_authenticated:
        main_options.append("리스크 키워드 확장")
    
    menu_main = st.radio("메뉴 선택", main_options, index=1, key="main_menu", on_change=reset_tool)
    
    st.markdown("---")
    
    # 2. 하단 도구 및 보안 구역
    if not st.session_state.combiner_authenticated:
        # 인증 전: 비밀번호 입력창 표시 (리스크 키워드 확장, 단어 조합 생성기용)
        st.write("🔐 보안 메뉴 액세스 (키워드/조합기)")
        pw_col, btn_col = st.columns([2, 1])
        with pw_col:
            pw_input = st.text_input("PW", type="password", label_visibility="collapsed", key="pw_sidebar")
        with btn_col:
            if st.button("확인"):
                if pw_input == st.secrets["COMBINER_PW"]:
                    st.session_state.combiner_authenticated = True
                    st.rerun()
                else:
                    st.error("❌")
    else:
        # 인증 후: 단어 조합 생성기 라디오 버튼 노출
        menu_tool = st.radio("도구", ["단어 조합 생성기"], 
                             index=None, key="tool_menu", on_change=reset_main, label_visibility="collapsed")
        if st.button("보안 메뉴 잠금", use_container_width=True):
            st.session_state.combiner_authenticated = False
            # 잠금 시 선택된 메뉴가 보안 메뉴라면 기본 메뉴로 튕겨내기 위해 처리
            st.session_state.main_menu = "실시간 이슈 모니터링"
            st.rerun()
    
    st.markdown("---")
    
    # [원본 유지] 중단 버튼 로직 (기존 코드 동일)
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
    run_combiner()
elif menu_main == "실시간 이슈 모니터링":
    run_monitor()
elif menu_main == "리스크 키워드 확장":
    run_keyword()
elif menu_main == "클로드 분석용 언론 수집":
    run_claude_collector()
