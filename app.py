import streamlit as st
from page_monitor import run_monitor
from page_keyword import run_keyword
from page_claude import run_claude_collector  
from page_combiner import run_combiner
from page_scroll import run_domain_collector

# 1. 페이지 설정
st.set_page_config(layout="wide", page_title="Shu Risk Center", page_icon="🚨")

# 2. 공통 CSS (디자인 보강)
st.markdown("""
    <style>
        [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stToolbar"], header[data-testid="stHeader"] {
            display: none !important; height: 0 !important;
        }
        .main .block-container { padding-top: 2rem !important; max-width: 95% !important; }
        
        /* 사이드바 라디오 버튼 간격 및 디자인 */
        [data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
        [data-testid="stSidebar"] .stRadio label {
            padding: 8px 12px !important;
            border-radius: 8px !important;
            margin-bottom: 2px !important;
        }
        
        /* 구분선 스타일 커스텀 */
        .sidebar-divider {
            margin: 15px 0;
            border-top: 1px solid #e0e0e0;
            width: 100%;
        }
        
        [data-testid="stSidebar"] { background-color: #f8f9fa !important; }
        [data-testid="stSidebar"] h1 { color: #212529 !important; font-weight: 700 !important; font-size: 1.5rem !important; }
    </style>
""", unsafe_allow_html=True)

# 3. 관리자 인증 로직
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

if 'admin_mode' not in st.session_state: 
    st.session_state.admin_mode = False

# --- 사이드바 영역 ---
with st.sidebar:
    st.title("🚀 QA1 AI 업무 대시보드")
    st.write("") # 미세 여백
    
    # [수정] 메뉴 리스트에서 선 모양 텍스트 제거
    menu_list = [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장",
        "도메인 추출🚧",
        "단어 조합 생성기🚧"
    ]

    # [핵심] 통합 라디오 버튼
    # 메뉴를 쪼개지 않고 하나로 유지하여 '중복 선택' 원천 차단
    menu_main = st.radio(
        "📋 메뉴 선택",
        menu_list,
        index=1,
        key="total_menu_radio"
    )
    
    # [수정] CSS를 이용해 3번 메뉴와 4번 메뉴 사이에 진짜 실선 긋기
    # 파이썬 코드가 실행될 때 시각적으로만 구분선을 끼워넣습니다.
    st.markdown("""
        <script>
            var labels = window.parent.document.querySelectorAll('label[data-baseweb="radio"]');
            if (labels.length >= 5) {
                // 3번째 메뉴(리스크 키워드 확장) 다음에 실선 추가
                var divider = document.createElement('div');
                divider.style.borderTop = '1px solid #ddd';
                divider.style.margin = '10px 5px';
                labels[2].parentElement.after(divider);
            }
        </script>
    """, unsafe_allow_html=True)
    
    st.markdown("---")

    # 보안 대상 메뉴 설정
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

# --- 본문 실행 영역 ---
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
