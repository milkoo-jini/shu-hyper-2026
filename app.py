import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner  # [신규] 파일 임포트만 추가

st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 상태 변수 초기화 (기존 코드 그대로)
if 'stop_flag' not in st.session_state: st.session_state.stop_flag = False
if 'is_collecting' not in st.session_state: st.session_state.is_collecting = False

with st.sidebar:
    st.title("🚀 QA1 업무 대시보드")
    st.markdown("---")
    
    # 상단 메뉴
    menu_main = st.radio("메뉴 선택", [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장"
    ], index=1)
    
    # 기존과 동일한 회색 실선으로 업무/도구 구분
    st.markdown("---")
    
    # 하단 도구 메뉴 (제목 없이 깔끔하게 항목만 노출)
    menu_tool = st.radio("tool_select", ["단어 조합 생성기"], index=None, label_visibility="collapsed")
    
    st.markdown("---")
    
    # [원본 유지] 중단 버튼 로직 (기존 코드와 100% 동일)
    if menu_main == "클로드 분석용 언론 수집":
        if st.button("⛔ 분석 중단", use_container_width=True, type="primary"):
            st.session_state.stop_flag = True
            st.session_state.is_collecting = False
            st.rerun()
        st.markdown("---")

    st.caption("v2.1 Hybrid Engine (AI + Local)")

# --- 실행 로직 (기존 기능 연결 유지) ---
if menu_tool == "단어 조합 생성기":
    run_combiner()
elif menu_main == "실시간 이슈 모니터링":
    run_monitor()
elif menu_main == "리스크 키워드 확장":
    run_keyword()
else:
    run_claude_collector()
