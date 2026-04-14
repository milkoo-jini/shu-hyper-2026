import streamlit as st
import pandas as pd
import datetime, re, requests, io, os
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime

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
        self.wrong_data  = self.load_txt_file('오답기사리스트.txt')
        self.risk_vocab  = self.build_vocab(self.answer_data)
        self.noise_vocab = self.build_vocab(self.wrong_data)

        # 제외 단어 — 광고·홍보·단순정보성
        self.exclude_list = [
            "변호사", "법무법인", "법률사무소", "상담문의", "무료상담", "홍보", "마케팅", "보도자료",
            "분양", "입주", "청약", "특가", "할인", "세일", "프로모션", "칼럼", "사설", "기고",
            "운세", "부고", "인사", "ceo스토리", "who is", "who", "WHO", "트럼프", "인터뷰", "interview",
            "라운지", "포커스", "소식", "재계는", "레이더", "사사건건", "와글와글", "오프닝"
        ]

        # 단순 정보성 어미
        self.exclude_endings = ['시사점', '모색', '종료', '설치', '추진', '이유']

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
        # 제외단어 체크
        if any(ex in title for ex in self.exclude_list): return False
        # 어미 필터
        if any(title.endswith(e) for e in self.exclude_endings): return False

        current_words = set(re.findall(r'[가-힣0-9]{2,}', title))

        # 오답 vocab 3개 이상 겹치면 제외
        if len(current_words & self.noise_vocab) >= 3: return False

        # 5대 리스크 기준
        risk_standards = {
            "기만_사칭": ['사칭', '딥페이크', '허위', '가짜', '속여', '유명인'],
            "피해_보복": ['유출', '먹튀', '스토킹', '협박', '폐업', '연락두절', '보복'],
            "불법_유통": ['마약', '짝퉁', '도박', '성착취물', '밀수', '오남용'],
            "신뢰_훼손": ['비리', '부정부패', '해킹', '보안사고', '선거법', '뇌물'],
            "신종_수법": ['변종', '우회', '수법', '취약점', '악용', '비정상']
        }
        for words in risk_standards.values():
            if any(w in title for w in words): return True

        # 정답 vocab 2개 이상 겹치면 통과
        if len(current_words & self.risk_vocab) >= 2: return True

        # 강력 키워드 — 정답지 없어도 사고 냄새나면 통과
        strong_words = ['구속', '수사', '적발', '침해', '피소', '혐의', '폭로', '검거', '입건']
        if any(sw in title for sw in strong_words): return True

        return False

    def is_duplicate(self, title, final_results):
        # 가중치 기반 중복 제거 — 3글자 이상 단어 2점, 2글자 단어 1점, 합산 4점 이상이면 중복
        current_words = set(re.findall(r'[가-힣0-9%]{2,}', title))
        for r in final_results:
            prev_words = set(re.findall(r'[가-힣0-9%]{2,}', r['기사제목']))
            score = sum(2 if len(w) >= 3 else 1 for w in (current_words & prev_words))
            if score >= 4:
                return True
        return False

    def make_claude_prompt(self, to_analyze):
        answer_examples = "\n".join([f"- {t}" for t in self.answer_data[:20]])
        wrong_examples  = "\n".join([f"- {t}" for t in self.wrong_data[-30:]])
        return f"""당신은 국가급 위기 관리 및 플랫폼 생태계 감시 전문가입니다.

### **📖 [공부해야 할 정답 사례]**
{answer_examples if answer_examples else "사례 분석 중..."}

### **🕵️ [리스크 판별 기준 - 아래 본질이 보이면 무조건 포착]**
1. **기만 및 사칭**: 사칭, 허위 정보, 딥페이크 등 사용자를 속이는 행위.
2. **이용자 피해 및 보복**: 유출, 협박, 스토킹, 금전적 먹튀, 기습 폐업 등.
3. **불법 유통 및 위반**: 마약, 짝퉁, 도박 사이트 유도, 성착취물 등.
4. **사회적 신뢰 훼손**: 비리, 부정부패, 선거법 위반, 국가 기관 보안 사고 등.
5. **신종 수법 및 사각지대**: 플랫폼 취약점을 악용하는 모든 비정상적 영업.

### **⚠️ [분석 철학]**
- **카테고리에 갇히지 마십시오**: 정치, 경제, 사회 등 분야 상관없이 위 기준에 해당하면 리스크입니다.
- **포괄적 해석**: 정답 사례와 단어가 달라도, 피해자가 발생하거나 법을 어기는 본질이 같다면 포착하세요.
- **오답만 제외**: 아래 명시된 단순 동정/홍보 뉴스만 필터링하십시오.

### **🚫 [오답 사례 - 무조건 패스]**
{wrong_examples if wrong_examples else "없음"}

---
### **[검토 대상 리스트]**
{to_analyze}

---
[제목 / 판별결과(포착/패스) / 사유] 형식으로 정리하세요."""

    def search_naver_news(self, keyword):
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_id, "X-Naver-Client-Secret": self.naver_secret}
        params = {"query": keyword, "display": 20, "sort": "date"}
        try:
            res = requests.get(url, headers=headers, params=params, timeout=5)
            return res.json().get('items', []) if res.status_code == 200 else []
        except: return []

    # BeautifulSoup 기반 구글 뉴스 파싱 + 시간 필터
    def search_google_news(self, keyword):
        url = f"https://news.google.com/rss/search?q={keyword}%20when:1d&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(url, timeout=5)
            soup = BeautifulSoup(res.text, 'xml')
            results = []
            for item in soup.find_all('item'):
                title   = item.title.text if item.title else ''
                link    = item.link.text  if item.link  else ''
                pub_date = item.pubDate.text if item.pubDate else ''
                results.append({'title': title, 'link': link, 'pubDate': pub_date})
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

    menu_c1, menu_c2, menu_c3, menu_c4 = st.columns([1.2, 2, 1.5, 0.5])

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
            full_txt = engine_temp.make_claude_prompt("\n".join(sel_titles))
            st.download_button("📄 분석용.txt 다운로드", full_txt.encode('utf-8'), "Claude_Task.txt", use_container_width=True)
        else:
            st.button("📄 대기 중", disabled=True, use_container_width=True)

    with menu_c4:
        st.markdown(f"<div class='status-badge'>{len(st.session_state[DATA_KEY])}건</div>", unsafe_allow_html=True)

    if st.session_state.get('is_collecting', False):
        progress_placeholder = st.empty()
        with st.spinner(""):
            engine = MasterGuardian_Smart_Claude()

            if os.path.exists('언론키워드셋.txt'):
                with open('언론키워드셋.txt', 'r', encoding='utf-8') as f:
                    keywords = list(set([l.strip() for l in f if l.strip()]))

                final_filtered = []
                url_bucket = set()
                time_limit = datetime.now(engine.kst) - timedelta(hours=24)

                for idx, kw in enumerate(keywords):
                    progress_placeholder.markdown(f"📡 **'{kw}'** 수집 중... [{idx+1}/{len(keywords)}]")
                    all_news = engine.search_naver_news(kw) + engine.search_google_news(kw)

                    for art in all_news:
                        link  = art.get('link', art.get('originallink', ''))
                        title = re.sub(r'<[^>]*>', '', art.get('title', '')).replace('&quot;', '"').strip()

                        if not link or link in url_bucket: continue

                        # 시간 필터 — 24시간 이내만
                        pub_date_str = art.get('pubDate', '')
                        if pub_date_str:
                            try:
                                pub_dt = parsedate_to_datetime(pub_date_str)
                                if pub_dt.tzinfo is None:
                                    pub_dt = pub_dt.replace(tzinfo=engine.kst)
                                if pub_dt < time_limit:
                                    continue
                            except: pass

                        # 리스크 판별
                        if not engine.is_risk_context(title): continue

                        # 가중치 기반 중복 제거
                        if engine.is_duplicate(title, final_filtered): continue

                        url_bucket.add(link)
                        final_filtered.append({
                            '수집시간': datetime.now(engine.kst).strftime('%H:%M'),
                            '기사제목': title,
                            '링크': link,
                            '선택': True
                        })

                st.session_state[DATA_KEY] = final_filtered
                progress_placeholder.empty()

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
