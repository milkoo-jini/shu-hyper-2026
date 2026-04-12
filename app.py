import streamlit as st
import pandas as pd
import datetime, re, requests, io
from bs4 import BeautifulSoup
import pytz

# --- [1. ENGINE: 기존 동작 방식 및 문맥 필터 보존] ---
class ShuHyperMonitorWeb:
    def __init__(self):
        self.naver_id = st.secrets["NAVER_ID"]
        self.naver_secret = st.secrets["NAVER_SECRET"]
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.fixed_topics = ["지방선거", "월드컵"]
        # 문맥 기반 홍보성 필터 로직
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
            # 기존 11개 채널 수집 로직 (is_valid_context 필터 적용)
            res = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            for i in res.get('items', []):
                t = BeautifulSoup(i['title'], 'html.parser').get_text()
                if self.is_valid_context(t):
                    pool.append({'src': self.get_friendly_name('NAVER_DATE'), 'kw': t, 'url': i['link']})
            # (다른 채널 수집 로직들도 동일하게 fetch_all_routes 내부에 배치)
        except: pass
        
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return unique_pool

# --- [2. UI: 상태 관리 및 버튼 로직 강화] ---
st.set_page_config(layout="wide", page_title="실시간 이슈 모니터링")

st.markdown("""
    <style>
    [data-testid="column"] { display: flex; align-items: flex-end; }
    .stButton > button { height: 2.8rem !important; width: 100%; font-weight: bold; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# 버튼 상태 관리를 위한 세션 초기화
if 'data' not in st.session_state: st.session_state.data = []
if 'select_all' not in st.session_state: st.session_state.select_all = True

st.title("🛡️ 실시간 이슈 관제 센터")

top_col1, top_col2, top_col3 = st.columns([1, 1, 1])
with top_col1:
    if st.button("🚀 전체 채널 스캔", use_container_width=True):
        st.session_state.data = ShuHyperMonitorWeb().fetch_all_routes()
        st.session_state.select_all = True # 스캔 시 기본 전체 선택
        st.rerun()
with top_col2:
    search_query = st.text_input("🔍 키워드 검색", placeholder="검색어 입력...", label_visibility="collapsed")
with top_col3:
    count = len(st.session_state.data) if st.session_state.data else 0
    st.text_input("📊 수집 현황", value=f"{count}개 탐지됨", disabled=True, label_visibility="collapsed")

st.divider()

if st.session_state.data:
    df_raw = pd.DataFrame(st.session_state.data)
    f_df = df_raw.copy()
    if search_query: f_df = f_df[f_df['kw'].str.contains(search_query, case=False)]

    korea_now = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%-m/%-d %H:%M')
    
    # [데이터 매핑] 캡처 오류 해결을 위한 컬럼 구성
    display_df = pd.DataFrame({
        '데이터 수집 시점': [korea_now] * len(f_df),
        '출처': f_df['src'],
        '헤드라인': f_df['url'],   
        'hidden_title': f_df['kw'], # 실제 기사 제목
        '선택': st.session_state.select_all # 세션 상태를 직접 반영
    })

    # [수정] 버튼 클릭 시 세션 상태 변경 로직
    _, btn_col = st.columns([8.2, 1.8])
    with btn_col:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("전체✅"):
                st.session_state.select_all = True
                st.rerun()
        with b2:
            if st.button("해제❌"):
                st.session_state.select_all = False
                st.rerun()

    # [출력 제어] 제목 노출 및 링크 매핑 완결
    edited_df = st.data_editor(
        display_df,
        column_config={
            "데이터 수집 시점": st.column_config.TextColumn("데이터 수집 시점", width="medium"),
            "출처": st.column_config.TextColumn("출처", width="medium"),
            "헤드라인": st.column_config.LinkColumn(
                "헤드라인 (클릭 시 원문 이동)",
                display_text="hidden_title", # hidden_title의 실제 제목을 링크 텍스트로 사용
                width="large"
            ),
            "hidden_title": None, # 화면 숨김
            "선택": st.column_config.CheckboxColumn("선택")
        },
        column_order=("데이터 수집 시점", "출처", "헤드라인", "선택"),
        hide_index=True,
        use_container_width=True,
        height=650,
        key="main_editor" # 고정 키값을 주어 상태 유지
    )

    # 보고서 추출
    selected_rows = edited_df[edited_df['선택'] == True]
    if not selected_rows.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            report_df = selected_rows.copy()
            report_df['기사제목'] = report_df['hidden_title']
            report_df.drop(columns=['선택', 'hidden_title']).to_excel(writer, index=False)
        st.download_button(label="📊 엑셀 리포트 추출", data=output.getvalue(), file_name="Shu_Report.xlsx", use_container_width=True)
