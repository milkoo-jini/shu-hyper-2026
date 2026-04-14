import streamlit as st
import pandas as pd
import datetime, re, requests, io, time
import urllib.parse
from bs4 import BeautifulSoup
import pytz
import os
import email.utils

# ==========================================
# 1. 슈 님 원본 엔진 (분석 철학 및 5대 기준 완벽 반영)
# ==========================================
class MasterGuardian_Smart_Claude:
    def __init__(self):
        try:
            self.naver_id = st.secrets["NAVER_ID"]
            self.naver_secret = st.secrets["NAVER_SECRET"]
        except:
            self.naver_id = self.naver_secret = None

        self.kst = pytz.timezone('Asia/Seoul')
        
        # 메모장 데이터 로드 및 학습
        self.answer_data = self.load_txt_file('정답기사리스트.txt')
        self.wrong_data = self.load_txt_file('오답기사리스트.txt')
        self.risk_vocab = self.build_vocab(self.answer_data)
        self.noise_vocab = self.build_vocab(self.wrong_data)
        self.time_limit = 86400  # 24시간 제한

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
        """24시간 이내 기사인지 판별"""
        try:
            pub_time = email.utils.parsedate_to_datetime(pub_date).timestamp()
            return (time.time() - pub_time) <= self.time_limit
        except:
            return True

    def is_risk_context(self, title):
        """
        [슈 님의 분석 철학 및 5대 기준 적용 로직]
        """
        current_words = set(re.findall(r'[가-힣0-9]{2,}', title))
        
        # ⚠️ [오답만 제외] 단순 동정/홍보 뉴스 필터링 (3개 이상 중복 시)
        if len(current_words & self.noise_vocab) >= 3: 
            return False
            
        # ⚠️ [5대 리스크 기준 & 포괄적 해석] 카테고리 무관, 본질적 리스크 포착
        risk_standards = [
            # 1. 기만 및 사칭 (사용자를 속이는 행위)
            '사칭', '허위', '딥페이크', '기만', '속여', '조작', '가짜', '도용', '광고성',
            # 2. 이용자 피해 및 보복 (피해자 발생 본질)
            '유출', '협박', '스토킹', '먹튀', '폐업', '피해', '탈취', '보복', '갈취',
            # 3. 불법 유통 및 위반 (불법 행위)
            '마약', '짝퉁', '가품', '도박', '착취', '불법', '밀수', '음란', '성착취',
            # 4. 사회적 신뢰 훼손 (공공/기관 리스크)
            '비리', '부패', '위반', '해킹', '침해', '피소', '혐의', '구속', '수사', '징계',
            # 5. 신종 수법 및 사각지대 (비정상적 영업)
            '악용', '취약점', '비정상', '수법', '사각지대', '우회', '틈새', '변종'
        ]
        
        # ⚠️ [카테고리에 갇히지 마십시오] 분야 상관없이 키워드 매칭 시 즉시 포착
        if any(sw in title for sw in risk_standards):
            return True

        # ⚠️ [포괄적 해석] 정답 사례와 단어가 달라도 맥락 유사 시 포착 (2개 이상 중복)
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
# 2. UI 레이아웃 및 추출 로직
# ==========================================
def render_table(df, editor_key):
    return st.data_editor(
        df,
        column_config={
            "수집시점": st.column_config.TextColumn("시간", width=120),
            "src": st.column_config.TextColumn("출처/키워드", width=150),
            "kw": st.column_config.TextColumn("이슈 헤드라인 전문"),
            "url": st.column_config.LinkColumn(" ", display_text="🔗", width=60),
            "선택": st.column_config.CheckboxColumn(" ", width=60),
        },
        column_order=("수집시점", "src", "kw", "url", "선택"),
        hide_index=True, use_container_width=True, height=800,
        key=editor_key
    )

def run_claude_collector():
    st.markdown("### 🤖 클로드 분석용 언론 수집")
    st.caption("분석 철학에 기반하여 24시간 이내 리스크 데이터를 포괄적으로 수집합니다.")

    if 'claude_pool' not in st.session_state: st.session_state.claude_pool = []
    if 'claude_key' not in st.session_state: st.session_state.claude_key = 0
    if 'is_collecting' not in st.session_state: st.session_state.is_collecting = False

    # 상단 컨트롤 바 (검색 기능 통합)
    c1, c2, c3, c4, c5 = st.columns([1.5, 2, 0.5, 0.5, 0.5])
    with c1:
        if st.button("🚀 로우 데이터 수집 시작", use_container_width=True):
            st.session_state.is_collecting = True; st.rerun()
    with c2:
        # [추가된 기능] 결과 내 키워드 검색
        search_query = st.text_input("", placeholder="🔍 결과 내 키워드 검색", label_visibility="collapsed")
    with c3:
        st.markdown(f"<div class='status-badge'>{len(st.session_state.claude_pool)}건</div>", unsafe_allow_html=True)
    with c4:
        if st.button("전체선택", use_container_width=True, key="sel_all"):
            for i in st.session_state.claude_pool: i['선택'] = True
            st.session_state.claude_key += 1; st.rerun()
    with c5:
        if st.button("선택해제", use_container_width=True, key="desel_all"):
            for i in st.session_state.claude_pool: i['선택'] = False
            st.session_state.claude_key += 1; st.rerun()

    if st.session_state.is_collecting:
        with st.spinner("철학 및 기준에 따라 정밀 선별 중..."):
            engine = MasterGuardian_Smart_Claude()
            if os.path.exists('언론키워드셋.txt'):
                with open('언론키워드셋.txt', 'r', encoding='utf-8') as f:
                    keywords = [l.strip() for l in f if l.strip()]
                
                results = []
                for kw in keywords:
                    items = engine.search_naver_news(kw)
                    for i in items:
                        # [조건 1] 24시간 이내 기사
                        if engine.is_within_time(i.get('pubDate', '')):
                            title = BeautifulSoup(i['title'], 'html.parser').get_text()
                            # [조건 2] 슈 님의 5대 리스크 기준 부합
                            if engine.is_risk_context(title):
                                results.append({'src': kw, 'kw': title, 'url': i['link'], '선택': True})
                
                st.session_state.claude_pool = results
                st.session_state.claude_key += 1
                st.session_state.is_collecting = False; st.rerun()

    st.markdown("---")
    
    if st.session_state.claude_pool:
        df = pd.DataFrame(st.session_state.claude_pool)
        # 결과 내 검색 필터링
        if search_query:
            df = df[df['kw'].str.contains(search_query, case=False, na=False)]
            
        df['수집시점'] = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m/%d %H:%M')
        edited = render_table(df, f"table_{st.session_state.claude_key}_{search_query}")

        # 추출 및 백업
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

# ==========================================
# 3. 메인 (CSS 스타일 적용)
# ==========================================
def main():
    st.set_page_config(layout="wide", page_title="Shu Monitor 2026")
    st.markdown("""
        <style>
            [data-testid="stHeader"], [data-testid="stToolbar"] {display: none !important;}
            .main .block-container {padding-top: 2rem !important; max-width: 95% !important;}
            .status-badge {
                background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 6px;
                padding: 0.5rem; text-align: center; color: #1e3a8a; font-weight: bold;
                height: 2.8rem; line-height: 1.8rem;
            }
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.title("🛡️ SHU SYSTEM")
        st.markdown("---")
        menu = st.radio("메뉴 선택", ["📺 실시간 모니터링", "🤖 클로드 분석용 수집"])

    if menu == "📺 실시간 모니터링":
        st.info("기존 실시간 모니터링 로직을 여기에 통합하세요.")
    elif menu == "🤖 클로드 분석용 수집":
        run_claude_collector()

if __name__ == "__main__":
    main()
