import streamlit as st
import pandas as pd
import datetime, re, requests, io
from bs4 import BeautifulSoup
import pytz

# --- [1. ENGINE: 슈 님의 11개 루트 100% 보존] ---
class ShuHyperMonitorWeb:
    def __init__(self, main_query):
        self.naver_id = st.secrets["NAVER_ID"]
        self.naver_secret = st.secrets["NAVER_SECRET"]
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.main_query = main_query
        self.ad_context_patterns = [
            r"\[.*(공개|이벤트|특가|판매).*\]", r"\d+% (할인|적립|증정)",
            r"(지금|바로|확인|클릭|가기)하세요", r"(최저가|압도적|독보적|최대 규모)"
        ]

    def is_valid_context(self, text):
        for pattern in self.ad_context_patterns:
            if re.search(pattern, text): return False
        return True

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        
        try:
            # 루트 1: 주요 이슈 (네이버 - 사용자 입력 키워드 최신순)
            if self.main_query:
                res = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={self.main_query}&display=50&sort=date", headers=h).json()
                for i in res.get('items', []):
                    t = BeautifulSoup(i['title'], 'html.parser').get_text()
                    if self.is_valid_context(t): pool.append({'src': '📢 주요 이슈(네이버)', 'kw': t, 'url': i['link']})

            # 루트 2: 실시간 뉴스 (사회 속보 RSS)
            res_rss = requests.get("https://news.naver.com/rss/feed/section/102", headers=self.headers)
            for i in BeautifulSoup(res_rss.text, 'xml').find_all('item')[:30]:
                if self.is_valid_context(i.title.text): pool.append({'src': '⏱️ 실시간 뉴스', 'kw': i.title.text, 'url': i.link.text})

            # 루트 3: 급상승 시그널
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            for i in sig.get('top10', []): pool.append({'src': '📈 시그널', 'kw': i['keyword'], 'url': f"https://search.naver.com/search.naver?query={i['keyword']}"})

            # (루트 4~11: 구글, 다음, 네이트, 줌, 에펨, 디시 등 기존 11개 로직 동일 적용)
            # [생략된 부분은 위 fetch_all_routes 내부에서 슈 님의 전체 코드를 그대로 유지하면 됩니다]

        except: pass
        
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return unique_pool

# --- [2. UI: 칸 사이즈 고정 및 가운데 정렬] ---
st.set_page_config(layout="wide", page_title="실시간 이슈 모니터링")

# 표 내부 텍스트 가운데 정렬을 위한 CSS 추가
st.markdown("""
    <style>
    /* 데이터 에디터 내 특정 열 가운데 정렬 시도 (지원 환경에 따라 다름) */
    div[data-testid="stTable"] td { text-align: center !important; }
    .stButton > button { height: 2.8rem !important; font-weight: bold; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

if 'data_pool' not in st.session_state: st.session_state.data_pool = []
if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

st.title("🛡️ 실시간 이슈 관제 센터")

with st.expander("⚙️ 관제 설정 (주요 이슈 검색어)", expanded=True):
    target_query = st.text_input("타겟 키워드", value="논란 OR 사건 OR 사고 OR 적발")

top_col1, top_col2, top_col3 = st.columns([1, 1, 1])
with top_col1:
    if st.button("🚀 전체 채널 스캔", use_container_width=True):
        st.session_state.data_pool = [dict(d, 선택=True) for d in ShuHyperMonitorWeb(target_query).fetch_all_routes()]
        st.session_state.editor_key += 1; st.rerun()

with top_col2:
    filter_query = st.text_input("🔍 결과 내 필터링", placeholder="검색어 입력...", label_visibility="collapsed")
with top_col3:
    count = len(st.session_state.data_pool)
    st.text_input("📊 수집 현황", value=f"{count}개 탐지됨", disabled=True, label_visibility="collapsed")

st.divider()

if st.session_state.data_pool:
    df = pd.DataFrame(st.session_state.data_pool)
    if filter_query: df = df[df['kw'].str.contains(filter_query, case=False)]

    korea_now = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m/%d %H:%M')
    df['데이터 수집 시점'] = korea_now

    # 상단 버튼 (전체선택/해제)
    _, btn_col = st.columns([8.2, 1.8])
    with btn_col:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("전체✅"):
                for item in st.session_state.data_pool: item['선택'] = True
                st.session_state.editor_key += 1; st.rerun()
        with b2:
            if st.button("해제❌"):
                for item in st.session_state.data_pool: item['선택'] = False
                st.session_state.editor_key += 1; st.rerun()

    # [수정 포인트] 칸 사이즈 고정 및 가운데 정렬 설정
    edited_df = st.data_editor(
        df,
        column_config={
            "데이터 수집 시점": st.column_config.TextColumn(
                "데이터 수집 시점", 
                width=120,    # 고정 사이즈
                help="데이터가 수집된 한국 시간"
            ),
            "src": st.column_config.TextColumn(
                "출처", 
                width=130,    # 고정 사이즈
            ),
            "kw": st.column_config.TextColumn(
                "이슈 헤드라인 전문", 
                width="large" # 유동적 확보
            ),
            "url": st.column_config.LinkColumn(
                "원문", 
                display_text="🔗", # 링크 칸 최소화
                width=60        # 좁게 설정
            ),
            "선택": st.column_config.CheckboxColumn(
                "선택", 
                width=60        # 좁게 설정
            )
        },
        column_order=("데이터 수집 시점", "src", "kw", "url", "선택"),
        hide_index=True,
        use_container_width=True,
        key=f"editor_{st.session_state.editor_key}"
    )

    # 보고서 추출
    selected_rows = edited_df[edited_df['선택'] == True]
    if not selected_rows.empty:
        output = io.BytesIO()
        selected_rows.drop(columns=['선택']).to_excel(output, index=False)
        st.download_button(label="📊 엑셀 리포트 추출", data=output.getvalue(), file_name="Shu_Report.xlsx", use_container_width=True)
