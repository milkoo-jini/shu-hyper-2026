import streamlit as st
import pandas as pd
import datetime, re, requests, io
from bs4 import BeautifulSoup
import pytz

# --- [1. ENGINE: AI 로직 제거, 순수 11개 루트 복구] ---
class ShuMonitorEngine:
    def __init__(self):
        self.naver_id = st.secrets["NAVER_ID"]
        self.naver_secret = st.secrets["NAVER_SECRET"]
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.fixed_query = "먹튀사이트 OR 사칭광고 OR 가짜후기 OR 고수익알바 OR 불법적발 OR 논란 OR 사건 OR 사고 OR 적발 OR 속보"

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        try:
            # 루트 1: 네이버 뉴스 API
            res = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={self.fixed_query}&display=100&sort=date", headers=h).json()
            for i in res.get('items', []):
                t = BeautifulSoup(i['title'], 'html.parser').get_text()
                pool.append({'src': "📢네이버", 'kw': t, 'url': i['link']})

            # 루트 2: 실시간 속보 RSS
            res_rss = requests.get("https://news.naver.com/rss/feed/section/102", headers=self.headers)
            for i in BeautifulSoup(res_rss.text, 'xml').find_all('item')[:30]:
                pool.append({'src': "⏱️속보", 'kw': i.title.text, 'url': i.link.text})

            # 루트 3: 급상승 시그널
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            for i in sig.get('top10', []):
                t = i['keyword']
                pool.append({'src': "📈시그널", 'kw': t, 'url': f"https://search.naver.com/search.naver?query={t}"})

            # [루트 4~11: 나머지 구글, 커뮤니티 등 기존 코드를 여기에 그대로 유지]

        except Exception as e:
            st.error(f"수집 중 오류 발생: {e}")
        
        # 중복 제거
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return unique_pool

# --- [2. UI: 제목 복구 및 버튼 정밀 배치] ---
st.set_page_config(layout="wide", page_title="관제 센터")

st.markdown("""
    <style>
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; }
    div[data-testid="stVerticalBlock"] > div { font-size: 0.85rem !important; }
    div[data-testid="stTable"] td { text-align: center !important; }
    .stButton > button { height: 2.1rem !important; font-size: 0.85rem !important; font-weight: bold; border-radius: 4px; }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    h3 { margin-top: -10px !important; margin-bottom: 5px !important; color: #1E88E5; }
    </style>
    """, unsafe_allow_html=True)

if 'data_pool' not in st.session_state: st.session_state.data_pool = []
if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

# [상단 1라인] 업무 제목 및 메인 컨트롤
t1, t2, t3, t4 = st.columns([1.5, 1, 1, 1.2])
with t1:
    st.markdown("### 🛡️ 실시간 이슈 관제")
with t2:
    if st.button("🚀 전체 채널 스캔 시작", use_container_width=True):
        st.session_state.data_pool = [dict(d, 선택=True) for d in ShuMonitorEngine().fetch_all_routes()]
        st.session_state.editor_key += 1; st.rerun()
with t3:
    filter_query = st.text_input("", placeholder="🔍 결과 내 필터링...", label_visibility="collapsed")
with t4:
    count = len(st.session_state.data_pool)
    st.text_input("", value=f"📊 {count}개 이슈 감지됨", disabled=True, label_visibility="collapsed")

# [상단 2라인] 전체선택/해제 (우측 정렬 및 콤팩트 사이즈)
_, sel_col = st.columns([8.2, 1.8])
with sel_col:
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("전체선택", use_container_width=True):
            for item in st.session_state.data_pool: item['선택'] = True
            st.session_state.editor_key += 1; st.rerun()
    with sc2:
        if st.button("선택해제", use_container_width=True):
            for item in st.session_state.data_pool: item['선택'] = False
            st.session_state.editor_key += 1; st.rerun()

if st.session_state.data_pool:
    df = pd.DataFrame(st.session_state.data_pool)
    if filter_query: df = df[df['kw'].str.contains(filter_query, case=False)]
    df['수집시점'] = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m/%d %H:%M')

    # 슈 님 확정 4개 메뉴 폭 고정
    edited_df = st.data_editor(
        df,
        column_config={
            "수집시점": st.column_config.TextColumn("수집시점", width=85),
            "src": st.column_config.TextColumn("출처", width=65),
            "kw": st.column_config.TextColumn("이슈 헤드라인 전문", width="large"),
            "url": st.column_config.LinkColumn("원문", display_text="🔗", width=65),
            "선택": st.column_config.CheckboxColumn("선택", width=65)
        },
        column_order=("수집시점", "src", "kw", "url", "선택"),
        hide_index=True,
        use_container_width=True,
        key=f"editor_{st.session_state.editor_key}"
    )

    if not edited_df[edited_df['선택'] == True].empty:
        output = io.BytesIO()
        edited_df[edited_df['선택'] == True].drop(columns=['선택']).to_excel(output, index=False)
        st.download_button(label="📊 골라낸 기사 엑셀 리포트 추출", data=output.getvalue(), file_name="Shu_Report.xlsx", use_container_width=True)
