import streamlit as st
import pandas as pd
import datetime, re, time, requests, io
from bs4 import BeautifulSoup
import pytz

# --- [1. SHU HYPER ENGINE: 로직 무결성 유지] ---
class ShuHyperMonitorWeb:
    def __init__(self):
        self.naver_id = st.secrets["NAVER_ID"]
        self.naver_secret = st.secrets["NAVER_SECRET"]
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.fixed_topics = ["월드컵", "지방선거"]
        self.risk_keywords = ["논란", "비판", "폭로", "의혹", "사기", "피해", "수사", "연패", "경질", "공천", "중계권", "충격", "속보"]
        self.exclude_ad_keywords = ["변호사", "법무법인", "무료상담", "승소", "마케팅", "홍보","기고"]
        self.korea_tz = pytz.timezone('Asia/Seoul')

    def get_friendly_name(self, raw_src):
        mapping = {
            'NAVER_DATE': '⏱️ 실시간 뉴스',
            'NAVER_SIM': '📢 주요 이슈(네이버)',
            'SIGNAL': '📈 급상승 시그널',
            'G_TRENDS': '🌐 구글 트렌드',
            'G_NEWS': '📰 구글 뉴스',
            'DAUM': '🟠 다음 인기',
            'NATE': '🔴 네이트 이슈',
            'ZUM': '🔵 줌 실검',
            'FMKOREA': '⚽ 에펨코리아(베스트)',
            'DCINSIDE': '🖼️ 디시인사이드'
        }
        return mapping.get(raw_src, raw_src)

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        
        try:
            # 1~2. 네이버 (최신/정확)
            n_date = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            pool.extend([{'src': self.get_friendly_name('NAVER_DATE'), 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in n_date.get('items', [])])
            n_sim = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=15&sort=sim", headers=h).json()
            pool.extend([{'src': self.get_friendly_name('NAVER_SIM'), 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in n_sim.get('items', [])])
            
            # 3. 고정 주제
            for t in self.fixed_topics:
                t_n = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=20&sort=date", headers=h).json()
                pool.extend([{'src': f'📍 고정관제({t})', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in t_n.get('items', [])])

            # 4~11. 기타 채널
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            pool.extend([{'src': self.get_friendly_name('SIGNAL'), 'kw': i['keyword'], 'url': f"https://search.naver.com/search.naver?query={i['keyword']}"} for i in sig.get('top10', [])])
            nate = requests.get("https://news.nate.com/edit/issueup/", headers=self.headers)
            pool.extend([{'src': self.get_friendly_name('NATE'), 'kw': a.text.strip(), 'url': 'https://news.nate.com'+a['href']} for a in BeautifulSoup(nate.text, 'html.parser').select('.txt_tit')[:10]])
            zum = requests.get("https://zum.com/#!/home", headers=self.headers)
            pool.extend([{'src': self.get_friendly_name('ZUM'), 'kw': a.text.strip(), 'url': f"https://search.zum.com/search.zum?query={a.text.strip()}"} for a in BeautifulSoup(zum.text, 'html.parser').select('.issue_keyword .txt')[:10]])
            g_trends = requests.get("https://trends.google.com/trending/rss?geo=KR", headers=self.headers)
            pool.extend([{'src': self.get_friendly_name('G_TRENDS'), 'kw': i.title.text, 'url': i.link.text} for i in BeautifulSoup(g_trends.text, 'xml').find_all('item')[:10]])
            d_res = requests.get("https://news.daum.net/ranking/popular", headers=self.headers)
            pool.extend([{'src': self.get_friendly_name('DAUM'), 'kw': a.text.strip(), 'url': a['href']} for a in BeautifulSoup(d_res.text, 'html.parser').select('.link_txt')[:20]])
            g_news = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", headers=self.headers)
            pool.extend([{'src': self.get_friendly_name('G_NEWS'), 'kw': i.title.text, 'url': i.link.text} for i in BeautifulSoup(g_news.text, 'xml').find_all('item')[:15]])
            fm = requests.get("https://www.fmkorea.com/best", headers=self.headers)
            pool.extend([{'src': self.get_friendly_name('FMKOREA'), 'kw': a.get_text().strip(), 'url': 'https://www.fmkorea.com'+a['href']} for a in BeautifulSoup(fm.text, 'html.parser').select('.title.hotdeal_var8 a')[:15]])
            dc = requests.get("https://www.dcinside.com/", headers=self.headers)
            pool.extend([{'src': self.get_friendly_name('DCINSIDE'), 'kw': a.get_text().strip(), 'url': a['href']} for a in BeautifulSoup(dc.text, 'html.parser').select('.box_best .list_best li a')[:10]])
        except: pass

        seen, unique_pool = set(), []
        for item in pool:
            skeleton = re.sub(r'\s+', '', item['kw'])
            if skeleton not in seen:
                seen.add(skeleton)
                unique_pool.append(item)
        return unique_pool

# --- [2. UI 설정: 동일 사이즈 및 칼정렬 최적화] ---
st.set_page_config(layout="wide", page_title="실시간 이슈 모니터링")

# CSS를 사용하여 높이와 정렬을 강제로 맞춤
st.markdown("""
    <style>
    [data-testid="column"] {
        display: flex;
        align-items: flex-end;
    }
    .stButton > button {
        height: 3.0rem !important; /* 입력창 높이와 일치 */
        margin-bottom: 1px;
    }
    </style>
    """, unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = []

st.title("🛡️ 실시간 이슈 관제 센터")

# [수정] 1:1:1 비율로 정렬 (동일 사이즈)
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("🚀 전체 채널 스캔", use_container_width=True):
        engine = ShuHyperMonitorWeb()
        with st.spinner("수집 중..."):
            st.session_state.data = engine.fetch_all_routes()
            st.rerun()

with col2:
    search_query = st.text_input("🔍 키워드 검색", placeholder="소노, 사고, 논란 등")

with col3:
    # 검색된 결과 개수를 보여주는 읽기 전용 칸 (디자인 일관성용)
    count = len(st.session_state.data) if st.session_state.data else 0
    st.text_input("📊 현재 수집 현황", value=f"{count}개 이슈 탐지됨", disabled=True)

st.divider()

if st.session_state.data:
    df_raw = pd.DataFrame(st.session_state.data)
    
    all_srcs = ["전체 채널"] + sorted(list(df_raw['src'].unique()))
    selected_source = st.pills("🎯 채널 필터", all_srcs, default="전체 채널")

    f_df = df_raw.copy()
    if search_query:
        f_df = f_df[f_df['kw'].str.contains(search_query, case=False)]
    if selected_source != "전체 채널":
        f_df = f_df[f_df['src'] == selected_source]

    display_df = pd.DataFrame({
        '시각': datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%H:%M'),
        '출처': f_df['src'],
        '헤드라인': f_df['url'],
        '제목텍스트': f_df['kw'],
        '선택': True
    })

    st.subheader(f"📋 관제 리스트 ({len(display_df)}건)")
    edited_df = st.data_editor(
        display_df,
        column_config={
            "시각": st.column_config.TextColumn("시각", width="small"),
            "출처": st.column_config.TextColumn("출처", width="medium"),
            "헤드라인": st.column_config.LinkColumn(
                "헤드라인 (클릭 시 이동)", 
                display_text=r"^.+$", 
                width="large"
            ),
            "제목텍스트": None, 
            "선택": st.column_config.CheckboxColumn("조치", default=True)
        },
        column_order=("시각", "출처", "헤드라인", "선택"),
        hide_index=True,
        use_container_width=True,
        height=600
    )

    selected_rows = edited_df[edited_df['선택'] == True]
    if not selected_rows.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            selected_rows.drop(columns=['선택', '제목텍스트']).to_excel(writer, index=False)
        
        st.download_button(
            label=f"✅ 선택한 {len(selected_rows)}건 리포트 다운로드",
            data=output.getvalue(),
            file_name=f"Shu_Report_{datetime.datetime.now().strftime('%m%d_%H%M')}.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True
        )
