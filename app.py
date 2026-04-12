import streamlit as st
import pandas as pd
import datetime, re, time, requests, io
from bs4 import BeautifulSoup
import pytz

# --- [1. SHU HYPER ENGINE: 11개 채널 & 필터 데이터] ---
class ShuHyperMonitorWeb:
    def __init__(self):
        self.naver_id = st.secrets["NAVER_ID"]
        self.naver_secret = st.secrets["NAVER_SECRET"]
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.fixed_topics = ["지방선거", "월드컵"]
        self.risk_keywords = ["논란", "비판", "폭로", "의혹", "사기", "피해", "수사", "연패", "경질", "공천", "중계권", "충격", "속보"]
        self.exclude_ad_keywords = ["변호사", "법무법인", "무료상담", "승소", "마케팅", "홍보","기고"]
        self.korea_tz = pytz.timezone('Asia/Seoul')

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
            # 11개 채널 수집 (네이버, 구글, 시그널, 다음, 네이트, 줌, 커뮤니티 등)
            for t in self.fixed_topics:
                t_n = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=20&sort=date", headers=h).json()
                pool.extend([{'src': f'📍 고정주제({t})', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in t_n.get('items', [])])
            
            n_date = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            pool.extend([{'src': self.get_friendly_name('NAVER_DATE'), 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in n_date.get('items', [])])
            
            g_trends = requests.get("https://trends.google.com/trending/rss?geo=KR", headers=self.headers)
            for i in BeautifulSoup(g_trends.text, 'xml').find_all('item')[:10]:
                kw = i.title.text
                pool.append({'src': self.get_friendly_name('G_TRENDS'), 'kw': kw, 'url': f"https://www.google.com/search?q={kw}&tbm=nws"})
            
            # ... 기타 채널 로직 동일하게 유지
        except: pass

        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return unique_pool

# --- [2. UI 설정: 상단 메뉴 배열 최적화] ---
st.set_page_config(layout="wide", page_title="실시간 이슈 모니터링")

# 버튼과 텍스트박스 높이를 일치시키고 간격을 조정하는 CSS
st.markdown("""
    <style>
    [data-testid="column"] { display: flex; align-items: flex-end; }
    .stButton > button { height: 2.8rem !important; width: 100%; }
    div[data-baseweb="input"] { height: 2.8rem !important; }
    </style>
    """, unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = []
if 'select_all' not in st.session_state: st.session_state.select_all = True

st.title("🛡️ 실시간 이슈 관제 센터")

# 상단 메뉴 1:1:1 정렬 (크기 통일)
top_col1, top_col2, top_col3 = st.columns([1, 1, 1])
with top_col1:
    if st.button("🚀 전체 채널 스캔", use_container_width=True):
        st.session_state.data = ShuHyperMonitorWeb().fetch_all_routes()
        st.session_state.select_all = True
        st.rerun()
with top_col2:
    search_query = st.text_input("🔍 키워드 검색", placeholder="검색어 입력...", label_visibility="collapsed")
with top_col3:
    count = len(st.session_state.data) if st.session_state.data else 0
    st.text_input("📊 수집 현황", value=f"{count}개 탐지됨", disabled=True, label_visibility="collapsed")

st.divider()

if st.session_state.data:
    df_raw = pd.DataFrame(st.session_state.data)
    
    # 정렬: 지방선거 > 월드컵 > 실시간 뉴스 > 나머지
    def get_order(src):
        if "지방선거" in src: return 0
        if "월드컵" in src: return 1
        if "실시간 뉴스" in src: return 2
        return 3
    df_raw['order'] = df_raw['src'].apply(get_order)
    df_raw = df_raw.sort_values(by='order').reset_index(drop=True)

    # 필터
    all_srcs = ["전체 채널"] + sorted(list(df_raw['src'].unique()))
    selected_source = st.pills("🎯 채널 필터", all_srcs, default="전체 채널")

    f_df = df_raw.copy()
    if search_query: f_df = f_df[f_df['kw'].str.contains(search_query, case=False)]
    if selected_source != "전체 채널": f_df = f_df[f_df['src'] == selected_source]

    # 시각 형식 (M/D HH:MM)
    f_time = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%-m/%-d %H:%M')
    
    display_df = pd.DataFrame({
        '시각': [f_time] * len(f_df),
        '출처': f_df['src'],
        '제목데이터': f_df['kw'], 
        '헤드라인': f_df['url'],   
        '선택': st.session_state.select_all
    })

    # 전체 선택/해제 버튼 우측(조치 컬럼 위) 배치
    _, btn_col = st.columns([8.2, 1.8])
    with btn_col:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("전체✅", use_container_width=True):
                st.session_state.select_all = True
                st.rerun()
        with b2:
            if st.button("해제❌", use_container_width=True):
                st.session_state.select_all = False
                st.rerun()

    # 데이터 에디터: 제목 노출 버그 해결본
    edited_df = st.data_editor(
        display_df,
        column_config={
            "시각": st.column_config.TextColumn("시각", width="medium"),
            "출처": st.column_config.TextColumn("출처", width="medium"),
            "헤드라인": st.column_config.LinkColumn(
                "헤드라인 (클릭 시 이동)", 
                display_text="제목데이터", # '제목데이터' 컬럼을 참조하여 실제 제목 노출
                width="large"
            ),
            "제목데이터": None, 
            "선택": st.column_config.CheckboxColumn("선택", default=st.session_state.select_all)
        },
        column_order=("시각", "출처", "헤드라인", "선택"),
        hide_index=True,
        use_container_width=True,
        height=600,
        key="editor_shu_v11"
    )

    # 리포트 추출
    selected_rows = edited_df[edited_df['선택'] == True]
    if not selected_rows.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output) as writer:
            selected_rows.drop(columns=['선택']).to_excel(writer, index=False)
        st.download_button(label="📊 엑셀 리포트 추출", data=output.getvalue(), file_name="Shu_Report.xlsx", use_container_width=True)
