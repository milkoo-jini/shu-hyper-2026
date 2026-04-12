import streamlit as st
import pandas as pd
import datetime, re, requests, io, os
from bs4 import BeautifulSoup
import pytz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- [1. ENGINE: 11개 루트 및 AI 분석 엔진] ---
class ShuHyperAI:
    def __init__(self):
        self.naver_id = st.secrets["NAVER_ID"]
        self.naver_secret = st.secrets["NAVER_SECRET"]
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # 슈 님 확정 통합 쿼리 (10개 핵심 키워드)
        self.fixed_query = "먹튀사이트 OR 사칭광고 OR 가짜후기 OR 고수익알바 OR 불법적발 OR 논란 OR 사건 OR 사고 OR 적발 OR 속보"
        
        # 정답기사리스트.txt 학습
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
        
        # [중요] 여기서부터 11개 루트가 차례대로 실행됩니다.
        try:
            # 루트 1: 네이버 뉴스 API (고정 쿼리)
            res = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={self.fixed_query}&display=100&sort=date", headers=h).json()
            for i in res.get('items', []):
                t = BeautifulSoup(i['title'], 'html.parser').get_text()
                s = self.get_similarity(t)
                pool.append({'src': "🎯정답유사" if s > 0.25 else "📢네이버", 'kw': t, 'url': i['link'], 'score': s})

            # 루트 2: 네이버 사회 속보 RSS
            res_rss = requests.get("https://news.naver.com/rss/feed/section/102", headers=self.headers)
            for i in BeautifulSoup(res_rss.text, 'xml').find_all('item')[:30]:
                t = i.title.text
                s = self.get_similarity(t)
                pool.append({'src': "⏱️속보", 'kw': t, 'url': i.link.text, 'score': s})

            # 루트 3: 급상승 시그널
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            for i in sig.get('top10', []):
                pool.append({'src': "📈시그널", 'kw': i['keyword'], 'url': f"https://search.naver.com/search.naver?query={i['keyword']}", 'score': 0.1})

            # 루트 4~11: 구글트렌드, 다음이슈, 네이트, 줌, FM코리아, 디시인사이드 등
            # (슈 님의 기존 11개 루트 세부 코드가 이 부분에 모두 포함되어야 합니다.)
            # 각 루트에서 수집된 데이터도 'src', 'kw', 'url', 'score' 형식으로 pool에 append 됩니다.

        except Exception as e:
            st.error(f"수집 중 오류 발생: {e}")
        
        # 중복 제거 및 AI 점수순 정렬
        seen, unique_pool = set(), []
        for item in sorted(pool, key=lambda x: x.get('score', 0), reverse=True):
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return unique_pool

# --- [2. UI: 슈 님 전용 고정 레이아웃] ---
st.set_page_config(layout="wide", page_title="실시간 이슈 모니터링")

st.markdown("""
    <style>
    div[data-testid="stTable"] td { text-align: center !important; }
    .stButton > button { height: 2.8rem !important; font-weight: bold; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

if 'data_pool' not in st.session_state: st.session_state.data_pool = []
if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

st.title("🛡️ 실시간 이슈 관제 센터")

# 상단 입력창 제거, 버튼과 필터만 유지
top_col1, top_col2, top_col3 = st.columns([1, 1, 1])
with top_col1:
    if st.button("🚀 11개 채널 AI 관제 가동", use_container_width=True):
        st.session_state.data_pool = [dict(d, 선택=True) for d in ShuHyperAI().fetch_all_routes()]
        st.session_state.editor_key += 1; st.rerun()

with top_col2:
    filter_query = st.text_input("🔍 필터링", placeholder="결과 내 검색...", label_visibility="collapsed")
with top_col3:
    count = len(st.session_state.data_pool)
    st.text_input("📊 현황", value=f"{count}개 탐지됨", disabled=True, label_visibility="collapsed")

st.divider()

if st.session_state.data_pool:
    df = pd.DataFrame(st.session_state.data_pool)
    if filter_query: df = df[df['kw'].str.contains(filter_query, case=False)]
    df['수집시점'] = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m/%d %H:%M')

    # [검수 완료] 슈 님 확정 4개 메뉴 폭 고정 및 가운데 정렬
    edited_df = st.data_editor(
        df,
        column_config={
            "수집시점": st.column_config.TextColumn("수집시점", width=85),
            "src": st.column_config.TextColumn("출처", width=65),
            "kw": st.column_config.TextColumn("이슈 헤드라인 전문", width="large"), # 제목 클릭은 이 열에서 확인
            "url": st.column_config.LinkColumn("원문", display_text="🔗", width=65),
            "선택": st.column_config.CheckboxColumn("선택", width=65),
            "score": None 
        },
        column_order=("수집시점", "src", "kw", "url", "선택"),
        hide_index=True,
        use_container_width=True,
        key=f"editor_{st.session_state.editor_key}"
    )

    # 엑셀 보고서 추출
    selected_rows = edited_df[edited_df['선택'] == True]
    if not selected_rows.empty:
        output = io.BytesIO()
        selected_rows.drop(columns=['선택', 'score']).to_excel(output, index=False)
        st.download_button(label="📊 엑셀 리포트 추출", data=output.getvalue(), file_name="Shu_Report.xlsx", use_container_width=True)
