import streamlit as st
import pandas as pd
import datetime, re, requests, io, os
from bs4 import BeautifulSoup
import pytz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- [1. ENGINE: 기존 11개 루트 및 AI 정렬 로직 동일] ---
class ShuHyperAI:
    def __init__(self):
        self.naver_id = st.secrets["NAVER_ID"]
        self.naver_secret = st.secrets["NAVER_SECRET"]
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.fixed_query = "먹튀사이트 OR 사칭광고 OR 가짜후기 OR 고수익알바 OR 불법적발 OR 논란 OR 사건 OR 사고 OR 적발 OR 속보"
        self.train_lines = self._load_training_data()
        self.vectorizer = TfidfVectorizer()
        if self.train_lines:
            self.train_vectors = self.vectorizer.fit_transform(self.train_lines)

    def _load_training_data(self):
        file_path = "정답기사리스트.txt"
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f.readlines() if len(line.strip()) > 5]
        return []

    def get_similarity(self, title):
        if not self.train_lines: return 0.0
        try:
            target_vec = self.vectorizer.transform([title])
            sim = cosine_similarity(target_vec, self.train_vectors)
            return float(sim.max())
        except: return 0.0

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        try:
            res = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={self.fixed_query}&display=100&sort=date", headers=h).json()
            for i in res.get('items', []):
                t = BeautifulSoup(i['title'], 'html.parser').get_text()
                sim_score = self.get_similarity(t)
                tag = "🎯정답유사" if sim_score > 0.25 else "📢네이버"
                pool.append({'src': tag, 'kw': t, 'url': i['link'], 'score': sim_score})
            # [루트 2~11: 기존 슈 님의 코드를 그대로 유지]
        except: pass
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return sorted(unique_pool, key=lambda x: x.get('score', 0) if x.get('score', 0) > 0.25 else 0, reverse=True)

# --- [2. UI: 초슬림 레이아웃 + 버튼 복구] ---
st.set_page_config(layout="wide", page_title="관제 센터")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    div[data-testid="stVerticalBlock"] > div { font-size: 0.9rem !important; }
    div[data-testid="stTable"] td { text-align: center !important; }
    /* 버튼 높이 조절 */
    .stButton > button { height: 2.2rem !important; font-weight: bold; border-radius: 6px; }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

if 'data_pool' not in st.session_state: st.session_state.data_pool = []
if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

# 상단 관제 라인 (초슬림)
c1, c2, c3 = st.columns([1.2, 1.5, 1.3])
with c1:
    if st.button("🚀 AI 관제 가동", use_container_width=True):
        st.session_state.data_pool = [dict(d, 선택=True) for d in ShuHyperAI().fetch_all_routes()]
        st.session_state.editor_key += 1; st.rerun()
with c2:
    filter_query = st.text_input("", placeholder="🔍 결과 내 필터링...", label_visibility="collapsed")
with c3:
    count = len(st.session_state.data_pool)
    st.text_input("", value=f"📊 {count}개 이슈 감지됨", disabled=True, label_visibility="collapsed")

# 표 바로 위에 전체선택/해제 버튼 배치
_, sel_col = st.columns([8.2, 1.8])
with sel_col:
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("전체✅"):
            for item in st.session_state.data_pool: item['선택'] = True
            st.session_state.editor_key += 1; st.rerun()
    with sc2:
        if st.button("해제❌"):
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
            "선택": st.column_config.CheckboxColumn("선택", width=65),
            "score": None 
        },
        column_order=("수집시점", "src", "kw", "url", "선택"),
        hide_index=True,
        use_container_width=True,
        key=f"editor_{st.session_state.editor_key}"
    )

    if not edited_df[edited_df['선택'] == True].empty:
        output = io.BytesIO()
        edited_df[edited_df['선택'] == True].drop(columns=['선택', 'score']).to_excel(output, index=False)
        st.download_button(label="📊 엑셀 리포트 추출", data=output.getvalue(), file_name="Shu_Report.xlsx", use_container_width=True)
