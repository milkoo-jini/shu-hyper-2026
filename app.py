import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner
from page_scroll import run_domain_collector

# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 2. 공통 CSS (슈 님의 기존 디자인 100% 유지 + 선 보정 추가)
st.markdown("""
    <style>
        /* [기존 디자인 유지] */
        [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stToolbar"], header[data-testid="stHeader"] {
            display: none !important; height: 0 !important;
        }
        .main .block-container { padding-top: 2rem !important; max-width: 95% !important; }
        .status-badge {
            background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 6px;
            padding: 0.5rem; text-align: center; color: #212529; font-weight: bold;
            height: 2.8rem; line-height: 1.8rem;
        }
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; }
        [data-testid="stSidebar"] .stRadio label { font-size: 0.95rem !important; color: #212529 !important; }
        [data-testid="stSidebar"] .stButton button { border-radius: 6px !important; }
        hr { border-color: #dee2e6 !important; margin: 0.8rem 0 !important; }
        .stButton button { border-radius: 6px !important; font-weight: 500 !important; }
        .stTextInput input { border-radius: 6px !important; }
        .stDataFrame thead tr th { background-color: #f1f3f5 !important; color: #495057 !important; font-weight: 600 !important; }
        [data-testid="stSidebar"] h1 { color: #212529 !important; font-weight: 700 !important; }
        [data-testid="stSidebar"] .stRadio > div { gap: 0.3rem !important; }
        [data-testid="stSidebar"] .stRadio label { padding: 0.4rem 0.6rem !important; border-radius: 6px !important; transition: background 0.2s !important; }
        [data-testid="stSidebar"] .stRadio label:hover { background-color: #e9ecef !important; }
        [data-testid="stSidebar"] .stCaption { color: #868e96 !important; font-size: 0.75rem !important; text-align: center !important; }

        /* [선 보정 핵심] 텍스트가 뭐든 상관없이 4번째 항목을 '진짜 실선'으로 강제 변환 */
        div[data-testid="stSidebar"] .stRadio [role="radiogroup"] > div:nth-of-type(4) {
            border-top: 1px solid #dee2e6 !important;
            height: 0px !important;
            margin: 1.2rem 0 !important; /* 위아래 st.markdown("---")과 똑같은 간격 */
            padding: 0 !important;
            pointer-events: none !important;
            overflow: hidden !important;
        }
        /* 4번째 항목 내부의 라디오 버튼과 글자를 완전히 소멸시킴 */
        div[data-testid="stSidebar"] .stRadio [role="radiogroup"] > div:nth-of-type(4) * {
            display: none !important;
            visibility: hidden !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. 관리자 인증 로직 (원본 유지)
def check_admin_pw():
    current_selected = st.session_state.get("total_menu_radio")
    if current_selected == "리스크 키워드 확장":
        target_pw = st.secrets["ADMIN_PASSWORD"]
    else:
        target_pw = st.secrets["COMBINER_PW"]

    if st.session_state.admin_pw_entry == target_pw:
        st.session_state.admin_mode = True
        st.session_state.admin_pw_entry = ""
    else:
        st.error("비밀번호 불일치")

# 4. 상태 변수 초기화
if 'admin_mode' not in st.session_state: 
    st.session_state.admin_mode = False

# --- 사이드바 영역 ---
with st.sidebar:
    st.title("🚀 QA1 AI 업무 대시보드")
    st.markdown("---")
    
    st.markdown("### 📋 메뉴 선택")

    menu_list = [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장",
        "──────────────",
        "도메인 추출🚧",
        "단어 조합 생성기🚧"
    ]

    menu_main = st.sidebar.radio(
        "메뉴 선택",
        menu_list,
        index=1,
        key="total_menu_radio",
        label_visibility="collapsed"
    )
    
    st.markdown("---")

    is_secure_selected = menu_main in ["도메인 추출🚧", "리스크 키워드 확장", "단어 조합 생성기🚧"]

    if is_secure_selected:
        if not st.session_state.admin_mode:
            st.markdown("### 🔐 관리자 인증")
            st.text_input("접속 비밀번호", type="password", 
                         label_visibility="collapsed", placeholder="비밀번호 입력",
                         key="admin_pw_entry", on_change=check_admin_pw)
            if st.button("인증", use_container_width=True):
                check_admin_pw()
        else:
            st.markdown("### ✅ 인증 완료")
            if st.button("잠금", use_container_width=True):
                st.session_state.admin_mode = False
                st.rerun()
        st.markdown("---")

    st.caption("v2.1 Hybrid Engine (AI + Local)")

# --- 본문 실행 영역 (원본 유지) ---
if menu_main == "단어 조합 생성기🚧":
    if st.session_state.admin_mode: run_combiner()
    else: st.info("👈 사이드바에서 관리자 인증을 진행해 주세요.")
elif menu_main == "리스크 키워드 확장":
    if st.session_state.admin_mode: run_keyword()
    else: st.info("👈 사이드바에서 관리자 인증을 진행해 주세요.")
elif menu_main == "도메인 추출🚧":
    if st.session_state.admin_mode: run_domain_collector()
    else: st.info("👈 사이드바에서 관리자 인증을 진행해 주세요.")
elif menu_main == "실시간 이슈 모니터링":
    run_monitor()
elif menu_main == "클로드 분석용 언론 수집":
    run_claude_collector()
