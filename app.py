import streamlit as st
import pandas as pd
import datetime, re, time, requests
from bs4 import BeautifulSoup
import pytz  # 한국 시간 설정을 위해 추가

# --- [1. SHU HYPER ENGINE: 로직 무결성 유지] ---
class ShuHyperMonitorWeb:
    def __init__(self):
        self.naver_id = st.secrets["NAVER_ID"]
        self.naver_secret = st.secrets["NAVER_SECRET"]
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.fixed_topics = ["북중미 월드컵", "2026 지방선거"]
        self.risk_keywords = ["논란", "비판", "폭로", "의혹", "사기", "피해", "수사", "연패", "경질", "공천", "중계권", "충격", "속보"]
        self.exclude_ad_keywords = ["[Who Is ?]", "인물열전", "CEO스토리", "기업인사", "조언", "상담", "변호사", "법무법인", "선임", "전문가", "무료상담", "승소", "법률사무소", "홍보", "마케팅"]
        # 한국 시간대 설정
        self.korea_tz = pytz.timezone('Asia/Seoul')

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        try:
            # 11개 채널 수집 (형님 로직)
            n_sim = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=15&sort=sim", headers=h).json()
            pool.extend([{'src': 'NAVER(정확)', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text()} for i in n_sim.get('items', [])])
            n_date = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            pool.extend([{'src': 'NAVER(최신)', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text()} for i in n_date.get('items', [])])
            for t in self.fixed_topics:
                t_n = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=20&sort=date", headers=h).json()
                pool.extend([{'src': f'FIXED({t})', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text()} for i in t_n.get('items', [])])
            
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            pool.extend([{'src': 'SIGNAL', 'kw': i['keyword']} for i in sig.get('top10', [])])
            nate = requests.get("https://news.nate.com/edit/issueup/", headers=self.headers)
            pool.extend([{'src': 'NATE', 'kw': a.text.strip()} for a in BeautifulSoup(nate.text, 'html.parser').select('.txt_tit')[:10]])
            zum = requests.get("https://zum.com/#!/home", headers=self.headers)
            pool.extend([{'src': 'ZUM', 'kw': a.text.strip()} for a in BeautifulSoup(zum.text, 'html.parser').select('.issue_keyword .txt')[:10]])
            g_trends = requests.get("https://trends.google.com/trending/rss?geo=KR", headers=self.headers)
            pool.extend([{'src': 'G-TRENDS', 'kw': i.title.text} for i in BeautifulSoup(g_trends.text, 'xml').find_all('item')[:10]])
            d_res = requests.get("https://news.daum.net/ranking/popular", headers=self.headers)
            pool.extend([{'src': 'DAUM', 'kw': a.text.strip()} for a in BeautifulSoup(d_res.text, 'html.parser').select('.link_txt')[:30]])
            g_news = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", headers=self.headers)
            pool.extend([{'src': 'G-NEWS', 'kw': i.title.text} for i in BeautifulSoup(g_news.text, 'xml').find_all('item')[:15]])
            fm = requests.get("https://www.fmkorea.com/best", headers=self.headers)
            pool.extend([{'src': 'FMKOREA', 'kw': a.get_text().strip()} for a in BeautifulSoup(fm.text, 'html.parser').select('.title.hotdeal_var8 a')[:20]])
            dc = requests.get("https://www.dcinside.com/", headers=self.headers)
            pool.extend([{'src': 'DCINSIDE', 'kw': a.get_text().strip()} for a in BeautifulSoup(dc.text, 'html.parser').select('.box_best .list_best li a')[:15]])
        except: pass

        seen, unique_pool = set(), []
        for item in pool:
            skeleton = re.sub(r'\s+', '', item['kw'])
            if skeleton not in seen:
                seen.add(skeleton)
                unique_pool.append(item)
        return unique_pool

    def run_engine(self):
        final_list = []
        raw_data = self.fetch_all_routes()
        # 현재 한국 시간 생성
        now_korea = datetime.datetime.now(self.korea_tz)
        current_time_str = now_korea.strftime('%m/%d %H:%M')

        for item in raw_data:
            if any(ad in item['kw'] for ad in self.exclude_ad_keywords): continue
            is_risk = any(rk in item['kw'] for rk in self.risk_keywords)
            is_fixed = any(topic in item['kw'] for topic in self.fixed_topics)

            if is_risk or is_fixed:
                final_list.append({
                    'TIME': current_time_str,
                    'TYPE': 'FIXED' if is_fixed else 'RISK', # FIXED 우선 분류
                    'SOURCE': item['src'],
                    'HEADLINE': item['kw']
                })
        
        if final_list:
            # 1순위: TYPE(FIXED가 RISK보다 사전순으로 앞이라 위로 올라감), 2순위: 원래 순서 유지
            df = pd.DataFrame(final_list)
            df = df.sort_values(by=['TYPE'], ascending=True).reset_index(drop=True)
            
            fname = f"Shu_Hyper_Report_{now_korea.strftime('%m%d_%H%M')}.xlsx"
            df.to_excel(fname, index=False)
            return df.to_dict('records'), fname
        return [], None

# --- [2. UI 설정: 아이케어 필터링 대시보드] ---
st.set_page_config(layout="wide", page_title="실시간 이슈 모니터링")

st.markdown("""
    <style>
    .stApp { background-color: #f1f3f5; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #1c7ed6; color: white; font-weight: bold; }
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ 실시간 이슈 모니터링")
st.markdown("<p style='color:#495057; font-size:18px; margin-top:-15px;'>Risk Control Center</p>", unsafe_allow_html=True)

if 'results' not in st.session_state: st.session_state.update({'results': [], 'fname': ""})

# [핵심] 상단 컨트롤 레이아웃: 버튼 + 필터
c1, c2, c3 = st.columns([2, 2, 1])

with c1:
    if st.button("🚀 SCAN START"):
        engine = ShuHyperMonitorWeb()
        with st.spinner("분석 중..."):
            res, name = engine.run_engine()
            st.session_state['results'], st.session_state['fname'] = res, name
            st.rerun()

with c2:
    sources = ["전체 채널"] + list(set([d['SOURCE'] for d in st.session_state['results']])) if st.session_state['results'] else ["데이터 없음"]
    selected_source = st.selectbox("🎯 채널별로 보기", sources)

with c3:
    types = ["전체 유형"] + list(set([d['TYPE'] for d in st.session_state['results']])) if st.session_state['results'] else ["데이터 없음"]
    selected_type = st.selectbox("📂 유형별로 보기", types)

st.divider()

# 데이터 필터링 및 출력
if st.session_state['results']:
    df = pd.DataFrame(st.session_state['results'])
    
    # 필터 적용 로직
    filtered_df = df.copy()
    if selected_source != "전체 채널":
        filtered_df = filtered_df[filtered_df['SOURCE'] == selected_source]
    if selected_type != "전체 유형":
        filtered_df = filtered_df[filtered_df['TYPE'] == selected_type]

    st.subheader(f"📋 관제 리스트 ({len(filtered_df)}건)")
    st.dataframe(
        filtered_df,
        column_config={
            "TIME": st.column_config.TextColumn("시각", width="small"),
            "TYPE": st.column_config.TextColumn("분류", width="small"),
            "SOURCE": st.column_config.TextColumn("출처", width="medium"),
            "HEADLINE": st.column_config.TextColumn("헤드라인", width="large"),
        },
        use_container_width=True,
        height=700,
        hide_index=True
    )
