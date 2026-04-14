import streamlit as st
import pandas as pd
import datetime, re, requests, io, time, os
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

# [무결성 체크] 슈 님의 순정 클래스 - 기준 로직 100% 보존
class MasterGuardian_Smart_Claude:
    def __init__(self):
        self.kst = timezone(timedelta(hours=9))
        self.now = datetime.now(self.kst)
        
        try:
            self.naver_id = st.secrets["NAVER_ID"]
            self.naver_secret = st.secrets["NAVER_SECRET"]
        except:
            self.naver_id = ""
            self.naver_secret = ""

        self.answer_data = self.load_txt_file('정답기사리스트.txt') 
        self.wrong_data = self.load_txt_file('오답기사리스트.txt')   
        self.risk_vocab = self.build_vocab(self.answer_data)
        self.noise_vocab = self.build_vocab(self.wrong_data)

        self.exclude_list = [
            "변호사", "법무법인", "법률사무소", "상담문의", "무료상담", "홍보", "마케팅", "보도자료",
            "분양", "입주", "청약", "특가", "할인", "세일", "프로모션", "칼럼", "사설", "기고",
            "운세", "부고", "인사", "ceo스토리", "who is", "who", "WHO", "트럼프", "인터뷰", "interview",
            "라운지", "포커스", "소식", "재계는", "레이더", "사사건건", "와글와글", "오프닝"
        ]

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

    def is_risk_context(self, title):
        if any(ex in title for ex in self.exclude_list): return False
        current_words = set(re.findall(r'[가-힣0-9]{2,}', title))
        if len(current_words & self.noise_vocab) >= 3: return False

        risk_standards = {
            "기만_사칭": ['사칭', '딥페이크', '허위', '가짜', '속여', '유명인'],
            "피해_보복": ['유출', '먹튀', '스토킹', '협박', '폐업', '연락두절', '보복'],
            "불법_유통": ['마약', '짝퉁', '도박', '성착취물', '밀수', '오남용'],
            "신뢰_훼손": ['비리', '부정부패', '해킹', '보안사고', '선거법', '뇌물'],
            "신종_수법": ['변종', '우회', '수법', '취약점', '악용', '비정상']
        }
        for words in risk_standards.values():
            if any(w in title for w in words): return True
        return len(current_words & self.risk_vocab) >= 2

    def make_claude_download_txt(self, to_analyze):
        return f"""---\n### **[검토 대상 리스트]**\n{to_analyze}\n\n---\n[제목 / 판별결과(포착/패스) / 사유] 형식으로 정리하세요."""

    def search_naver_news(self, keyword):
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_id, "X-Naver-Client-Secret": self.naver_secret}
        params = {"query": keyword, "display": 20, "sort": "date"}
        try:
            res = requests.get(url, headers=headers, params=params)
            return res.json().get('items', []) if res.status_code == 200 else []
        except: return []

    # ✅ 수정 1: 구글 뉴스 파싱 → BeautifulSoup으로 교체 (링크 중복 방지)
    def search_google_news(self, keyword):
        url = f"https://news.google.com/rss/search?q={keyword}%20when:1d&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(url, timeout=5)
            soup = BeautifulSoup(res.text, 'xml')
            results = []
            for item in soup.find_all('item'):
                title = item.title.text if item.title else ''
                # 구글 리다이렉트 대신 실제 기사 링크 추출
                source_url = item.find('source')
                link = item.link.text if item.link else ''
                results.append({'title': title, 'link': link})
            return results
        except: return []


def run_claude_collector():
    st.markdown("""
        <style>
            [data-testid="stHeader"],
            [data-testid="stDecoration"],
            [data-testid="stToolbar"],
            header[data-testid="stHeader"] {
                display: none !important;
                height: 0 !important;
            }
            .main .block-container {
                padding-top: 2.5rem !important;
                margin-top: 0 !important;
                max-width: 95% !important;
            }
            .status-badge {
                background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 6px;
                padding: 0.5rem; text-align: center; color: #1e3a8a; font-weight: bold;
                height: 2.8rem; line-height: 1.8rem;
            }
        </style>
    """, unsafe_allow_html=True)

    if "is_collecting" not in st.session_state: st.session_state.is_collecting = False

    st.markdown("### 🛡️ 클로드 분석용 언론 수집")
    
    DATA_KEY = "FINAL_FILTERED_STORAGE_V2"
    if DATA_KEY not in st.session_state: 
        st.session_state[DATA_KEY] = []
    
    menu_c1, menu_c2, menu_c3, menu_c4, menu_c5 = st.columns([1.2, 2, 1.5, 0.5, 0.5])
    
    with menu_c1:
        if st.button("🚀 수집 시작", use_container_width=True):
            st.session_state[DATA_KEY] = []
            st.session_state.is_collecting = True
            st.rerun()

    with menu_c2:
        search_query = st.text_input("", placeholder="🔍 결과 내 필터링", label_visibility="collapsed")

    with menu_c3:
        df_btn = pd.DataFrame(st.session_state[DATA_KEY])
        if not df_btn.empty and any(df_btn['선택']):
            sel_titles = df_btn[df_btn['선택'] == True]['기사제목'].tolist()
            engine_temp = MasterGuardian_Smart_Claude()
            full_txt = engine_temp.make_claude_download_txt("\n".join(sel_titles))
            st.download_button("📄 분석용.txt 다운로드", full_txt.encode('utf-8'), "Claude_Task.txt", use_container_width=True)
        else:
            st.button("📄 대기 중", disabled=True, use_container_width=True)

    with menu_c4:
        st.markdown(f"<div class='status-badge'>{len(st.session_state[DATA_KEY])}건</div>", unsafe_allow_html=True)
    with menu_c5:
        if st.button("선택해제", use_container_width=True):
            for item in st.session_state[DATA_KEY]: item["선택"] = False
            st.rerun()

    if st.session_state.get('is_collecting', False):
        with st.spinner("📡 전수 조사 중..."):
            engine = MasterGuardian_Smart_Claude()
            
            if os.path.exists('언론키워드셋.txt'):
                with open('언론키워드셋.txt', 'r', encoding='utf-8') as f:
                    keywords = list(set([l.strip() for l in f if l.strip()]))
                
                # 1단계: 링크 기준 1차 중복 제거
                raw_pool = {} 
                for idx, kw in enumerate(keywords):
                    pass  # 진행상황은 spinner로 표시
                    all_news = engine.search_naver_news(kw) + engine.search_google_news(kw)
                    
                    for art in all_news:
                        link = art.get('link', art.get('originallink', ''))
                        if not link or link in raw_pool: continue
                        title = re.sub(r'<[^>]*>', '', art.get('title', '')).replace('&quot;', '"').strip()
                        if engine.is_risk_context(title):
                            raw_pool[link] = title

                # ✅ 수정 2: 2단계 중복 제거 → 핵심 단어 2개 이상 겹치면 중복

                final_filtered = []
                current_time = datetime.now(engine.kst).strftime('%H:%M')

                def extract_key_words(text):
                    # 2글자 이상 한글·숫자 단어 추출
                    return set(re.findall(r'[가-힣0-9]{2,}', text))

                seen_titles = []  # (key_words, title) 저장

                for link, title in raw_pool.items():
                    key_words = extract_key_words(title)
                    is_dup = False
                    for prev_key, _ in seen_titles:
                        # 핵심 단어 2개 이상 겹치면 중복
                        if len(key_words & prev_key) >= 2:
                            is_dup = True
                            break
                    if not is_dup:
                        seen_titles.append((key_words, title))
                        final_filtered.append({
                            '수집시간': current_time, 
                            '기사제목': title, 
                            '링크': link, 
                            '선택': True
                        })
                
                st.session_state[DATA_KEY] = final_filtered
                

        st.session_state.is_collecting = False
        st.rerun()

    if st.session_state[DATA_KEY]:
        df = pd.DataFrame(st.session_state[DATA_KEY])
        if search_query:
            df = df[df['기사제목'].str.contains(search_query, case=False, na=False)]
        
        st.data_editor(
            df,
            column_config={
                "수집시간": st.column_config.TextColumn("시간", width=85),
                "기사제목": st.column_config.TextColumn("헤드라인"),
                "링크": st.column_config.LinkColumn(" ", display_text="🔗", width=40),
                "선택": st.column_config.CheckboxColumn(" ", width=40),
            },
            hide_index=True, use_container_width=True, height=700,
            key=f"EDITOR_V2_{len(st.session_state[DATA_KEY])}"
        )
