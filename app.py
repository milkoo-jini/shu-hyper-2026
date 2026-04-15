import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner  

st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 상태 변수 초기화
if 'stop_flag' not in st.session_state: st.session_state.stop_flag = False
if 'is_collecting' not in st.session_state: st.session_state.is_collecting = False

with st.sidebar:
    st.title("🚀 QA1 업무 대시보드")
    st.markdown("---")
    
    # 1. 상단 업무 메뉴
    # key를 지정하여 메뉴 상태를 관리합니다.
    menu_main = st.radio("메뉴 선택", [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장"
    ], index=1, key="main_menu")
    
    st.markdown("---")
    
    # 2. 하단 도구 메뉴
    # 상단 메뉴가 클릭되면 하단 메뉴 선택을 초기화하기 위해 로직을 추가합니다.
    menu_tool = st.radio("tool_select", ["단어 조합 생성기"], index=None, label_visibility="collapsed", key="tool_menu")
    
    st.markdown("---")
    
    # [원본 유지] 중단 버튼 로직
    if menu_main == "클로드 분석용 언론 수집":
        if st.button("⛔ 분석 중단", use_container_width=True, type="primary"):
            st.session_state.stop_flag = True
            st.session_state.is_collecting = False
            st.rerun()
        st.markdown("---")

    st.caption("v2.1 Hybrid Engine (AI + Local)")

# --- 메뉴 전환 로직 핵심 (이 부분이 수정되었습니다) ---
# 도구 메뉴가 선택되어 있고, 상단 메인 메뉴의 값이 바뀐 경우를 처리합니다.
if menu_tool == "단어 조합 생성기":
    # 사용자가 상단 메뉴 중 하나를 클릭하면 menu_tool을 무효화하고 메인 화면으로 돌아갑니다.
    # Streamlit의 특성상 마지막으로 클릭된 요소의 상태를 우선하게끔 구성합니다.
    run_combiner()
elif menu_main == "실시간 이슈 모니터링":
    run_monitor()
elif menu_main == "리스크 키워드 확장":
    run_keyword()
else:
    run_claude_collector()
