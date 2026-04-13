import streamlit as st
import pandas as pd
import datetime, re, requests, io
from bs4 import BeautifulSoup
import pytz

class ShuMonitorEngine:
    def __init__(self):
        try:
            self.naver_id = st.secrets["NAVER_ID"]
            self.naver_secret = st.secrets["NAVER_SECRET"]
        except:
            self.naver_id = self.naver_secret = None
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        # 진짜 고정 주제 2개
        self.fixed_topics = ["월드컵", "지방선거"]
        
        # [확정] 슈 님 지정 출처 명칭 10선
        self.src_mapping = {
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

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        try:
            # 1. 네이버 (SIM/DATE)
            n_sim = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=15&sort=sim", headers=h).json()
            pool.extend([{'src': self.src_mapping['NAVER_SIM'], 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in n_sim.get('items', [])])
            
            n_date = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            pool.extend([{'src': self.src_mapping['NAVER_DATE'], 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in n_date.get('items', [])])
            
            # 2. 고정 주제
            for t in self.fixed_topics:
                t_n = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=25&sort=date", headers=h).json()
                pool.extend([{'src': f'🔥 {t}', 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'url': i['link']} for i in t_n.get('items', [])])
            
            # 3. 시그널
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            pool.extend([{'src': self.src_mapping['SIGNAL'], 'kw': i['keyword'], 'url': f"https://search.naver.com/search.naver?query={i['keyword']}"} for i in sig.get('top10', [])])
            
            # 4. 네이트
            nate = requests.get("https://news.nate.com/edit/issueup/", headers=self.headers)
            pool.extend([{'src': self.src_mapping['NATE'], 'kw': a.text.strip(), 'url': "https://news.nate.com/edit/issueup/"} for a in BeautifulSoup(nate.text, 'html.parser').select('.txt_tit')[:10]])
            
            # 5. 줌
            zum = requests.get("https://zum.com/#!/home", headers=self.headers)
            pool.extend([{'src': self.src_mapping['ZUM'], 'kw': a.text.strip(), 'url': "https://zum.com/"} for a in BeautifulSoup(zum.text, 'html.parser').select('.issue_keyword .txt')[:10]])
            
            # 6. 구글 트렌드
            g_trends = requests.get("https://trends.google.com/trending/rss?geo=KR", headers=self.headers)
            pool.extend([{'src': self.src_mapping['G_TRENDS'], 'kw': i.title.text, 'url': i.link.text if i.link else ""} for i in BeautifulSoup(g_trends.text, 'xml').find_all('item')[:10]])
            
            # 7. 다음
            d_res = requests.get("https://news.daum.net/ranking/popular", headers=self.headers)
            pool.extend([{'src': self.src_mapping['DAUM'], 'kw': a.text.strip(), 'url': a.get('href')} for a in BeautifulSoup(d_res.text, 'html.parser').select('.link_txt')[:30]])
            
            # 8. 구글 뉴스
            g_news = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", headers=self.headers)
            pool.extend([{'src': self.src_mapping['G_NEWS'], 'kw': i.title.text, 'url': i.link.text} for i in BeautifulSoup(g_news.text, 'xml').find_all('item')[:15]])
            
            # 9. 에펨코리아
            fm = requests.get("https://www.fmkorea.com/best", headers=self.headers)
            pool.extend([{'src': self.src_mapping['FMKOREA'], 'kw': a.get_text().strip(), 'url': 'https://www.fmkorea.com' + a.get('href')} for a in BeautifulSoup(fm.text, 'html.parser').select('.title.hotdeal_var8 a')[:20]])
            
            # 10. 디시인사이드
            dc = requests.get("https://www.dcinside.com/", headers=self.headers)
            pool.extend([{'src': self.src_mapping['DCINSIDE'], 'kw': a.get_text().strip(), 'url': a.get('href')} for a in BeautifulSoup(dc.text, 'html.parser').select('.box_best .list_best li a')[:15]])

        except: pass
        
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return sorted(unique_pool, key=lambda x: 0 if '🔥' in x['src'] else 1)

# --- [UI: 정렬 및 규격 고정] ---
st.set_page_config(layout="wide", page_title="이슈 모니터링")
st.markdown("""<style>
    .block-container { padding-top: 1.5rem !important; }
    .stTextInput > div > div > input { height: 2.5rem !important; border-radius: 6px !important; }
    .stButton > button { height: 2.5rem !important; font-weight: 700 !important; border-radius: 6px !important; }
    .status-box { background-color: #f0f7ff; border: 1px solid #cce3ff; border-radius: 6px; padding: 0.55rem; text-align: center; color: #0056b3; font-weight: bold; height: 2.5rem; line-height: 1.4rem; }
    h3 { margin-top: -15px !important; margin-bottom: 15px !important; color: #1E3A8A; }
    #MainMenu, header {visibility: hidden;}
</style>""", unsafe_allow_html=True)

if 'data_pool' not in st.session_state: st.session_state.data_pool = []
if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

# 상단 1라인: 타이틀 및 핵심 컨트롤
c1, c2, c3, c4 = st.columns([2, 1, 1, 1.2])
with c1: st.markdown("### 🛡️ 실시간 이슈 모니터링")
with c2:
    if st.button("🚀 전체 채널 스캔", use_container_width=True):
        st.session_state.data_pool = [dict(d, 선택=True) for d in ShuMonitorEngine().fetch_all_routes()]
        st.session_state.editor_key += 1; st.rerun()
with c3: filter_query = st.text_input("", placeholder="🔍 결과 내 필터링", label_visibility="collapsed")
with c4:
    count = len(st.session_state.data_pool)
    st.markdown(f"<div class='status-box'>📊 {count}개 이슈 감지</div>", unsafe_allow_html=True)

# 상단 2라인: 전체선택/해제 (우측 정렬)
_, b1, b2 = st.columns([8.2, 0.9, 0.9])
with b1:
    if st.button("전체선택", use_container_width=True):
        for item in st.session_state.data_pool: item['선택'] = True
        st.session_state.editor_key += 1; st.rerun()
with b2:
    if st.button("선택해제", use_container_width=True):
        for item in st.session_state.data_pool: item['선택'] = False
        st.session_state.editor_key += 1; st.rerun()

# [중앙 데이터] 규격 85-65-65-65 엄수 및 수집시점 교정
if st.session_state.data_pool:
    df = pd.DataFrame(st.session_state.data_pool)
    if filter_query: df = df[df['kw'].str.contains(filter_query, case=False)]
    
    # [수정] 월/일 시:분 형식 고정 (예: 4/13 09:10)
    now = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
    df['수집시점'] = now.strftime('%-m/%-d %H:%M')

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
        hide_index=True, use_container_width=True, key=f"editor_{st.session_state.editor_key}"
    )

    if not edited_df[edited_df['선택'] == True].empty:
        output = io.BytesIO()
        edited_df[edited_df['선택'] == True].drop(columns=['선택']).to_excel(output, index=False)
        st.download_button(label="📊 엑셀 리포트 추출", data=output.getvalue(), file_name="Shu_Report.xlsx", use_container_width=True)
