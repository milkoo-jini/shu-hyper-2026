import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner  
# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 2. 공통 CSS — 라이트모드 기준, 전체 페이지 통일
st.markdown("""
    <style>
        /* 헤더·데코·툴바 숨기기 */
        [data-testid="stHeader"],
        [data-testid="stDecoration"],
        [data-testid="stToolbar"],
        header[data-testid="stHeader"] {
            display: none !important;
            height: 0 !important;
        }

        /* 본문 여백 */
        .main .block-container {
            padding-top: 2rem !important;
            margin-top: 0 !important;
            max-width: 95% !important;
        }

        /* 공통 배지 */
        .status-badge {
            background-color: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 0.5rem;
            text-align: center;
            color: #1e3a8a;
            font-weight: bold;
            height: 2.8rem;
            line-height: 1.8rem;
        }

        /* 사이드바 스타일 */
        [data-testid="stSidebar"] {
            background-color: #f8f9fa !important;
        }
        [data-testid="stSidebar"] .stRadio label {
            font-size: 0.95rem !important;
            color: #212529 !important;
        }
        [data-testid="stSidebar"] .stButton button {
            border-radius: 6px !important;
        }

        /* 구분선 */
        hr {
            border-color: #dee2e6 !important;
            margin: 0.8rem 0 !important;
        }

        /* 버튼 통일 */
        .stButton button {
            border-radius: 6px !important;
            font-weight: 500 !important;
        }

        /* 텍스트 인풋 통일 */
        .stTextInput input {
            border-radius: 6px !important;
        }

        /* 데이터 에디터 헤더 */
        .stDataFrame thead tr th {
            background-color: #f1f3f5 !important;
            color: #495057 !important;
            font-weight: 600 !important;
        }

        /* 사이드바 타이틀 */
        [data-testid="stSidebar"] h1 {
            color: #1e3a8a !important;
            font-weight: 700 !important;
        }

        /* 라디오 버튼 스타일 */
        [data-testid="stSidebar"] .stRadio > div {
            gap: 0.3rem !important;
        }
        [data-testid="stSidebar"] .stRadio label {
            padding: 0.4rem 0.6rem !important;
            border-radius: 6px !important;
            transition: background 0.2s !important;
        }
        [data-testid="stSidebar"] .stRadio label:hover {
            background-color: #e9ecef !important;
        }

        /* 버전 표기 */
        [data-testid="stSidebar"] .stCaption {
            color: #868e96 !important;
            font-size: 0.75rem !important;
            text-align: center !important;
        }
    </style>
""", unsafe_allow_html=True)

# 3. 관리자 인증 로직 (엔터 입력 및 버튼 클릭 공용)
def check_admin_pw():
    if st.session_state.admin_pw_entry == st.secrets["COMBINER_PW"]:
        st.session_state.admin_mode = True
        st.session_state.admin_pw_entry = ""
    else:
        st.error("비밀번호 불일치")

# 4. 상태 변수 초기화
if 'admin_mode' not in st.session_state: 
    st.session_state.admin_mode = False

def reset_tool(): 
    st.session_state.tool_menu = None
def reset_main(): 
    st.session_state.main_menu = None

# --- 사이드바 영역 ---
with st.sidebar:
    st.title("🚀 QA1 AI 업무 대시보드")
    st.markdown("---")
    
    menu_main = st.radio("메뉴 선택", [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장"
    ], index=1, key="main_menu", on_change=reset_tool)
    
    st.markdown("---")
    
    menu_tool = st.radio("도구", ["단어 조합 생성기"], 
                         index=None, key="tool_menu", on_change=reset_main, label_visibility="collapsed")
    
    st.markdown("---")

    is_secure_selected = (menu_main == "리스크 키워드 확장") or (st.session_state.get("tool_menu") == "단어 조합 생성기")

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

# --- 본문 실행 영역 ---
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
