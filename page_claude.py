import streamlit as st
import pandas as pd
import datetime, re, requests, io, time
import urllib.parse
from bs4 import BeautifulSoup
import pytz
import os
import email.utils

# ==========================================
# 1. 슈 님 원본 엔진 (분석 철학 및 5대 기준 완벽 보존)
# ==========================================
class MasterGuardian_Smart_Claude:
    def __init__(self):
        try:
            self.naver_id = st.secrets["NAVER_ID"]
            self.naver_secret = st.secrets["NAVER_SECRET"]
        except:
            self.naver_id = self.naver_secret = None

        self.kst = pytz.timezone('Asia/Seoul')
        self.answer_data = self.load_txt_file('정답기사리스트.txt')
        self.wrong_data = self.load_txt_file('오답기사리스트.txt')
        self.risk_vocab = self.build_vocab(self.answer_data)
        self.noise_vocab = self.build_vocab(self.wrong_data)
        self.time_limit = 86400 # 24시간 제한

    def load_txt_file(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        return []

    def build_vocab(self, data_list):
        vocab = set()
        for title in data_list:
            words = re.findall(r'[가-힣0-9]{2,}', title)
            vocab.update(words)
        return vocab

    def is_within_time(self, pub_date):
        try:
            pub_time = email.utils.parsedate_to_datetime(pub_date).timestamp()
            return (time.time() - pub_time) <= self.time_limit
        except:
            return True

    def is_risk_context(self, title):
        """
        슈 님의 5대 리스크 철학 반영 로직
        """
        current_words = set(re.findall(r'[가-힣0-9]{2,}', title))
        
        # [철학] 오답 기사 제외 (3개 이상 중복 시)
        if len(current_words & self.noise_vocab) >= 3: 
            return False
            
        # [철학] 5대 기준 포괄적 키워드 (분야 상관없이 본질 포착)
        risk_standards = [
            '사칭', '허위', '딥페이크', '기만', '속여', '조작', '가짜', '도용',
            '유출', '협박', '스토킹', '먹튀', '폐업', '피해', '탈취', '보복',
            '마약', '짝퉁', '가품', '도박', '착취', '불법', '밀수',
            '비리', '부패', '위반', '해킹', '침해', '피소', '혐의', '구속',
            '악용', '취약점', '비정상', '수법', '사각지대', '우회'
        ]
        if any(sw in title for sw in risk_standards):
            return True

        # [철학] 정답 사례와 맥락 유사 시 포착 (2개 이상 중복)
        if len(current_words & self.risk_vocab) >= 2:
            return True
            
        return False

    def search_naver_news(self, keyword):
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        url = f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(keyword)}&display=50&sort=date"
        try:
            res = requests.get(url, headers=h, timeout=5)
            return res.json().get('items', [])
        except: return []

# ==========================================
# 2. UI 컴포넌트 (오류 해결 버전)
# ==========================================
def render_table(df, editor_key):
    return st.data_editor(
        df,
        column_config={
            "수집시점": st.column_config.TextColumn("시간", width=120),
            "src": st.column_config.TextColumn("출처", width=150),
            "kw": st.column_config.TextColumn("이슈 헤드라인 전문"),
            "url": st.column_config.LinkColumn(" ", display_text="🔗", width=60),
            "선택": st.column_config.CheckboxColumn(" ", width=60),
        },
        column_order=("수집시점", "src", "kw", "url", "선택"),
        hide_index=True, use_container_width=True, height=800,
        key=editor_key
    )

def run_claude_collector():
    # [수정] TypeError 방지를 위해 icon 파라미터 제거 후 텍스트로 합침
    st.markdown("### 🤖 클로드 분석용 언론 수집")
    st.caption("AI 분석용 로우 데이터 가공")

    if 'claude_pool' not in st.session_state: st.session_state.claude_pool = []
    if 'claude_key' not in st.session_state: st.session_state.claude_key = 0
    if 'is_collecting' not in st.session_state: st.session_state.is_collecting = False
    if 'stop_flag' not in st.session_state: st.session_state.stop_flag = False

    # 컨트롤 바
    c1, c2, c3, c4, c5 = st.columns([1.5, 2, 0.5, 0.5, 0.5])
    with c1:
        if st.button("🚀 로우 데이터 수집 시작", use_container_width=True):
            st.session_state.is_collecting = True
            st.session_state.stop_flag = False
            st.rerun()
    with c2:
        search_query = st.text_input("", placeholder="🔍 결과 내 키워드 검색", label_visibility="collapsed")
    with c3:
        st.markdown(f"<div class='status-badge'>{len(st.session_state.claude_pool)}건</div>", unsafe_allow_html=True)
    with c4:
        if st.button("전체선택", use_container_width=True):
            for i in st.session_state.claude_pool: i['선택'] = True
            st.session_state.claude_key += 1; st.rerun()
    with c5:
        if st.button("선택해제", use_container_width=True):
            for i in st.session_state.claude_pool: i['선택'] = False
            st.session_state.claude_key += 1; st.rerun()

    # 모래시계(Spinner)
    spinner_placeholder = st.empty()

    if st.session_state.is_collecting:
        with spinner_placeholder.container():
            with st.spinner("⏳ 5대 리스크 기준 대조 및 수집 중..."):
                engine = MasterGuardian_Smart_Claude()
                if os.path.exists('언론키워드셋.txt'):
                    with open('언론키워드셋.txt', 'r', encoding='utf-8') as f:
                        keywords = [l.strip() for l in f if l.strip()]
                    
                    results = []
                    for kw in keywords:
                        # 사이드바 stop_flag 체크 로직 (보존)
                        if st.session_state.get('stop_flag', False):
                            st.warning("분석이 사용자에 의해 중단되었습니다.")
                            break
                        
                        items = engine.search_naver_news(kw)
                        for i in items:
                            if engine.is_within_time(i.get('pubDate', '')):
                                title = BeautifulSoup(i['title'], 'html.parser').get_text()
                                if engine.is_risk_context(title):
                                    results.append({'src': kw, 'kw': title, 'url': i['link'], '선택': True})
                    
                    st.session_state.claude_pool = results
                    st.session_state.claude_key += 1
                
                st.session_state.is_collecting = False
                spinner_placeholder.empty()
                st.rerun()

    st.markdown("---")
    
    if st.session_state.claude_pool:
        df = pd.DataFrame(st.session_state.claude_pool)
        if search_query:
            df = df[df['kw'].str.contains(search_query, case=False, na=False)]
            
        df['수집시점'] = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m/%d %H:%M')
        edited = render_table(df, f"table_{st.session_state.claude_key}")

        sel = edited[edited['선택'] == True]
        if not sel.empty:
            t1, t2 = st.columns(2)
            with t1:
                txt = "\n".join(sel['kw'].tolist())
                st.download_button("📄 클로드용 TXT 다운로드", txt.encode('utf-8'), "Claude_Raw.txt", use_container_width=True)
                st.text_area("텍스트 복사", value=txt, height=200)
            with t2:
                out = io.BytesIO()
                sel.drop(columns=['선택']).to_excel(out, index=False, engine='openpyxl')
                st.download_button("📊 엑셀 백업 다운로드", out.getvalue(), "Risk_Backup.xlsx", use_container_width=True)
