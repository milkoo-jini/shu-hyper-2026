import streamlit as st
import pandas as pd
import datetime, re, time, requests, io
from bs4 import BeautifulSoup
import pytz

# --- [1. SHU HYPER ENGINE: 필터 및 11개 채널 로직] ---
class ShuHyperMonitorWeb:
    def __init__(self):
        # 인증 및 기본 설정
        self.naver_id = st.secrets["NAVER_ID"]
        self.naver_secret = st.secrets["NAVER_SECRET"]
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # [고정] 관제 주제
        self.fixed_topics = ["지방선거", "월드컵"]
        
        # [핵심] 리스크 및 광고 제외 키워드 (맥락 차단용)
        self.risk_keywords = ["논란", "비판", "폭로", "의혹", "사기", "피해", "수사", "연패", "경질", "공천", "중계권", "충격", "속보"]
        self.exclude_ad_keywords = ["변호사", "법무법인", "무료상담", "승소", "마케팅", "홍보", "기고", "출시", "특가", "이벤트", "증정"]
        
        self.korea_tz = pytz.timezone('Asia/Seoul')

    def is_valid_issue(self, text):
        """단순 단어 매칭을 넘어 홍보성 노이즈를 수집 단계에서 차단"""
        if any(ad_kw in text for ad_kw in self.exclude_ad_keywords):
            return False
        return True

    def get_friendly_name(self, raw_src):
        """슈 님이 지정하신 11개 채널 한글 명칭 매핑"""
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
            # 1~2. 고정 주제
            for t in self.fixed_topics:
                t_n = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=20&sort=date", headers=h).json()
                for i in t_n.get('items', []):
                    title = BeautifulSoup(i['title'], 'html.parser').get_text()
                    if self.is_valid_issue(title):
                        pool.append({'src': f'📍 고정관제({t})', 'kw': title, 'url': i['link']})

            # 3~4. 네이버 뉴스 (실시간/주요)
            for mode, key in [('date', 'NAVER_DATE'), ('sim', 'NAVER_SIM')]:
                res = requests.get(f"https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=30&sort={mode}", headers=h).json()
                for i in res.get('items', []):
                    title = BeautifulSoup(i['title'], 'html.parser').get_text()
                    if self.is_valid_issue(title):
                        pool.append({'src': self.get_friendly_name(key), 'kw': title, 'url': i['link']})

            # 5. 급상승 시그널
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            for i in sig.get('top10', []):
                if self.is_valid_issue(i['keyword']):
                    pool.append({'src': self.get_friendly_name('SIGNAL'), 'kw': i['keyword'], 'url': f"https://search.naver.com/search.naver?query={i['keyword']}"})

            # 6. 구글 트렌드
            g_trends = requests.get("https://trends.google.com/trending/rss?geo=KR", headers=self.headers)
            for i in BeautifulSoup(g_trends.text, 'xml').find_all('item')[:10]:
                if self.is_valid_issue(i.title.text):
                    pool.append({'src': self.get_friendly_name('G_TRENDS'), 'kw': i.title.text, 'url': f"https://www.google.com/search?q={i.title.text}&tbm=nws"})

            # 7. 구글 뉴스
            g_news = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", headers=self.headers)
            for i in BeautifulSoup(g_news.text, 'xml').find_all('item')[:15]:
                if self.is_valid_issue(i.title.text):
                    pool.append({'src': self.get_friendly_name('G_NEWS'), 'kw': i.title.text, 'url': i.link.text})

            # 8. 다음 인기
            daum = requests.get("https://news.daum.net/ranking/popular", headers=self.headers)
            for a in BeautifulSoup(daum.text, 'html.parser').select('.link_txt')[:20]:
                if self.is_valid_issue(a.text):
                    pool.append({'src': self.get_friendly_name('DAUM'), 'kw': a.text.strip(), 'url': a['href']})

            # 9. 네이트 이슈
            nate = requests.get("https://news.nate.com/edit/issueup/", headers=self.headers)
            for a in BeautifulSoup(nate.text, 'html.parser').select('.txt_tit')[:10]:
                if self.is_valid_issue(a.text):
                    pool.append({'src': self.get_friendly_name('NATE'), 'kw': a.text.strip(), 'url': 'https://news.nate.com'+a['href']})

            # 10. 줌 실검
            zum = requests.get("https://zum.com/#!/home", headers=self.headers)
            for a in BeautifulSoup(zum.text, 'html.parser').select('.issue_keyword .txt')[:10]:
                if self.is_valid_issue(a.text):
                    pool.append({'src': self.get_friendly_name('ZUM'), 'kw': a.text.strip(), 'url': f"https://search.zum.com/search.zum?query={a.text.strip()}"})

            # 11. 커뮤니티 (FM코리아/디시)
            fm = requests.get("https://www.fmkorea.com/best", headers=self.headers)
            for a in BeautifulSoup(fm.text, 'html.parser').select('.title.hotdeal_var8 a')[:15]:
                if self.is_valid_issue(a.text):
                    pool.append({'src': self.get_friendly_name('FMKOREA'), 'kw': a.get_text().strip(), 'url': 'https://www.fmkorea.com'+a['href']})
            
            dc = requests.get("https://www.dcinside.com/", headers=self.headers)
            for a in BeautifulSoup(dc.text, 'html.parser').select('.box_best .list_best li a')[:10]:
                if self.is_valid_issue(a.text):
                    pool.append({'src': self.get_friendly_name('DCINSIDE'), 'kw': a.get_text().strip(), 'url': a['href']})

        except: pass

        # 중복 제거 (공백 제거 기준)
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return unique_pool

# --- [2. UI 및 표시 형식] ---
st.set_page_config(layout="wide", page_title="실시간 이슈 모니터링")

# 상단 레이아웃 및 버튼 높이 조정
st.markdown("""
    <style>
    [data-testid="column"] { display: flex; align-items: flex-end; }
    .stButton > button { height: 2.8rem !important; width: 100%; font-weight: bold; }
    div[data-baseweb="input"] { height: 2.8rem !important; }
    </style>
    """, unsafe_allow_html=True)

if 'data' not in st.session_state: st.session_state.data = []
if 'select_all' not in st.session_state: st.session_state.select_all = True

st.title("🛡️ 실시간 이슈 관제 센터")

# 상단 메뉴 1:1:1 균형 정렬
top_col1, top_col2, top_col3 = st.columns([1, 1, 1])
with top_col1:
    if st.button("🚀 전체 채널 스캔", use_container_width=True):
        st.session_state.data = ShuHyperMonitorWeb().fetch_all_routes()
        st.session_state.select_all = True
        st.rerun()
with top_col2:
    search_query = st.text_input("🔍 키워드 검색", placeholder="조사할 키워드 입력...", label_visibility="collapsed")
with top_col3:
    count = len(st.session_state.data) if st.session_state.data else 0
    st.text_input("📊 수집 현황", value=f"{count}개 이슈 탐지 (광고/노이즈 필터 가동 중)", disabled=True, label_visibility="collapsed")

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

    # 필터링
    f_df = df_raw.copy()
    if search_query: f_df = f_df[f_df['kw'].str.contains(search_query, case=False)]

    # 시각 형식 (M/D HH:MM)
    f_time = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%-m/%-d %H:%M')
    
    # 데이터 프레임 구성
    display_df = pd.DataFrame({
        '시각': [f_time] * len(f_df),
        '출처': f_df['src'],
        '헤드라인': f_df['url'],   # 실제 URL
        '제목_원본': f_df['kw'],   # 표시될 제목
        '선택': st.session_state.select_all
    })

    # 전체 선택/해제 (우측 정렬)
    _, btn_col = st.columns([8.2, 1.8])
    with btn_col:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("전체✅"):
                st.session_state.select_all = True; st.rerun()
        with b2:
            if st.button("해제❌"):
                st.session_state.select_all = False; st.rerun()

    # [수정] 데이터 에디터: 제목 노출 오류 완벽 차단
    edited_df = st.data_editor(
        display_df,
        column_config={
            "시각": st.column_config.TextColumn("시각", width="medium"),
            "출처": st.column_config.TextColumn("출처", width="medium"),
            "헤드라인": st.column_config.LinkColumn(
                "헤드라인 (클릭 시 이동)", 
                display_text="제목_원본", # 참조 컬럼명을 직접 지정하여 오표기 방지
                width="large"
            ),
            "제목_원본": None, # 화면 숨김
            "선택": st.column_config.CheckboxColumn("조치")
        },
        column_order=("시각", "출처", "헤드라인", "선택"),
        hide_index=True,
        use_container_width=True,
        height=600,
        key="shu_hyper_v15_final"
    )

    # 리포트 추출
    selected_rows = edited_df[edited_df['선택'] == True]
    if not selected_rows.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            selected_rows.drop(columns=['선택', '제목_원본']).to_excel(writer, index=False)
        st.download_button(label="📊 엑셀 리포트 추출", data=output.getvalue(), file_name="Shu_Report.xlsx", use_container_width=True)
