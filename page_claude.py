import streamlit as st
import pandas as pd
import datetime, re, requests, io, time
import urllib.parse
from bs4 import BeautifulSoup
import pytz
import os
import email.utils
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

# [원본 엔진 - 슈 님의 로직 및 프롬프트 100% 보존]
class MasterGuardian_Smart_Claude:
    def __init__(self):
        self.now = datetime.now()
        # 원본 시간 제한: 24시간
        self.time_limit = self.now - timedelta(hours=24)
        
        # NAVER API 설정 (Secrets 활용 권장)
        try:
            self.naver_id = st.secrets["NAVER_ID"]
            self.naver_secret = st.secrets["NAVER_SECRET"]
        except:
            self.naver_id = "g6EGE1xFHkT99HQ2CRtd"
            self.naver_secret = "Q9DVSRZVL2"

        # 메모장 데이터 로딩
        self.answer_data = self.load_txt_file('정답기사리스트.txt') 
        self.wrong_data = self.load_txt_file('오답기사리스트.txt')   
        
        # 정답/오답 단어장 구축 (원본 로직)
        self.risk_vocab = self.build_vocab(self.answer_data)
        self.noise_vocab = self.build_vocab(self.wrong_data)

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
        """[원본] 슈 님이 주신 5가지 리스크 기준 및 메모장 데이터를 바탕으로 1차 선별"""
        current_words = set(re.findall(r'[가-힣0-9]{2,}', title))
        
        # 1️⃣ [오답 차단] 오답 패턴과 3개 이상 단어가 겹치면 탈락
        if len(current_words & self.noise_vocab) >= 3:
            return False

        # 2️⃣ [5대 리스크 기준 통과] 슈 님이 주신 본질적 기준 단어
        risk_standards = {
            "기만_사칭": ['사칭', '딥페이크', '허위', '가짜', '속여', '유명인'],
            "피해_보복": ['유출', '먹튀', '스토킹', '협박', '폐업', '연락두절', '보복'],
            "불법_유통": ['마약', '짝퉁', '도박', '성착취물', '밀수', '오남용'],
            "신뢰_훼손": ['비리', '부정부패', '해킹', '보안사고', '선거법', '뇌물'],
            "신종_수법": ['변종', '우회', '수법', '취약점', '악용', '비정상']
        }
        for category, words in risk_standards.items():
            if any(w in title for w in words): return True

        # 3️⃣ [정답지 학습 통과] 정답지(교과서)와 문맥상 2개 이상 단어 일치 시 통과
        if len(current_words & self.risk_vocab) >= 2:
            return True
        
        # 4️⃣ [강력 키워드] 사고 냄새가 나면 통과
        strong_words = ['구속', '수사', '적발', '침해', '피소', '혐의', '폭로', '검거', '입건']
        if any(sw in title for sw in strong_words): return True
            
        return False

    def make_claude_prompt(self, to_analyze):
        """[원본] 슈 님의 분석 철학이 반영된 최종 프롬프트 생성"""
        answer_examples = "\n".join([f"- {t}" for t in self.answer_data[:20]])
        wrong_examples = "\n".join([f"- {t}" for t in self.wrong_data[-30:]])
        
        prompt = f"""당신은 국가급 위기 관리 및 플랫폼 생태계 감시 전문가입니다. 

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
        return prompt

    def search_naver_news(self, keyword):
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {"X-Naver-Client-Id": self.naver_id, "X-Naver-Client-Secret": self.naver_secret}
        params = {"query": keyword, "display": 50, "sort": "date"}
        try:
            res = requests.get(url, headers=headers, params=params, timeout=5)
            return res.json().get('items', []) if res.status_code == 200 else []
        except: return []

    def search_google_news(self, keyword):
        url = f"https://news.google.com/rss/search?q={keyword}%20when:1d&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(url, timeout=5)
            titles = re.findall(r'<title>(.*?)</title>', res.text)[1:]
            links = re.findall(r'<link>(.*?)</link>', res.text)[1:]
            pub_dates = re.findall(r'<pubDate>(.*?)</pubDate>', res.text)
            return [{'title': t, 'link': l, 'pubDate': d} for t, l, d in zip(titles, links, pub_dates)]
        except: return []

def run_claude_collector():
    # [UI] 톤앤매너만 깔끔하게 유지
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Color+Emoji&display=swap');
            .emoji { font-family: 'Noto Color Emoji', sans-serif !important; }
        </style>
        <h3><span class="emoji">🛡️</span> 클로드 분석용 언론 수집</h3>
    """, unsafe_allow_html=True)
    st.caption("AI 분석용 로우 데이터 가공")

    status_placeholder = st.empty()

    if 'claude_pool' not in st.session_state: st.session_state.claude_pool = []
    if 'claude_key' not in st.session_state: st.session_state.claude_key = 0

    c1, c2, c3, c4, c5 = st.columns([1.5, 2, 0.5, 0.5, 0.5])
    with c1:
        if st.button("🚀 로우 데이터 수집 시작", use_container_width=True):
            st.session_state.is_collecting = True
            st.session_state.stop_flag = False
            st.rerun()
    with c2:
        search_query = st.text_input("", placeholder="🔍 결과 내 키워드 검색", label_visibility="collapsed")
    with c3:
        st.markdown(f"<div style='border:1px solid #007BFF; color:#007BFF; font-weight:bold; border-radius:5px; padding:5.5px; text-align:center;'>{len(st.session_state.claude_pool)}건</div>", unsafe_allow_html=True)
    with c4:
        if st.button("전체선택", use_container_width=True):
            for i in st.session_state.claude_pool: i['선택'] = True
            st.session_state.claude_key += 1; st.rerun()
    with c5:
        if st.button("선택해제", use_container_width=True):
            for i in st.session_state.claude_pool: i['선택'] = False
            st.session_state.claude_key += 1; st.rerun()

    if st.session_state.get('is_collecting', False):
        with status_placeholder.status("📡 수집 및 이중 학습 필터링 시작...", expanded=True) as status:
            engine = MasterGuardian_Smart_Claude()
            if os.path.exists('언론키워드셋.txt'):
                with open('언론키워드셋.txt', 'r', encoding='utf-8') as f:
                    keywords = [l.strip() for l in f if l.strip()]
                
                final_results = []
                url_bucket = set()
                to_analyze_text = ""
                total = len(keywords)

                for idx, kw in enumerate(keywords):
                    status.update(label=f"🔎 [{idx+1}/{total}] '{kw}' 정밀 스캔 중...", state="running")
                    
                    if st.session_state.get('stop_flag', False):
                        status.update(label="⛔ 분석 중단됨", state="error")
                        break
                    
                    # 네이버 + 구글 뉴스 합산 (원본 로직)
                    articles = engine.search_naver_news(kw) + engine.search_google_news(kw)
                    
                    for art in articles:
                        title, link = art['title'], art['link']
                        pub_date_str = art.get('pubDate', '')
                        display_title = re.sub(r'<[^>]*>', '', title).replace('&quot;', '"').strip()
                        
                        if link in url_bucket: continue
                        
                        # [원본] 시간 제한 필터링
                        if pub_date_str:
                            try:
                                pub_dt = parsedate_to_datetime(pub_date_str)
                                if pub_dt.tzinfo: pub_dt = pub_dt.replace(tzinfo=None)
                                if pub_dt < engine.time_limit: continue
                            except: pass

                        # [원본] 어미 필터 + 리스크 본질 검사
                        if any(display_title.endswith(e) for e in ['시사점', '모색', '종료', '설치', '추진', '이유']): continue
                        if not engine.is_risk_context(display_title): continue

                        # [원본] 점수제 중복 제거 로직
                        current_words = set(re.findall(r'[가-힣0-9%]{2,}', display_title))
                        is_duplicate = any(sum(2 if len(w) >= 3 else 1 for w in (current_words & set(re.findall(r'[가-힣0-9%]{2,}', r['기사제목'])))) >= 4 
                                          for r in final_results)
                        if is_duplicate: continue

                        final_results.append({'검색키워드': kw, '기사제목': display_title, '링크': link, '선택': True})
                        to_analyze_text += f"- {display_title}\n"
                        url_bucket.add(link)
                    
                    time.sleep(0.01)

                st.session_state.claude_pool = final_results
                st.session_state.final_prompt = engine.make_claude_prompt(to_analyze_text) if to_analyze_text else ""
                st.session_state.claude_key += 1
                status.update(label=f"✅ 선별 완료 (총 {len(final_results)}건)", state="complete")
            
            st.session_state.is_collecting = False
            time.sleep(1)
            st.rerun()

    st.divider()
    
    if st.session_state.claude_pool:
        df = pd.DataFrame(st.session_state.claude_pool)
        if search_query:
            df = df[df['기사제목'].str.contains(search_query, case=False, na=False)]
        
        edited = st.data_editor(
            df,
            column_config={
                "검색키워드": st.column_config.TextColumn("출처", width=150),
                "기사제목": st.column_config.TextColumn("클로드 분석 대상 헤드라인"),
                "링크": st.column_config.LinkColumn(" ", display_text="🔗", width=60),
                "선택": st.column_config.CheckboxColumn(" ", width=60),
            },
            column_order=("검색키워드", "기사제목", "링크", "선택"),
            hide_index=True, use_container_width=True, height=800,
            key=f"table_{st.session_state.claude_key}"
        )
        
        sel = edited[edited['선택'] == True]
        if not sel.empty:
            t1, t2 = st.columns(2)
            with t1:
                # [원본 반영] 선택된 기사들로 Claude 프롬프트 재생성
                engine_temp = MasterGuardian_Smart_Claude()
                to_analyze_selected = "\n".join([f"- {t}" for t in sel['기사제목'].tolist()])
                final_prompt = engine_temp.make_claude_prompt(to_analyze_selected)
                
                st.download_button("📄 Claude_Request.txt 다운로드", final_prompt.encode('utf-8'), "Claude_Request.txt", use_container_width=True)
                st.text_area("클로드에 붙여넣을 프롬프트", value=final_prompt, height=400)
            with t2:
                out = io.BytesIO()
                sel.drop(columns=['선택']).to_excel(out, index=False, engine='openpyxl')
                st.download_button("📊 엑셀 결과 저장", out.getvalue(), f"Report_{datetime.now().strftime('%m%d_%H%M')}.xlsx", use_container_width=True)
