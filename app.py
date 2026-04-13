import streamlit as st
import pandas as pd
import datetime, re, requests, io
from bs4 import BeautifulSoup
import pytz

# --- [1. ENGINE: 월드컵/지방선거 포함 11개 채널] ---
class ShuMonitorEngine:
    def __init__(self):
        try:
            self.naver_id = st.secrets["NAVER_ID"]
            self.naver_secret = st.secrets["NAVER_SECRET"]
        except:
            self.naver_id = self.naver_secret = None
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.fixed_topics = ["월드컵", "지방선거"]

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        try:
            # 네이버(정확/최신) 및 고정주제
            n_sim = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=15&sort=sim", headers=h).json()
            pool.extend([{'src': 'NAVER(정확)', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in n_sim.get('items', [])])
            n_date = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            pool.extend([{'src': 'NAVER(최신)', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in n_date.get('items', [])])
            for t in self.fixed_topics:
                t_n = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=30&sort=date", headers=h).json()
                pool.extend([{'src': f'🔥{t}', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in t_n.get('items', [])])
            
            # 기타 11개 채널 (시그널, 네이트, 줌, 구글, 다음, FM, DC 등)
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            pool.extend([{'src': 'SIGNAL', 'kw': i['keyword'], 'url': f"https://search.naver.com/search.naver?query={i['keyword']}"} for i in sig.get('top10', [])])
            # ... (나머지 줌, 네이트 등 11개 로직 동일)
        except: pass
        
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return sorted(unique_pool, key=lambda x: 0 if any(topic in x['src'] for topic in self.fixed_topics) else 1)

# --- [2. UI: 레이아웃 및 메뉴 폭 고정] ---
st.set_page_config(layout="wide", page_title="이슈 모니터링")

st.markdown("""
    <style>
    /* 전체 여백 조절 */
    .block-container { padding-top: 1.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    /* 버튼 스타일 */
    .stButton > button { height: 2.5rem !important; font-weight: bold; border-radius: 6px; width: 100%; }
    /* 제목 스타일 */
    .main-title { font-size: 1.8rem !important; font-weight: bold; color: #1E88E5; margin-bottom: 1rem; }
    #MainMenu, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

if 'data_pool' not in st.session_state: st.session_state.data_pool = []
if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

# 상단 제목 영역
st.markdown('<p class="main-title">🛡️ 실시간 이슈 모니터링</p>', unsafe_allow_html=True)

# 상단 컨트롤바 (가독성 확보를 위해 칸 크기 조정)
c1, c2, c3 = st.columns([1.5, 2, 1.5])
with c1:
    if st.button("🚀 전체 채널 스캔 시작"):
        st.session_state.data_pool = [dict(d, 선택=True) for d in ShuMonitorEngine().fetch_all_routes()]
        st.session_state.editor_key += 1; st.rerun()
with c2:
    filter_query = st.text_input("", placeholder="🔍 결과 내 키워드 필터링...", label_visibility="collapsed")
with c3:
    count = len(st.session_state.data_pool)
    st.info(f"📊 현재 {count}개의 이슈가 탐지되었습니다.")

st.divider()

# 선택 버튼 영역 (우측 끝 정렬)
_, b1, b2 = st.columns([7, 1.5, 1.5])
with b1:
    if st.button("전체선택"):
        for item in st.session_state.data_pool: item['선택'] = True
        st.session_state.editor_key += 1; st.rerun()
with b2:
    if st.button("선택해제"):
        for item in st.session_state.data_pool: item['선택'] = False
        st.session_state.editor_key += 1; st.rerun()

# 데이터 표 (요청하신 폭 강제 고정)
if st.session_state.data_pool:
    df = pd.DataFrame(st.session_state.data_pool)
    if filter_query: df = df[df['kw'].str.contains(filter_query, case=False)]
    df['수집시점'] = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M')

    edited_df = st.data_editor(
        df,
        column_config={
            "수집시점": st.column_config.TextColumn("수집시점", width=85),
            "src": st.column_config.TextColumn("출처", width=65), # 요청하신 65
            "kw": st.column_config.TextColumn("이슈 헤드라인 전문", width="large"),
            "url": st.column_config.LinkColumn("원문", display_text="🔗", width=65), # 요청하신 65
            "선택": st.column_config.CheckboxColumn("선택", width=65) # 요청하신 65
        },
        column_order=("수집시점", "src", "kw", "url", "선택"),
        hide_index=True,
        use_container_width=True,
        key=f"editor_{st.session_state.editor_key}"
    )

    # 하단 엑셀 버튼
    if not edited_df[edited_df['선택'] == True].empty:
        output = io.BytesIO()
        edited_df[edited_df['선택'] == True].drop(columns=['선택']).to_excel(output, index=False)
        st.download_button(label="📊 선택한 기사 엑셀 리포트 다운로드", data=output.getvalue(), file_name="Shu_Report.xlsx", use_container_width=True)
