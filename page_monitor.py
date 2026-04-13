import streamlit as st
import pandas as pd
import datetime, re, requests, io
import urllib.parse
from bs4 import BeautifulSoup
import pytz

class ShuMonitorEngine:
    def __init__(self):
        try:
            self.naver_id = st.secrets["NAVER_ID"]
            self.naver_secret = st.secrets["NAVER_SECRET"]
        except:
            self.naver_id = self.naver_secret = None

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.google.com/',
        }
        self.kst = pytz.timezone('Asia/Seoul')
        self.time_limit = 86400 * 3

        # 고정 주제 (항상 포함)
        self.fixed_topics = ["북중미 월드컵", "지방선거"]

        # 네이버 API 검색 쿼리
        # 정치·사회 광범위 이슈는 구글 트렌드에서 커버
        # 네이버는 업무 관련 + 사건사고 위주로만
        self.naver_queries = [
            # 업무 핵심 — 플랫폼·이커머스 제재
            "신종사기 적발",
            "공정위 적발",
            "허위광고 적발",
            "다크패턴",
            # 업무 핵심 — 식의약품
            "식약처 적발",
            "식약처 회수",
            "불법 의약품 유통",
            "건강기능식품 불법",
            # 업무 핵심 — 온라인 불법 유통
            "불법판매 적발",
            "가품 위조 적발",
            "온라인 불법 유통",
            "해외직구 불법",
            # 업무 핵심 — 사기·기망
            "투자사기 적발",
            "온라인 사기 적발",
            "중고거래 사기",
            "사칭 광고 적발",
            "딥페이크 적발",
            "피싱 악성앱",
            # 업무 핵심 — 개인정보·보안
            "개인정보 유출",
            "대포통장 적발",
            # 사건사고
            "먹튀 피해",
            "폐업 환불 거부",
            "사기사이트 적발",
            "마약 유통 적발",
            "집단 피해 신고",
            "소비자 피해 급증",
            # 재난·긴급 (날씨·사고)
            "긴급 재난",
            "기상 경보",
            "대형 사고",
        ]

        # 제외 단어 — 광고·홍보·단순정보성 노이즈
        self.exclude_ad = [
            # 법률 광고
            "변호사", "법무법인", "법률사무소", "선임", "상담문의", "무료상담", "승소",
            "카톡문의", "직통전화", "전화번호", "실력있는", "알아보고있다면",
            # 홍보·마케팅
            "홍보", "마케팅", "협찬", "보도자료", "캠페인",
            # 분양·상품 광고
            "분양", "입주", "청약", "특가", "할인", "세일", "프로모션", "무료증정", "체험단", "쇼룸",
            # 단순 정보성
            "총정리", "알아보자", "방법은", "이유는", "성공사례", "무료진단",
            # 단순 행정·의전
            "인사동정", "협약", "mou", "체결", "출범", "맞손", "시구", "방문",
            # 주관적 의견
            "칼럼", "사설", "기고", "기자시각", "독자투고",
            # 기타 노이즈
            "운세", "부고", "인사", "ceo스토리", "기업인사", "인물열전", "who is",
            "주년", "탄생", "e종목",
            "사업 시동", "실증 추진", "전략 공유", "등급 허가", "Q&A", "합동 교육", "교육 실시",
            "공항날씨", "오늘날씨", "제주날씨", "날씨예보", "도약시킬 것", "패트롤", "월드비전",
            "레바논 분쟁", "적십자", "만원 기부", "중국 자동차", "한국 자동차", "피스타치오 가격",
            "제 2의 김창민", "사법 민낯", "계열사 누락", "금융 HOT 뉴스",
            "성금", "브리프", "이야기", "브리핑", "인터뷰", "인물", "論하다", "기업家", "겜덕", "이모저모", "세미나", "강원소방", "지휘관 회의",
        ]
        self.exclude_entertainment = [
            # 방송·연예 가십 (방송 출연해서 한 말, 근황 등)
            "방영", "예능", "본방", "시청률", "컴백", "데뷔", "무대",
            "아이돌", "솔로", "앨범", "차트", "박스오피스", "제작보고회",
            "회상했다", "회고", "추억", "성공 비결",
            "팬미팅", "굿즈", "직캠", "fancam", "열애", "결별", "이별", "교제",
            # 스포츠 가십 (고정주제 월드컵은 별도 수집하므로 일반 스포츠 가십 제외)
            "프로야구", "야구", "관중", "피치클록", "득점왕", "홈런",
        ]
        self.total_exclude = [w.lower() for w in (self.exclude_ad + self.exclude_entertainment)]

        self.src_mapping = {
            'SIGNAL':     '📶 시그널 실검',
            'ZUM':        '🔵 줌 실시간',
            'NAVER_DATE': '⏱️ 네이버 실시간',
            'NAVER_SIM':  '📢 네이버 주요이슈',
            'G_TRENDS':   '🌐 구글 트렌드',
            'G_NEWS':     '📰 구글 뉴스',
            'DAUM':       '🟠 다음 인기',
            'NATE':       '🔴 네이트 이슈',
            'FMKOREA':    '⚽ 에펨코리아(포텐)',
            'DCINSIDE':   '🖼️ 디시인사이드(실베)',
        }

    # ----------------------------------------------------------------
    # [핵심] 제외 단어 체크 — 모든 채널에서 이 함수 하나만 사용
    # 조사 붙은 단어(쇼룸에, 변호사를 등)도 잡히도록
    # 원본 텍스트(공백 있는 상태)와 공백 제거 텍스트 둘 다 검사
    # ----------------------------------------------------------------
    def _is_excluded(self, *texts):
        combined_orig    = " ".join(t.lower() for t in texts if t)
        combined_nospace = combined_orig.replace(" ", "")
        for ex in self.total_exclude:
            ex_nospace = ex.replace(" ", "")
            if ex_nospace in combined_nospace or ex in combined_orig:
                return True
        return False

    # ----------------------------------------------------------------
    # 네이버 API 결과 처리 (공통)
    # ----------------------------------------------------------------
    def _process_naver(self, items, label):
        res = []
        if not items:
            return res
        now = datetime.datetime.now(self.kst)
        for i in items:
            try:
                p_date = datetime.datetime.strptime(
                    i.get('pubDate', ''), '%a, %d %b %Y %H:%M:%S +0900'
                ).replace(tzinfo=self.kst)
                title = BeautifulSoup(i['title'], 'html.parser').get_text()
                desc  = BeautifulSoup(i.get('description', ''), 'html.parser').get_text()
                if (now - p_date).total_seconds() < self.time_limit:
                    if not self._is_excluded(title, desc):
                        res.append({
                            'src': label, 'kw': title, 'desc': desc, 'url': i.get('link', '')
                        })
            except:
                pass
        return res

    # ----------------------------------------------------------------
    # 커뮤니티·뉴스 스크래핑 (공통)
    # ----------------------------------------------------------------
    def _generic_fetch(self, url, selector, label, base_url="", limit=20):
        try:
            res  = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            out  = []
            for a in soup.select(selector):
                title = a.text.strip()
                if title and not self._is_excluded(title):
                    link = a.get('href', '')
                    if link and not link.startswith('http'):
                        link = base_url + link
                    out.append({'src': label, 'kw': title, 'desc': '', 'url': link})
                    if len(out) >= limit:
                        break
            return out
        except:
            return []

    # ----------------------------------------------------------------
    # 메인 수집
    # ----------------------------------------------------------------
    def fetch_all_routes(self):
        pool = []
        h = {
            'X-Naver-Client-Id':     self.naver_id,
            'X-Naver-Client-Secret': self.naver_secret
        }

        # 1. 시그널 실검
        try:
            sig_soup = BeautifulSoup(
                requests.get("https://signal.bz/logging", headers=self.headers, timeout=5).text,
                'html.parser'
            )
            for idx, item in enumerate(sig_soup.select(".ranking-item .rank-text")[:10]):
                kw = item.text.strip()
                if not self._is_excluded(kw):
                    pool.append({
                        'src': self.src_mapping['SIGNAL'],
                        'kw': f"{idx+1}위: {kw}", 'desc': '',
                        'url': f"https://search.naver.com/search.naver?query={urllib.parse.quote(kw)}"
                    })
        except:
            pass

        # 2. 줌 실시간
        try:
            zum_soup = BeautifulSoup(
                requests.get("https://zum.com", headers=self.headers, timeout=5).text,
                'html.parser'
            )
            for idx, item in enumerate(zum_soup.select(".issue_keyword_list li .word")[:10]):
                kw = item.text.strip()
                if not self._is_excluded(kw):
                    pool.append({
                        'src': self.src_mapping['ZUM'],
                        'kw': f"{idx+1}위: {kw}", 'desc': '',
                        'url': f"https://search.zum.com/search.zum?query={urllib.parse.quote(kw)}"
                    })
        except:
            pass

        # 3. 네이버 뉴스 — 쿼리별 분리, date(최신순)만 수집
        for q in self.naver_queries:
            eq = urllib.parse.quote(q)
            try:
                date = requests.get(
                    f"https://openapi.naver.com/v1/search/news.json?query={eq}&display=20&sort=date",
                    headers=h, timeout=5
                ).json()
                pool.extend(self._process_naver(date.get('items', []), self.src_mapping['NAVER_DATE']))
            except:
                pass

        # 4. 고정 주제 (항상 포함, 동일 필터 통과)
        for t in self.fixed_topics:
            try:
                t_res = requests.get(
                    f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(t)}&display=25&sort=date",
                    headers=h, timeout=5
                ).json()
                pool.extend(self._process_naver(t_res.get('items', []), f"🔥 {t} 이슈"))
            except:
                pass

        # 5. 구글 트렌드 (한국)
        try:
            rss = requests.get("https://trends.google.com/trending/rss?geo=KR", headers=self.headers, timeout=5)
            for i in BeautifulSoup(rss.text, 'xml').find_all('item'):
                title    = i.title.text
                news_url = i.find('ht:news_item_url')
                link     = news_url.text if news_url else i.link.text
                if not self._is_excluded(title):
                    pool.append({'src': self.src_mapping['G_TRENDS'], 'kw': title, 'desc': '', 'url': link})
        except:
            pass

        # 6. 구글 뉴스 — 부정 이슈 키워드로 검색
        for q in ["사건사고 한국", "피해 사기 논란"]:
            try:
                eq    = urllib.parse.quote(q)
                g_res = requests.get(
                    f"https://news.google.com/rss/search?q={eq}&hl=ko&gl=KR&ceid=KR:ko",
                    headers=self.headers, timeout=5
                )
                for i in BeautifulSoup(g_res.text, 'xml').find_all('item')[:15]:
                    title = i.title.text
                    if not self._is_excluded(title):
                        pool.append({'src': self.src_mapping['G_NEWS'], 'kw': title, 'desc': '', 'url': i.link.text})
            except:
                pass

        # 7. 다음 뉴스 (URL 변경됨)
        pool.extend(self._generic_fetch("https://news.daum.net/",  "a.link_txt",          self.src_mapping['DAUM'], limit=30))
        pool.extend(self._generic_fetch("https://news.daum.net/",  ".tit_thumb",          self.src_mapping['DAUM'], limit=30))

        # 8. 네이트 뉴스
        pool.extend(self._generic_fetch("https://news.nate.com/",  ".tit a",              self.src_mapping['NATE'], limit=15))
        pool.extend(self._generic_fetch("https://news.nate.com/",  ".news_tit a",         self.src_mapping['NATE'], limit=15))

        # 9. 에펨·디시·시그널·줌은 Streamlit Cloud에서 IP 차단되어 수집 불가
        # 추후 로컬 환경에서만 사용하거나 API 대체 필요

        # 중복 제거 — 완전 일치 + 고유명사/수치 기반 + 공통 단어 비율
        def tokenize(text):
            text = re.sub(r'[^\w\s]', ' ', text)
            return set(w for w in text.split() if len(w) >= 2)

        def extract_key_tokens(text):
            # 고유명사(대문자 포함 단어, 숫자 포함 단어), 3글자 이상 단어 추출
            text = re.sub(r'[^\w\s]', ' ', text)
            tokens = text.split()
            key = set()
            for w in tokens:
                if len(w) >= 3:
                    key.add(w)
                if re.search(r'[0-9]', w):  # 수치 포함 단어 (900만원 등)
                    key.add(w)
            return key

        def is_similar(tokens_a, tokens_b, threshold=0.8):
            if not tokens_a or not tokens_b:
                return False
            intersection = tokens_a & tokens_b
            smaller = min(len(tokens_a), len(tokens_b))
            return len(intersection) / smaller >= threshold

        def is_key_duplicate(key_a, key_b):
            # 고유명사/수치 3개 이상 겹치면 중복
            if not key_a or not key_b:
                return False
            return len(key_a & key_b) >= 2

        seen_exact = set()
        seen_tokens = []
        seen_keys = []
        unique_pool = []
        for item in pool:
            # 1단계: 완전 일치 제거
            exact = re.sub(r'\s+', '', item['kw'])
            if exact in seen_exact:
                continue
            seen_exact.add(exact)
            # 2단계: 고유명사·수치 기반 중복 제거 (HL홀딩스+공정위+900만원 등)
            key_tokens = extract_key_tokens(item['kw'])
            if any(is_key_duplicate(key_tokens, prev) for prev in seen_keys):
                continue
            seen_keys.append(key_tokens)
            # 3단계: 공통 단어 비율 기반 유사 중복 제거
            tokens = tokenize(item['kw'])
            if any(is_similar(tokens, prev) for prev in seen_tokens):
                continue
            seen_tokens.append(tokens)
            unique_pool.append(item)

        # 정렬: 고정주제(🔥) 1순위 > 네이버 실시간(⏱️) 2순위 > 나머지
        def sort_key(x):
            if '🔥' in x['src']:
                return 0
            if '⏱️' in x['src']:
                return 1
            return 2
        return sorted(unique_pool, key=sort_key)


# ----------------------------------------------------------------
# UI
# ----------------------------------------------------------------
def run_monitor():
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

    if 'data_pool'  not in st.session_state: st.session_state.data_pool  = []
    if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

    # 로딩 상태 초기화
    if 'is_scanning' not in st.session_state: st.session_state.is_scanning = False

    # 제목 + 로딩 이모지
    if st.session_state.is_scanning:
        st.markdown("### 🔍 실시간 이슈 모니터링 &nbsp; ⏳ 스캔 중...")
    else:
        st.markdown("### 🔍 실시간 이슈 모니터링")

    c1, c2, c3 = st.columns([1, 1, 0.8])
    with c1:
        if st.button("🚀 전체 채널 스캔", use_container_width=True):
            st.session_state.is_scanning = True
            st.rerun()

    # 스캔 실행 (rerun 후 처리)
    if st.session_state.is_scanning:
        with st.spinner("채널 스캔 중입니다..."):
            st.session_state.data_pool = [dict(d, 선택=True) for d in ShuMonitorEngine().fetch_all_routes()]
            st.session_state.editor_key += 1
            st.session_state.is_scanning = False
            st.rerun()
    with c2:
        filter_query = st.text_input("", placeholder="🔍 결과 내 필터링", label_visibility="collapsed")
    with c3:
        st.markdown(f"<div class='status-badge'>{len(st.session_state.data_pool)}건</div>", unsafe_allow_html=True)

    _, b1, b2 = st.columns([8.2, 0.9, 0.9])
    with b1:
        if st.button("전체선택", use_container_width=True):
            for item in st.session_state.data_pool: item['선택'] = True
            st.session_state.editor_key += 1; st.rerun()
    with b2:
        if st.button("선택해제", use_container_width=True):
            for item in st.session_state.data_pool: item['선택'] = False
            st.session_state.editor_key += 1; st.rerun()

    st.markdown("---")

    if st.session_state.data_pool:
        df = pd.DataFrame(st.session_state.data_pool)
        if filter_query:
            df = df[df['kw'].str.contains(filter_query, case=False, na=False)]
        df['수집시점'] = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m/%d %H:%M')

        edited_df = st.data_editor(
            df,
            column_config={
                "수집시점": st.column_config.TextColumn("시간",               width=150),
                "src":      st.column_config.TextColumn("출처",               width=200),
                "kw":       st.column_config.TextColumn("이슈 헤드라인 전문", width=800),
                "url":      st.column_config.LinkColumn(" ", display_text="🔗", width=80),
                "선택":     st.column_config.CheckboxColumn(" ",              width=80),
            },
            column_order=("수집시점", "src", "kw", "url", "선택"),
            hide_index=True, use_container_width=False, height=600,
            key=f"editor_{st.session_state.editor_key}"
        )

        if not edited_df[edited_df['선택'] == True].empty:
            output = io.BytesIO()
            edited_df[edited_df['선택'] == True].drop(columns=['선택']).to_excel(
                output, index=False, engine='openpyxl'
            )
            st.download_button(
                label="📊 선택 항목 엑셀 추출",
                data=output.getvalue(),
                file_name="Shu_Issue_Report.xlsx",
                use_container_width=True
            )

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Shu Monitor")
    run_monitor()
