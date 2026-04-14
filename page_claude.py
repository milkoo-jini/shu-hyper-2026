import streamlit as st
import pandas as pd
import datetime, re, requests, io, time, os
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher # 중복 기사 판별용

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

        # 슈 님의 원본 데이터 로드
        self.answer_data = self.load_txt_file('정답기사리스트.txt') 
        self.wrong_data = self.load_txt_file('오답기사리스트.txt')   
        self.risk_vocab = self.build_vocab(self.answer_data)
        self.noise_vocab = self.build_vocab(self.wrong_data)

        # [보존] 제외 키워드 리스트 32개 그대로 유지
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
        # [순정 보존] 슈 님의 판독 로직 100% 유지
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
        params = {"query": keyword, "display": 50, "sort": "date"}
        try:
            res = requests.get(url, headers=headers, params=params)
            return res.json().get('items', []) if res.status_code == 200 else []
        except: return []

    def search_google_news(self, keyword):
        url = f"https://news.google.com/rss/search?q={keyword}%20when:1d&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(url)
            titles = re.findall(r'<title>(.*?)</title>', res.text)[1:]
            links = re.findall(r'<link>(.*?)</link>', res.text)[1:]
            return [{'title': t, 'link': l} for t, l in zip(titles, links)]
        except: return []

def run_claude_collector():
    st.markdown("### 🛡️ 클로드 분석용 언론 수집")
    
    # [수정] 데이터 세션 키
    DATA_KEY = "FINAL_FILTERED_STORAGE_V2"
    if DATA_KEY not in st.session_state: 
        st.session_state[DATA_KEY] = []
    
    menu_c1, menu_c2, menu_c3, menu_c4 = st.columns([1, 1.5, 2, 0.5])
    
    with menu_c1:
        if st.button("🚀 수집 시작", use_container_width=True):
            st.session_state[DATA_KEY] = []
            st.session_state.is_collecting = True
            st.rerun()

    with menu_c2:
        search_query = st.text_input("", placeholder="🔍 필터", label_visibility="collapsed")

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
        st.markdown(f"<div style='border:1px solid #007BFF; color:#007BFF; font-weight:bold; border-radius:5px; padding:5.5px; text-align:center;'>{len(st.session_state[DATA_KEY])}</div>", unsafe_allow_html=True)

    if st.session_state.get('is_collecting', False):
        with st.status("📡 전수 조사 중 (중복 박멸 모드)...", expanded=True) as status:
            engine = MasterGuardian_Smart_Claude()
            
            if os.path.exists('언론키워드셋.txt'):
                with open('언론키워드셋.txt', 'r', encoding='utf-8') as f:
                    keywords = list(set([l.strip() for l in f if l.strip()]))
                
                # [수정] 1단계: 모든 키워드의 기사를 링크 기준으로 1차 취합 (raw_pool)
                raw_pool = {} 
                for idx, kw in enumerate(keywords):
                    status.update(label=f"🔎 1차 수집: '{kw}' ({idx+1}/{len(keywords)})")
                    all_news = engine.search_naver_news(kw) + engine.search_google_news(kw)
                    
                    for art in all_news:
                        link = art.get('link', art.get('originallink', ''))
                        if not link or link in raw_pool: continue
                        
                        title = re.sub(r'<[^>]*>', '', art.get('title', '')).replace('&quot;', '"').strip()
                        # 슈 님의 순정 로직 통과 여부 확인
                        if engine.is_risk_context(title):
                            raw_pool[link] = title

                # [수정] 2단계: 수집 완료 후 모든 기사 대상 제목 유사도 전수 조사
                status.update(label="🧪 2차 필터링: 유사 기사 통합 중...")
                final_filtered = []
                current_time = datetime.now(engine.kst).strftime('%H:%M')
                
                for link, title in raw_pool.items():
                    is_dup = False
                    for seen in final_filtered:
                        # 제목 유사도 80% 이상이면 동일 기사로 간주하여 제외
                        if SequenceMatcher(None, title, seen['기사제목']).ratio() > 0.8:
                            is_dup = True
                            break
                    if not is_dup:
                        final_filtered.append({
                            '수집시간': current_time, 
                            '기사제목': title, 
                            '링크': link, 
                            '선택': True
                        })
                
                # 결과값 덮어쓰기
                st.session_state[DATA_KEY] = final_filtered
                
            status.update(label="✅ 수집 및 중복 제거 완료", state="complete")
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
