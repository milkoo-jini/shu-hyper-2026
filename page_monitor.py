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
        self.time_limit = 86400 * 1

        self.fixed_topics = ["북중미 월드컵", "지방선거"]

        self.naver_queries = [
            "신종사기 적발",
            "공정위 적발",
            "허위광고 적발",
            "다크패턴",
            "식약처 적발",
            "식약처 회수",
            "불법 의약품 유통",
            "건강기능식품 불법",
            "불법판매 적발",
            "가품 위조 적발",
            "온라인 불법 유통",
            "해외직구 불법",
            "투자사기 적발",
            "온라인 사기 적발",
            "중고거래 사기",
            "사칭 광고 적발",
            "딥페이크 적발",
            "피싱 악성앱",
            "개인정보 유출",
            "대포통장 적발",
            "먹튀 피해",
            "폐업 환불 거부",
            "사기사이트 적발",
            "마약 유통 적발",
            "집단 피해 신고",
            "소비자 피해 급증",
            "긴급 재난",
            "기상 경보",
            "대형 사고",
        ]

        self.exclude_ad = [
            "변호사", "법무법인", "법률사무소", "선임", "상담문의", "무료상담", "승소",
            "카톡문의", "직통전화", "전화번호", "실력있는", "알아보고있다면",
            "홍보", "마케팅", "협찬", "보도자료", "캠페인",
            "분양", "입주", "청약", "특가", "할인", "세일", "프로모션", "무료증정", "체험단", "쇼룸",
            "총정리", "알아보자", "방법은", "이유는", "성공사례", "무료진단",
            "인사동정", "협약", "mou", "체결", "출범", "맞손", "시구", "방문",
            "칼럼", "사설", "기고", "기자시각", "독자투고",
            "운세", "부고", "인사", "ceo스토리", "기업인사", "인물열전", "who is",
            "주년", "탄생", "e종목",
            "사업 시동", "실증 추진", "전략 공유", "등급 허가", "Q&A", "합동 교육", "교육 실시",
            "공항날씨", "오늘날씨", "제주날씨", "날씨예보", "도약시킬 것", "패트롤", "월드비전",
            "레바논 분쟁", "적십자", "만원 기부", "중국 자동차", "한국 자동차", "피스타치오 가격",
            "제 2의 김창민", "사법 민낯", "계열사 누락", "금융 HOT 뉴스",
            "성금", "브리프", "이야기", "브리핑", "인터뷰", "인물", "論하다", "기업家", "겜덕", "이모저모", "세미나", "강원소방", "지휘관 회의",
        ]
        self.exclude_entertainment = [
            "방영", "예능", "본방", "시청률", "컴백", "데뷔", "무대",
            "아이돌", "솔로", "앨범", "차트", "박스오피스", "제작보고회",
            "회상했다", "회고", "추억", "성공 비결",
            "팬미팅", "굿즈", "직캠", "fancam", "열애", "결별", "이별", "교제",
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

    def _is_excluded(self, *texts):
        combined_orig    = " ".join(t.lower() for t in texts if t)
        combined_nospace = combined_orig.replace(" ", "")
        for ex in self.total_exclude:
            ex_nospace = ex.replace(" ", "")
            if ex_nospace in combined_nospace or ex in combined_orig:
                return True
        return False

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

    def _dedup(self, pool):
        def is_weighted_duplicate(title, seen_titles):
            # 가중치 기반 중복 제거 — 3글자 이상 단어 2점, 2글자 단어 1점, 합산 4점 이상이면 중복
            current_words = set(re.findall(r'[가-힣0-9%]{2,}', title))
            for prev in seen_titles:
                prev_words = set(re.findall(r'[가-힣0-9%]{2,}', prev))
                score = sum(2 if len(w) >= 3 else 1 for w in (current_words & prev_words))
                if score >= 4:
                    return True
            return False

        seen_exact = set()
        seen_titles = []
        unique_pool = []
        for item in pool:
            # 1단계: 완전 일치 제거
            exact = re.sub(r'\s+', '', item['kw'])
            if exact in seen_exact:
                continue
            seen_exact.add(exact)
            # 2단계: 가중치 기반 중복 제거
            if is_weighted_duplicate(item['kw'], seen_titles):
                continue
            seen_titles.append(item['kw'])
            unique_pool.append(item)
        return unique_pool

    def fetch_all_routes(self):
        pool = []
        h = {
            'X-Naver-Client-Id':     self.naver_id,
            'X-Naver-Client-Secret': self.naver_secret
        }

        try:
            sig_soup = BeautifulSoup(
                requests.get("https://signal.bz/logging", headers=self.headers, timeout=5).text,
                'html.parser'
            )
            for idx, item in enumerate(sig_soup.select(".ranking-item .rank-text")[:10]):
                kw = item.text.strip()
                if not self._is_excluded(kw):
                    pool.append({'src': self.src_mapping['SIGNAL'], 'kw': f"{idx+1}위: {kw}", 'desc': '', 'url': f"https://search.naver.com/search.naver?query={urllib.parse.quote(kw)}"})
        except:
            pass

        try:
            zum_soup = BeautifulSoup(
                requests.get("https://zum.com", headers=self.headers, timeout=5).text,
                'html.parser'
            )
            for idx, item in enumerate(zum_soup.select(".issue_keyword_list li .word")[:10]):
                kw = item.text.strip()
                if not self._is_excluded(kw):
                    pool.append({'src': self.src_mapping['ZUM'], 'kw': f"{idx+1}위: {kw}", 'desc': '', 'url': f"https://search.zum.com/search.zum?query={urllib.parse.quote(kw)}"})
        except:
            pass

        for q in self.naver_queries:
            eq = urllib.parse.quote(q)
            try:
                date = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={eq}&display=20&sort=date", headers=h, timeout=5).json()
                pool.extend(self._process_naver(date.get('items', []), self.src_mapping['NAVER_DATE']))
            except:
                pass

        for t in self.fixed_topics:
            try:
                # 네이버 뉴스
                t_res = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={urllib.parse.quote(t)}&display=25&sort=date", headers=h, timeout=5).json()
                items = t_res.get('items', [])
                # 북중미 월드컵은 제목에 '월드컵' 또는 '북중미' 포함된 기사만, 지방선거는 필터 없음
                if t == "북중미 월드컵":
                    items = [i for i in items if '월드컵' in BeautifulSoup(i.get('title', ''), 'html.parser').get_text() or '북중미' in BeautifulSoup(i.get('title', ''), 'html.parser').get_text()]
                pool.extend(self._process_naver(items, f"🔥 {t} 이슈"))

                # 구글 뉴스
                eq = urllib.parse.quote(t)
                g_res = requests.get(f"https://news.google.com/rss/search?q={eq}&hl=ko&gl=KR&ceid=KR:ko", headers=self.headers, timeout=5)
                now = datetime.datetime.now(self.kst)
                for i in BeautifulSoup(g_res.text, 'xml').find_all('item')[:20]:
                    title = i.title.text
                    try:
                        pub = i.pubDate.text[:25].strip()
                        p_date = datetime.datetime.strptime(pub, '%a, %d %b %Y %H:%M:%S')
                        p_date = pytz.utc.localize(p_date).astimezone(self.kst)
                        if (now - p_date).total_seconds() > self.time_limit:
                            continue
                    except:
                        pass
                    if not self._is_excluded(title):
                        pool.append({'src': f"🔥 {t} 이슈", 'kw': title, 'desc': '', 'url': i.link.text})
            except:
                pass

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

        for q in ["사건사고 한국", "피해 사기 논란"]:
            try:
                eq    = urllib.parse.quote(q)
                g_res = requests.get(f"https://news.google.com/rss/search?q={eq}&hl=ko&gl=KR&ceid=KR:ko", headers=self.headers, timeout=5)
                now = datetime.datetime.now(self.kst)
                for i in BeautifulSoup(g_res.text, 'xml').find_all('item')[:15]:
                    title = i.title.text
                    try:
                        pub = i.pubDate.text[:25].strip()
                        p_date = datetime.datetime.strptime(pub, '%a, %d %b %Y %H:%M:%S')
                        p_date = pytz.utc.localize(p_date).astimezone(self.kst)
                        if (now - p_date).total_seconds() > self.time_limit:
                            continue
                    except:
                        pass
                    if not self._is_excluded(title):
                        pool.append({'src': self.src_mapping['G_NEWS'], 'kw': title, 'desc': '', 'url': i.link.text})
            except:
                pass

        pool.extend(self._generic_fetch("https://news.daum.net/", "a.link_txt", self.src_mapping['DAUM'], limit=30))
        pool.extend(self._generic_fetch("https://news.daum.net/", ".tit_thumb", self.src_mapping['DAUM'], limit=30))
        pool.extend(self._generic_fetch("https://news.nate.com/", ".tit a",     self.src_mapping['NATE'], limit=15))
        pool.extend(self._generic_fetch("https://news.nate.com/", ".news_tit a",self.src_mapping['NATE'], limit=15))

        unique_pool = self._dedup(pool)

        def sort_key(x):
            if '🔥' in x['src']: return 0
            if '⏱️' in x['src']: return 1
            return 2
        return sorted(unique_pool, key=sort_key)

    # ----------------------------------------------------------------
    # 키워드 검색 (탭2용)
    # ----------------------------------------------------------------
    def search_keyword(self, keyword):
        pool = []
        h = {
            'X-Naver-Client-Id':     self.naver_id,
            'X-Naver-Client-Secret': self.naver_secret
        }
        eq = urllib.parse.quote(keyword)

        # 네이버 뉴스
        try:
            date = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={eq}&display=30&sort=date", headers=h, timeout=5).json()
            for i in date.get('items', []):
                try:
                    title = BeautifulSoup(i['title'], 'html.parser').get_text()
                    desc  = BeautifulSoup(i.get('description', ''), 'html.parser').get_text()
                    if not self._is_excluded(title, desc):
                        pool.append({'src': '⏱️ 네이버 뉴스', 'kw': title, 'desc': desc, 'url': i.get('link', '')})
                except:
                    pass
        except:
            pass

        # 구글 뉴스
        try:
            g_res = requests.get(f"https://news.google.com/rss/search?q={eq}&hl=ko&gl=KR&ceid=KR:ko", headers=self.headers, timeout=5)
            for i in BeautifulSoup(g_res.text, 'xml').find_all('item')[:20]:
                title = i.title.text
                if not self._is_excluded(title):
                    pool.append({'src': '📰 구글 뉴스', 'kw': title, 'desc': '', 'url': i.link.text})
        except:
            pass

        # 구글 트렌드 (키워드 포함 항목만)
        try:
            rss = requests.get("https://trends.google.com/trending/rss?geo=KR", headers=self.headers, timeout=5)
            for i in BeautifulSoup(rss.text, 'xml').find_all('item'):
                title = i.title.text
                if keyword.lower() in title.lower() and not self._is_excluded(title):
                    news_url = i.find('ht:news_item_url')
                    link = news_url.text if news_url else i.link.text
                    pool.append({'src': '🌐 구글 트렌드', 'kw': title, 'desc': '', 'url': link})
        except:
            pass

        return self._dedup(pool)


# ----------------------------------------------------------------
# 공통 테이블 렌더링
# ----------------------------------------------------------------
def render_table(df, editor_key):
    return st.data_editor(
        df,
        column_config={
            "수집시점": st.column_config.TextColumn("시간",               width=150),
            "src":      st.column_config.TextColumn("출처",               width=200),
            "kw":       st.column_config.TextColumn("이슈 헤드라인 전문"),
            "url":      st.column_config.LinkColumn(" ", display_text="🔗", width=60),
            "선택":     st.column_config.CheckboxColumn(" ",              width=60),
        },
        column_order=("수집시점", "src", "kw", "url", "선택"),
        hide_index=True, use_container_width=True, height=900,
        key=editor_key
    )


# ----------------------------------------------------------------
# UI
# ----------------------------------------------------------------
def run_monitor():
    # CSS는 app.py에서 공통 적용

    # session_state 초기화
    if 'data_pool'    not in st.session_state: st.session_state.data_pool    = []
    if 'editor_key'   not in st.session_state: st.session_state.editor_key   = 0
    if 'is_scanning'  not in st.session_state: st.session_state.is_scanning  = False
    if 'search_pool'  not in st.session_state: st.session_state.search_pool  = []
    if 'search_key'   not in st.session_state: st.session_state.search_key   = 0
    if 'is_searching' not in st.session_state: st.session_state.is_searching = False
    if 'search_kw'    not in st.session_state: st.session_state.search_kw    = ""

    tab1, tab2 = st.tabs(["🔍 실시간 이슈 모니터링", "🔎 키워드 검색"])

    # ----------------------------------------------------------------
    # 탭1: 실시간 이슈 모니터링
    # ----------------------------------------------------------------
    with tab1:
        if st.session_state.is_scanning:
            st.markdown("### 🔍 실시간 이슈 모니터링 &nbsp; ⏳ 스캔 중...")
        else:
            st.markdown("### 🔍 실시간 이슈 모니터링")

        c1, c2, c3, c4, c5 = st.columns([1.5, 2, 0.5, 0.5, 0.5])
        with c1:
            if st.button("🚀 전체 채널 스캔", use_container_width=True):
                st.session_state.is_scanning = True
                st.rerun()
        with c2:
            filter_query = st.text_input("", placeholder="🔍 결과 내 필터링", label_visibility="collapsed", key="filter1")
        with c3:
            st.markdown(f"<div class='status-badge'>{len(st.session_state.data_pool)}건</div>", unsafe_allow_html=True)
        with c4:
            if st.button("전체선택", use_container_width=True, key="sel1"):
                for item in st.session_state.data_pool: item['선택'] = True
                st.session_state.editor_key += 1; st.rerun()
        with c5:
            if st.button("선택해제", use_container_width=True, key="desel1"):
                for item in st.session_state.data_pool: item['선택'] = False
                st.session_state.editor_key += 1; st.rerun()

        if st.session_state.is_scanning:
            with st.spinner("채널 스캔 중입니다..."):
                st.session_state.data_pool = [dict(d, 선택=True) for d in ShuMonitorEngine().fetch_all_routes()]
                st.session_state.editor_key += 1
                st.session_state.is_scanning = False
                st.rerun()

        st.markdown("---")

        if st.session_state.data_pool:
            df = pd.DataFrame(st.session_state.data_pool)
            if filter_query:
                df = df[df['kw'].str.contains(filter_query, case=False, na=False)]
            df['수집시점'] = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m/%d %H:%M')
            edited_df = render_table(df, f"editor_{st.session_state.editor_key}")

            if not edited_df[edited_df['선택'] == True].empty:
                output = io.BytesIO()
                edited_df[edited_df['선택'] == True].drop(columns=['선택']).to_excel(output, index=False, engine='openpyxl')
                st.download_button(label="📊 선택 항목 엑셀 추출", data=output.getvalue(), file_name="Shu_Issue_Report.xlsx", use_container_width=True)

    # ----------------------------------------------------------------
    # 탭2: 키워드 검색
    # ----------------------------------------------------------------
    with tab2:
        st.markdown("### 🔎 키워드 검색")
        st.caption("검색어를 입력하면 네이버 뉴스·구글 뉴스·구글 트렌드에서 관련 기사를 가져옵니다.")

        s1, s2 = st.columns([3, 0.7])
        with s1:
            search_input = st.text_input("", placeholder="검색어 입력 (예: 쿠팡, 딥페이크, 식약처)", label_visibility="collapsed", key="search_input")
        with s2:
            search_btn = st.button("🔎 검색", use_container_width=True)

        if search_btn and search_input.strip():
            st.session_state.is_searching = True
            st.session_state.search_kw = search_input.strip()
            st.rerun()

        if st.session_state.is_searching:
            with st.spinner(f"'{st.session_state.search_kw}' 검색 중..."):
                results = ShuMonitorEngine().search_keyword(st.session_state.search_kw)
                st.session_state.search_pool = [dict(d, 선택=True) for d in results]
                st.session_state.search_key += 1
                st.session_state.is_searching = False
                st.rerun()

        if st.session_state.search_pool:
            s3, s4, s5, s6 = st.columns([3, 0.5, 0.5, 0.5])
            with s3:
                filter_search = st.text_input("", placeholder="🔍 결과 내 필터링", label_visibility="collapsed", key="filter2")
            with s4:
                st.markdown(f"<div class='status-badge'>{len(st.session_state.search_pool)}건</div>", unsafe_allow_html=True)
            with s5:
                if st.button("전체선택", use_container_width=True, key="sel2"):
                    for item in st.session_state.search_pool: item['선택'] = True
                    st.session_state.search_key += 1; st.rerun()
            with s6:
                if st.button("선택해제", use_container_width=True, key="desel2"):
                    for item in st.session_state.search_pool: item['선택'] = False
                    st.session_state.search_key += 1; st.rerun()

            st.markdown("---")

            df2 = pd.DataFrame(st.session_state.search_pool)
            if filter_search:
                df2 = df2[df2['kw'].str.contains(filter_search, case=False, na=False)]
            df2['수집시점'] = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m/%d %H:%M')
            edited_df2 = render_table(df2, f"search_editor_{st.session_state.search_key}")

            if not edited_df2[edited_df2['선택'] == True].empty:
                output2 = io.BytesIO()
                edited_df2[edited_df2['선택'] == True].drop(columns=['선택']).to_excel(output2, index=False, engine='openpyxl')
                st.download_button(label="📊 선택 항목 엑셀 추출", data=output2.getvalue(), file_name="Shu_Search_Report.xlsx", use_container_width=True, key="dl2")

if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Shu Monitor")
    run_monitor()
