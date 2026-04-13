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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.kst = pytz.timezone('Asia/Seoul')
        self.time_limit = 86400 * 3

        # 고정 주제 (항상 포함)
        self.fixed_topics = ["북중미 월드컵", "지방선거"]

        # 네이버 API 검색 쿼리 — 부정적 이슈 중심으로 쿼리별 분리
        self.naver_queries = [
            "사건사고",
            "피해자",
            "사기",
            "논란",
            "고발",
            "의혹",
        ]

        # 제외 단어 — 광고·홍보·단순정보성 노이즈
        self.exclude_ad = [
            "변호사", "법무법인", "법률사무소", "선임", "상담문의", "무료상담", "승소",
            "카톡문의", "직통전화", "전화번호", "실력있는", "알아보고있다면",
            "홍보", "마케팅", "기고", "협찬", "광고", "보도자료",
            "무료증정", "이벤트", "모집", "체험단", "쇼룸", "오픈행사",
            "대처법", "준비법", "대응방법", "성공사례", "무료진단", "해결사",
            "조언", "상담", "전문가", "ceo스토리", "기업인사", "인물열전",
            "who is", "e종목", "클릭", "주년", "탄생",
            # 광고·분양·상품
            "분양", "입주", "청약", "임박", "특가", "할인", "세일", "프로모션", "한정", "신제품", "출시", "런칭",
            # 단순 정보성·기획
            "랭킹", "순위", "추천", "비교", "총정리", "정리해봤", "알아보자", "방법은", "이유는",
            # 연예 추가
            "팬미팅", "콘서트", "티켓", "굿즈", "직캠", "fancam", "교제", "열애", "결별", "이별",
        ]
        self.exclude_entertainment = [
            "방송", "출연", "방영", "예능", "드라마", "본방", "시청률", "mc",
            "컴백", "데뷔", "무대", "가수", "아이돌", "솔로", "앨범", "차트",
            "관객수", "박스오피스", "영화관", "개봉", "제작보고회",
            "회상했다", "회고", "당시", "과거", "추억", "인터뷰", "성공 비결",
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

        # 3. 네이버 뉴스 — 쿼리별 분리, sim만 수집 (중복 최소화)
        for q in self.naver_queries:
            eq = urllib.parse.quote(q)
            try:
                sim = requests.get(
                    f"https://openapi.naver.com/v1/search/news.json?query={eq}&display=20&sort=sim",
                    headers=h, timeout=5
                ).json()
                pool.extend(self._process_naver(sim.get('items', []), self.src_mapping['NAVER_SIM']))
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

        # 7. 다음·네이트
        pool.extend(self._generic_fetch("https://news.daum.net/ranking/popular", ".link_txt", self.src_mapping['DAUM'], limit=30))
        pool.extend(self._generic_fetch("https://news.nate.com/edit/issueup/",    ".txt_tit",  self.src_mapping['NATE'], limit=15))

        # 8. 커뮤니티 — 에펨/디시 유지 (더쿠·인스티즈는 연예 노이즈 비중 높아 제거)
        pool.extend(self._generic_fetch("https://www.fmkorea.com/best",  ".title.hotdeal_var8 a",     self.src_mapping['FMKOREA'],  "https://www.fmkorea.com", limit=25))
        pool.extend(self._generic_fetch("https://www.dcinside.com/",     ".box_best .list_best li a", self.src_mapping['DCINSIDE'], limit=15))

        # 중복 제거
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel)
                unique_pool.append(item)

        # 디버그: 채널별 수집 건수 표시
        debug_df = pd.Series([i['src'] for i in pool]).value_counts().reset_index()
        debug_df.columns = ['채널', '수집건수']
        st.markdown("#### 🔎 채널별 수집 현황 (디버그)")
        st.dataframe(debug_df, hide_index=True)
        st.markdown(f"**전체 수집: {len(pool)}건 / 중복제거 후: {len(unique_pool)}건**")

        # 정렬: 시그널·줌·고정주제·주요이슈 최상단
        priority = ['📶', '🔵', '🔥', '📢']
        return sorted(unique_pool, key=lambda x: 0 if any(k in x['src'] for k in priority) else 1)


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

    st.markdown("### 🔍 실시간 이슈 모니터링")

    c1, c2, c3 = st.columns([1, 1, 0.8])
    with c1:
        if st.button("🚀 전체 채널 스캔", use_container_width=True):
            st.session_state.data_pool = [dict(d, 선택=True) for d in ShuMonitorEngine().fetch_all_routes()]
            st.session_state.editor_key += 1
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
