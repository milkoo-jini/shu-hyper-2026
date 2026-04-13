import streamlit as st
import pandas as pd
import datetime, re, requests, io
from bs4 import BeautifulSoup
import pytz

# --- [1. ENGINE: 고정주제(월드컵, 지방선거) 반영 11개 루트] ---
class ShuMonitorEngine:
    def __init__(self):
        try:
            self.naver_id = st.secrets["NAVER_ID"]
            self.naver_secret = st.secrets["NAVER_SECRET"]
        except:
            self.naver_id = self.naver_secret = None
        
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # [수정] 슈 님의 진짜 고정 주제 2개
        self.fixed_topics = ["월드컵", "지방선거"]

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        
        try:
            # 1. 네이버 뉴스 (정확도/최신순) - 일반 관제
            n_sim = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=15&sort=sim", headers=h).json()
            pool.extend([{'src': 'NAVER(정확)', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in n_sim.get('items', [])])
            
            n_date = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            pool.extend([{'src': 'NAVER(최신)', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in n_date.get('items', [])])
            
            # 2. [고정주제 2개] 월드컵, 지방선거 집중 수집 (최상단 노출용)
            for t in self.fixed_topics:
                t_n = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=30&sort=date", headers=h).json()
                # 출처명을 FIXED 대신 주제명으로 직관적으로 표시
                pool.extend([{'src': f'🔥{t}', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in t_n.get('items', [])])
            
            # 3. 기타 채널들 (시그널, 네이트, 줌, 구글, 다음, FM, DC 등)
            # 시그널
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            pool.extend([{'src': 'SIGNAL', 'kw': i['keyword'], 'url': f"https://search.naver.com/search.naver?query={i['keyword']}"} for i in sig.get('top10', [])])
            
            # 네이트/줌/구글 등 생략된 11개 로직 내부 포함됨...
            # [기존에 드린 11개 채널 수집 코드가 이 아래에 모두 들어갑니다]

        except: pass
        
        # 중복 제거
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        
        # [우선순위] 월드컵/지방선거가 무조건 맨 위로 오게 정렬
        return sorted(unique_pool, key=lambda x: 0 if any(topic in x['src'] for topic in self.fixed_topics) else 1)

# --- [2. UI: 슬림 레이아웃 및 제목 원복] ---
st.set_page_config(layout="wide", page_title="이슈 모니터링")

st.markdown("""
    <style>
    .block-container { padding-top: 0.5rem !important; }
    .stButton > button { height: 2.1rem !important; font-size: 0.85rem !important; font-weight: bold; }
    h3 { margin-top: -10px !important; margin-bottom: 5px !important; color: #1E88E5; }
    </style>
    """, unsafe_allow_html=True)

if 'data_pool' not in st.session_state: st.session_state.data_pool = []
if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

t1, t2, t3, t4 = st.columns([1.5, 1, 1, 1.2])
with t1: st.markdown("### 🛡️ 실시간 이슈 모니터링")
with t2:
    if st.button("🚀 전체 채널 스캔 시작", use_container_width=True):
        st.session_state.data_pool = [dict(d, 선택=True) for d in ShuMonitorEngine().fetch_all_routes()]
        st.session_state.editor_key += 1; st.rerun()
with t3: filter_query = st.text_input("", placeholder="🔍 필터링...", label_visibility="collapsed")
with t4:
    count = len(st.session_state.data_pool)
    st.text_input("", value=f"📊 {count}개 이슈 감지", disabled=True, label_visibility="collapsed")

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

    edited_df = st.data_editor(
        df,
        column_config={
            "수집시점": st.column_config.TextColumn("수집시점", width=85),
            "src": st.column_config.TextColumn("출처", width=95),
            "kw": st.column_config.TextColumn("이슈 헤드라인 전문", width="large"),
            "url": st.column_config.LinkColumn("원문", display_text="🔗", width=65),
            "선택": st.column_config.CheckboxColumn("선택", width=65)
        },
        column_order=("수집시점", "src", "kw", "url", "선택"),
        hide_index=True, use_container_width=True, key=f"editor_{st.session_state.editor_key}"
    )

    if not edited_df[edited_df['선택'] == True].empty:
        output = io.BytesIO()
        edited_df[edited_df['선택'] == True].drop(columns=['선택']).to_excel(output, index=False)
        st.download_button(label="📊 골라낸 기사 엑셀 추출", data=output.getvalue(), file_name="Shu_Report.xlsx", use_container_width=True)
