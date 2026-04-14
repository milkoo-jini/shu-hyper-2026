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

class MasterGuardian_Smart_Claude:
    def __init__(self):
        self.now = datetime.now()
        self.time_limit = self.now - timedelta(hours=24)
        
        try:
            self.naver_id = st.secrets["NAVER_ID"]
            self.naver_secret = st.secrets["NAVER_SECRET"]
        except:
            self.naver_id = "g6EGE1xFHkT99HQ2CRtd"
            self.naver_secret = "Q9DVSRZVL2"

        self.answer_data = self.load_txt_file('정답기사리스트.txt') 
        self.wrong_data = self.load_txt_file('오답기사리스트.txt')   
        
        self.risk_vocab = self.build_vocab(self.answer_data)
        self.noise_vocab = self.build_vocab(self.wrong_data)

        # 제외 키워드 리스트 (슈 님 요청사항 100% 반영)
        self.exclude_ad = [
            "변호사", "법무법인", "법률사무소", "선임", "상담문의", "무료상담", "승소",
            "카톡문의", "직통전화", "전화번호", "실력있는", "알아보고있다면",
            "홍보", "마케팅", "협찬", "보도자료", "캠페인",
            "분양", "입주", "청약", "특가", "할인", "세일", "프로모션", "무료증정", "체험단", "쇼룸",
            "총정리", "알아보자", "방법은", "이유는", "성공사례", "무료진단",
            "인사동정", "협약", "mou", "체결", "출범", "맞손", "시구", "방문",
            "칼럼", "사설", "기고", "기자시각", "독자투고", "시론", "가판",
            "운세", "부고", "인사", "ceo스토리", "기업인사", "인물열전", "who is", "who", "WHO",
            "주년", "탄생", "e종목",
            "사업 시동", "실증 추진", "전략 공유", "등급 허가", "Q&A", "합동 교육", "교육 실시",
            "공항날씨", "오늘날씨", "제주날씨", "날씨예보", "도약시킬 것", "패트롤", "월드비전",
            "레바논 분쟁", "적십자", "만원 기부", "중국 자동차", "한국 자동차", "피스타치오 가격",
            "제 2의 김창민", "사법 민낯", "계열사 누락", "금융 HOT 뉴스",
            "성금", "브리프", "이야기", "브리핑", "인터뷰", "interview", "인물", "論하다", "기업家", "겜덕", "이모저모", "세미나", "강원소방", "지휘관 회의",
            "트럼프", "라운지", "포커스", "소식", "재계는", "레이더", "사사건건", "와글와글", "오프닝"
        ]
        self.exclude_entertainment = [
            "방영", "예능", "본방", "시청률", "컴백", "데뷔", "무대",
            "아이돌", "솔로", "앨범", "차트", "박스오피스", "제작보고회",
            "회상했다", "회고", "추억", "성공 비결",
            "팬미팅", "굿즈", "직캠", "fancam", "열애", "결별", "이별", "교제",
            "프로야구", "야구", "관중", "피치클록", "득점왕", "홈런"
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
        current_words = set(re.findall(r'[가-힣0-9]{2,}', title))
        if len(current_words & self.noise_vocab) >= 3: return False
        if any(ad_word in title for ad_word in self.exclude_ad): return False
        if any(ent_word in title for ent_word in self.exclude_entertainment): return False

        risk_standards = {
            "기만_사칭": ['사칭', '딥페이크', '허위', '가짜', '속여', '유명인'],
            "피해_보복": ['유출', '먹튀', '스토킹', '협박', '폐업', '연락두절', '보복'],
            "불법_유통": ['마약', '짝퉁', '도박', '성착취물', '밀수', '오남용'],
            "신뢰_훼손": ['비리', '부정부패', '해킹', '보안사고', '선거법', '뇌물'],
            "신종_수법": ['변종', '우회', '수법', '취약점', '악용', '비정상']
        }
        for category, words in risk_standards.items():
            if any(w in title for w in words): return True
        if len(current_words & self.risk_vocab) >= 2: return True
        strong_words = ['구속', '수사', '적발', '침해', '피소', '혐의', '폭로', '검거', '입건']
        if any(sw in title for sw in strong_words): return True
        return False

    def make_claude_prompt(self, to_analyze):
        answer_examples = "\n".join([f"- {t}" for t in self.answer_data[:20]])
        wrong_examples = "\n".join([f"- {t}" for t in self.wrong_data[-30:]])
        # 슈 님 원본 명령 프롬프트 그대로 유지
        prompt = f"""당신은 국가급 위기 관리 및 플랫폼 생태계 감시 전문가입니다.\n\n### **📖 [공부해야 할 정답 사례]**\n{answer_examples}\n\n### **🕵️ [리스크 판별 기준]**\n1. 기만 및 사칭\n2. 이용자 피해 및 보복\n3. 불법 유통 및 위반\n4. 사회적 신뢰 훼손\n5. 신종 수법 및 사각지대\n\n### **⚠️ [분석 철학]**\n- 포괄적 해석 적용\n- 단순 동정/홍보 오답만 제외\n\n### **🚫 [오답 사례]**\n{wrong_examples}\n\n---\n### **[검토 대상 리스트]**\n{to_analyze}\n\n---\n[제목 / 판별결과(포착/패스) / 사유] 형식으로 정리하세요."""
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
    st.markdown("### 🛡️ 클로드 분석용 언론 수집")
    st.caption("AI 분석용 로우 데이터 가공 (시간/제외단어 필터 탑재)")

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
        with status_placeholder.status("📡 수집 및 정밀 필터링 시작...", expanded=True) as status:
            engine = MasterGuardian_Smart_Claude()
            if os.path.exists('언론키워드셋.txt'):
                with open('언론키워드셋.txt', 'r', encoding='utf-8') as f:
                    keywords = [l.strip() for l in f if l.strip()]
                
                final_results = []
                url_bucket = set()
                total = len(keywords)

                for idx, kw in enumerate(keywords):
                    status.update(label=f"🔎 [{idx+1}/{total}] '{kw}' 스캔 중...", state="running")
                    if st.session_state.get('stop_flag', False):
                        status.update(label="⛔ 중단됨", state="error")
                        break
                    
                    articles = engine.search_naver_news(kw) + engine.search_google_news(kw)
                    for art in articles:
                        title, link = art['title'], art['link']
                        pub_date_str = art.get('pubDate', '')
                        display_title = re.sub(r'<[^>]*>', '', title).replace('&quot;', '"').strip()
                        if link in url_bucket: continue
                        
                        # [반영] 수집 시간 4/14 09:00 형식
                        collect_time = datetime.now().strftime('%m/%d %H:%M')
                        
                        if pub_date_str:
                            try:
                                pub_dt = parsedate_to_datetime(pub_date_str)
                                if pub_dt.tzinfo: pub_dt = pub_dt.replace(tzinfo=None)
                                if pub_dt < engine.time_limit: continue
                            except: pass
                        if any(display_title.endswith(e) for e in ['시사점', '모색', '종료', '설치', '추진', '이유']): continue
                        if not engine.is_risk_context(display_title): continue
                        current_words = set(re.findall(r'[가-힣0-9%]{2,}', display_title))
                        is_duplicate = any(sum(2 if len(w) >= 3 else 1 for w in (current_words & set(re.findall(r'[가-힣0-9%]{2,}', r['기사제목'])))) >= 4 
                                          for r in final_results)
                        if is_duplicate: continue

                        # [반영] 검색키워드 앞에 시간 추가
                        time_stamped_kw = f"{collect_time} | {kw}"
                        final_results.append({'검색키워드': time_stamped_kw, '기사제목': display_title, '링크': link, '선택': True})
                        url_bucket.add(link)
                    time.sleep(0.01)

                st.session_state.claude_pool = final_results
                st.session_state.claude_key += 1
                status.update(label=f"✅ 완료 (총 {len(final_results)}건)", state="complete")
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
                "검색키워드": st.column_config.TextColumn("검색키워드", width=180),
                "기사제목": st.column_config.TextColumn("클로드 분석 대상 헤드라인"),
                "링크": st.column_config.LinkColumn(" ", display_text="🔗", width=60),
                "선택": st.column_config.CheckboxColumn(" ", width=60),
            },
            column_order=("검색키워드", "기사제목", "링크", "선택"),
            hide_index=True, use_container_width=True, height=600,
            key=f"table_{st.session_state.claude_key}"
        )
        
        sel = edited[edited['선택'] == True]
        if not sel.empty:
            st.markdown("#### ⬇️ 결과 내보내기")
            d1, d2, d3 = st.columns(3)
            
            # 선택된 제목만 세로로 나열한 텍스트 생성
            titles_only = "\n".join(sel['기사제목'].tolist())
            
            with d1:
                # ✅ [추가] 클로드에게 바로 줄 제목 리스트 전용 텍스트 파일
                st.download_button(
                    "📄 Claude용 제목 리스트(.txt)",
                    titles_only.encode('utf-8'),
                    f"Titles_{datetime.now().strftime('%m%d_%H%M')}.txt",
                    use_container_width=True,
                    help="클로드에게 제목만 바로 줄 때 사용하세요"
                )
            with d2:
                # 기존 엑셀 다운로드
                out = io.BytesIO()
                sel.drop(columns=['선택']).to_excel(out, index=False, engine='openpyxl')
                st.download_button("📊 엑셀 결과 저장", out.getvalue(), f"Report_{datetime.now().strftime('%m%d_%H%M')}.xlsx", use_container_width=True)
            with d3:
                # 슈 님의 명령 프롬프트가 포함된 전체 파일
                engine_temp = MasterGuardian_Smart_Claude()
                to_analyze_selected = "\n".join([f"- {t}" for t in sel['기사제목'].tolist()])
                final_prompt = engine_temp.make_claude_prompt(to_analyze_selected)
                st.download_button("📝 프롬프트 포함 전체 저장", final_prompt.encode('utf-8'), "Claude_Full_Request.txt", use_container_width=True)

            st.text_area("클로드 복사용 프롬프트 미리보기", value=final_prompt, height=300)
