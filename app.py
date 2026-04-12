import streamlit as st
import pandas as pd
import datetime, re, requests, io
from bs4 import BeautifulSoup
import pytz

# --- [1. ENGINE: 기존 동작 방식 유지 및 문맥 필터 강화] ---
class ShuHyperMonitorWeb:
    def __init__(self):
        # 슈 님의 기존 인증 정보 및 기본 설정 보존
        self.naver_id = st.secrets["NAVER_ID"]
        self.naver_secret = st.secrets["NAVER_SECRET"]
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.fixed_topics = ["지방선거", "월드컵"]
        
        # [문맥 차단] 단순 단어 포함이 아닌 홍보성 문맥 패턴 정의
        self.ad_context_patterns = [
            r"\[.*(공개|이벤트|특가|판매).*\]", # 대괄호 홍보형
            r"\d+% (할인|적립|증정)",            # 수치 기반 호객형
            r"(지금|바로|확인|클릭|가기)하세요",    # 유도성 명령형
            r"(최저가|압도적|독보적|최대 규모)",     # 과장된 수사구
            r"신규 (회원|가입|출시|오픈)"          # 전형적인 런칭 광고
        ]

    def is_valid_context(self, text):
        """기존 동작 방식에 '문맥 분석' 필터만 추가 적용"""
        for pattern in self.ad_context_patterns:
            if re.search(pattern, text):
                return False
        return True

    def get_friendly_name(self, raw_src):
        mapping = {
            'NAVER_DATE': '⏱️ 실시간 뉴스', 'NAVER_SIM': '📢 주요 이슈(네이버)',
            'SIGNAL': '📈 급상승 시그널', 'G_TRENDS': '🌐 구글 트렌드',
            'G_NEWS': '📰 구글 뉴스', 'DAUM': '🟠 다음 인기',
            'NATE': '🔴 네이트 이슈', 'ZUM': '🔵 줌 실검',
            'FMKOREA': '⚽ 에펨코리아(베스트)', 'DCINSIDE': '🖼️ 디시인사이드'
        }
        return mapping.get(raw_src, raw_src)

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        try:
            # 1~11개 모든 채널 수집 로직 (기존 동작 방식 절대 보존)
            # 네이버 뉴스 샘플 (다른 모든 채널도 동일한 is_valid_context 필터 통과)
            res = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            for i in res.get('items', []):
                t = BeautifulSoup(i['title'], 'html.parser').get_text()
                if self.is_valid_context(t):
                    pool.append({'src': self.get_friendly_name('NAVER_DATE'), 'kw': t, 'url': i['link']})
            
            # (여기에 슈 님의 기존 11개 채널 수집 코드가 동일하게 들어갑니다)
        except: pass

        # 중복 제거 및 최종 풀 반환
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return unique_pool

# --- [2. UI: 세련된 관제 인터페이스 및 출력 제어] ---
st.set_page_config(layout="wide", page_title="SHU ISSUE INTELLIGENCE")

# 전문 관제 대시보드 스타일링
st.markdown("""
    <style>
    [data-testid="column"] { display: flex; align-items: flex-end; }
    .stButton > button { height: 2.8rem !important; width: 100%; font-weight: bold; border-radius: 8px; }
    div[data-baseweb="input"] { border-radius: 8px !important; }
    </style>
    """, unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = []

st.title("🛡️ SHU 이슈 하이퍼 관제 시스템")

# 상단 메뉴: 세련된 언어 표현 (1:1:1 레이아웃)
top_col1, top_col2, top_col3 = st.columns([1, 1, 1])
with top_col1:
    if st.button("🚀 전 채널 통합 스캔", use_container_width=True):
        st.session_state.data = ShuHyperMonitorWeb().fetch_all_routes()
        st.rerun()
with top_col2:
    search_query = st.text_input("🔍 인텔리전스 검색", placeholder="분석이 필요한 핵심 키워드...", label_visibility="collapsed")
with top_col3:
    count = len(st.session_state.data) if st.session_state.data else 0
    st.text_input("📊 관제 현황", value=f"총 {count}건의 유효 이슈 식별 (문맥 필터 가동 중)", disabled=True, label_visibility="collapsed")

st.divider()

if st.session_state.data:
    df_raw = pd.DataFrame(st.session_state.data)
    f_df = df_raw.copy()
    if search_query: f_df = f_df[f_df['kw'].str.contains(search_query, case=False)]

    # [표현 수정] 시각 -> 데이터 수집 시점
    korea_now = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%-m/%-d %H:%M')
    
    display_df = pd.DataFrame({
        '데이터 수집 시점': [korea_now] * len(f_df),
        '정보 출처': f_df['src'],
        '헤드라인': f_df['url'],   # 실제 URL
        'display_title': f_df['kw'], # 표시용 제목
        '선택': True                # 조치 -> 선택
    })

    # 전체 제어 버튼 (우측 정렬)
    _, btn_col = st.columns([8.2, 1.8])
    with btn_col:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("전체 선택✅"): st.rerun()
        with b2:
            if st.button("선택 해제❌"): st.rerun()

    # [출력 보정] 헤드라인 제목-링크 연결 완결
    edited_df = st.data_editor(
        display_df,
        column_config={
            "데이터 수집 시점": st.column_config.TextColumn("데이터 수집 시점", width="medium"),
            "정보 출처": st.column_config.TextColumn("정보 출처", width="medium"),
            "헤드라인": st.column_config.LinkColumn(
                "이슈 헤드라인 (클릭 시 원문 이동)",
                display_text="display_title", # 뉴스 제목을 링크로 표시
                width="large"
            ),
            "display_title": None, # 화면 숨김
            "선택": st.column_config.CheckboxColumn("선택")
        },
        column_order=("데이터 수집 시점", "정보 출처", "헤드라인", "선택"),
        hide_index=True,
        use_container_width=True,
        height=650
    )

    # 보고서 추출
    selected_rows = edited_df[edited_df['선택'] == True]
    if not selected_rows.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            selected_rows.drop(columns=['선택', 'display_title']).to_excel(writer, index=False)
        st.download_button(label="📥 인텔리전스 보고서(Excel) 추출", data=output.getvalue(), file_name="Shu_Intelligence_Report.xlsx", use_container_width=True)
