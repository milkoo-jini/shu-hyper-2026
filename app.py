import streamlit as st
import pandas as pd
import datetime, re, requests, io
from bs4 import BeautifulSoup
import pytz

# --- [1. ENGINE: 11개 채널 수집 로직 완벽 복구] ---
class ShuHyperMonitorWeb:
    def __init__(self):
        self.naver_id = st.secrets["NAVER_ID"]
        self.naver_secret = st.secrets["NAVER_SECRET"]
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.fixed_topics = ["지방선거", "월드컵"]
        # 문맥 기반 홍보성 필터
        self.ad_context_patterns = [
            r"\[.*(공개|이벤트|특가|판매).*\]", 
            r"\d+% (할인|적립|증정)",            
            r"(지금|바로|확인|클릭|가기)하세요",    
            r"(최저가|압도적|독보적|최대 규모)",     
            r"신규 (회원|가입|출시|오픈)"          
        ]

    def is_valid_context(self, text):
        for pattern in self.ad_context_patterns:
            if re.search(pattern, text): return False
        return True

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        
        try:
            # 1~2. 고정 주제 관제
            for t in self.fixed_topics:
                res = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=20&sort=date", headers=h).json()
                for i in res.get('items', []):
                    title = BeautifulSoup(i['title'], 'html.parser').get_text()
                    if self.is_valid_context(title):
                        pool.append({'src': f'📍 고정({t})', 'kw': title, 'url': i['link']})

            # 3~4. 네이버 실시간/주요 이슈
            for mode, src_name in [('date', '⏱️ 실시간 뉴스'), ('sim', '📢 주요 이슈(네이버)')]:
                res = requests.get(f"https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=30&sort={mode}", headers=h).json()
                for i in res.get('items', []):
                    title = BeautifulSoup(i['title'], 'html.parser').get_text()
                    if self.is_valid_context(title):
                        pool.append({'src': src_name, 'kw': title, 'url': i['link']})

            # 5. 급상승 시그널
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            for i in sig.get('top10', []):
                if self.is_valid_context(i['keyword']):
                    pool.append({'src': '📈 급상승 시그널', 'kw': i['keyword'], 'url': f"https://search.naver.com/search.naver?query={i['keyword']}"})

            # 6. 구글 트렌드
            g_trends = requests.get("https://trends.google.com/trending/rss?geo=KR", headers=self.headers)
            for i in BeautifulSoup(g_trends.text, 'xml').find_all('item')[:10]:
                title = i.title.text
                if self.is_valid_context(title):
                    pool.append({'src': '🌐 구글 트렌드', 'kw': title, 'url': f"https://www.google.com/search?q={title}&tbm=nws"})

            # 7. 구글 뉴스
            g_news = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", headers=self.headers)
            for i in BeautifulSoup(g_news.text, 'xml').find_all('item')[:15]:
                if self.is_valid_context(i.title.text):
                    pool.append({'src': '📰 구글 뉴스', 'kw': i.title.text, 'url': i.link.text})

            # 8. 다음 인기
            daum = requests.get("https://news.daum.net/ranking/popular", headers=self.headers)
            for a in BeautifulSoup(daum.text, 'html.parser').select('.link_txt')[:20]:
                title = a.text.strip()
                if self.is_valid_context(title):
                    pool.append({'src': '🟠 다음 인기', 'kw': title, 'url': a['href']})

            # 9. 네이트 이슈
            nate = requests.get("https://news.nate.com/edit/issueup/", headers=self.headers)
            for a in BeautifulSoup(nate.text, 'html.parser').select('.txt_tit')[:10]:
                title = a.text.strip()
                if self.is_valid_context(title):
                    pool.append({'src': '🔴 네이트 이슈', 'kw': title, 'url': 'https://news.nate.com'+a['href']})

            # 10. 줌 실검
            zum = requests.get("https://zum.com/#!/home", headers=self.headers)
            for a in BeautifulSoup(zum.text, 'html.parser').select('.issue_keyword .txt')[:10]:
                title = a.text.strip()
                if self.is_valid_context(title):
                    pool.append({'src': '🔵 줌 실검', 'kw': title, 'url': f"https://search.zum.com/search.zum?query={title}"})

            # 11. 커뮤니티 베스트 (FM코리아)
            fm = requests.get("https://www.fmkorea.com/best", headers=self.headers)
            for a in BeautifulSoup(fm.text, 'html.parser').select('.title.hotdeal_var8 a')[:15]:
                title = a.get_text().strip()
                if self.is_valid_context(title):
                    pool.append({'src': '⚽ 에펨코리아', 'kw': title, 'url': 'https://www.fmkorea.com'+a['href']})

        except Exception as e:
            st.error(f"수집 중 오류 발생: {e}")

        # 중복 제거
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return unique_pool

# --- [2. UI: 상태 관리 및 제목 매핑 무결성] ---
st.set_page_config(layout="wide", page_title="실시간 이슈 모니터링")

st.markdown("""
    <style>
    [data-testid="column"] { display: flex; align-items: flex-end; }
    .stButton > button { height: 2.8rem !important; width: 100%; font-weight: bold; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

if 'data_pool' not in st.session_state: st.session_state.data_pool = []
if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

# 큰제목 원복
st.title("🛡️ 실시간 이슈 관제 센터")

top_col1, top_col2, top_col3 = st.columns([1, 1, 1])
with top_col1:
    if st.button("🚀 전체 채널 스캔", use_container_width=True):
        raw_data = ShuHyperMonitorWeb().fetch_all_routes()
        st.session_state.data_pool = [dict(d, 선택=True) for d in raw_data]
        st.session_state.editor_key += 1
        st.rerun()
with top_col2:
    search_query = st.text_input("🔍 키워드 검색", placeholder="검색어 입력...", label_visibility="collapsed")
with top_col3:
    count = len(st.session_state.data_pool)
    st.text_input("📊 수집 현황", value=f"{count}개 탐지됨", disabled=True, label_visibility="collapsed")

st.divider()

if st.session_state.data_pool:
    df = pd.DataFrame(st.session_state.data_pool)
    if search_query:
        df = df[df['kw'].str.contains(search_query, case=False)]

    korea_now = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%-m/%-d %H:%M')
    df['데이터 수집 시점'] = korea_now

    # 전체 선택/해제 버튼 (세션 데이터 직접 제어)
    _, btn_col = st.columns([8.2, 1.8])
    with btn_col:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("전체✅"):
                for item in st.session_state.data_pool: item['선택'] = True
                st.session_state.editor_key += 1; st.rerun()
        with b2:
            if st.button("해제❌"):
                for item in st.session_state.data_pool: item['선택'] = False
                st.session_state.editor_key += 1; st.rerun()

    # [최종 해결] 제목 전문 노출 및 링크 무결성 보장
    # '뉴스 제목' 컬럼을 별도로 두고, '원문' 컬럼에 링크를 배치하여 캡처의 오류를 원천 차단합니다.
    edited_df = st.data_editor(
        df,
        column_config={
            "데이터 수집 시점": st.column_config.TextColumn("데이터 수집 시점", width="small"),
            "src": st.column_config.TextColumn("출처", width="small"),
            "kw": st.column_config.TextColumn("이슈 헤드라인 전문", width="large"), # 제목 전문 노출
            "url": st.column_config.LinkColumn("원문 링크", display_text="🔗 이동", width="small"), # 링크 분리
            "선택": st.column_config.CheckboxColumn("선택")
        },
        column_order=("데이터 수집 시점", "src", "kw", "url", "선택"),
        hide_index=True,
        use_container_width=True,
        key=f"editor_{st.session_state.editor_key}"
    )

    # 보고서 추출
    selected_rows = edited_df[edited_df['선택'] == True]
    if not selected_rows.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            selected_rows.drop(columns=['선택']).to_excel(writer, index=False)
        st.download_button(label="📊 엑셀 리포트 추출", data=output.getvalue(), file_name="Shu_Report.xlsx", use_container_width=True)
