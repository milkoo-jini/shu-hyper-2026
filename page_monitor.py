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
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        self.fixed_topics = ["북중미 월드컵", "지방선거"]
        self.time_limit = 86400 * 3 
        
        # [차단 필터]
        self.exclude_ad_keywords = [
            "who is", "who", "인물열전", "ceo스토리", "기업인사", "조언", "상담", 
            "변호사", "법무법인", "선임", "상담문의", "전문가", "무료상담", "승소", "법률사무소",
            "홍보", "마케팅", "기고", "대처법", "준비법", "대응방법", "성공사례", "무료진단",
            "해결사", "카톡문의", "직통전화", "전화번호", "실력있는", "알아보고있다면",
            "e종목", "클릭", "주년", "탄생", "쇼룸", "무료증정", "이벤트", "모집", "체험단"
        ]
        self.base_exclude = ['방송', '출연', '방영', '예능', '드라마', '본방', '시청률', 'mc', '컴백', '데뷔', '무대', '가수', '아이돌', '솔로', '앨범', '차트', '관객수', '박스오피스', '영화관', '개봉', '제작보고회', '회상했다', '회고', '당시', '과거', '추억', '인터뷰', '성공 비결']
        self.total_exclude = [word.lower() for word in (self.base_exclude + self.exclude_ad_keywords)]
        
        # [이름표 정리] VIEW 관련 명칭을 완전히 제거했습니다.
        self.src_mapping = {
            'NAVER_DATE': '⏱️ 네이버 실시간 뉴스', 
            'NAVER_SIM': '📢 네이버 주요 뉴스',
            'G_NEWS': '📰 구글 뉴스 검색', 
            'G_TRENDS': '🌐 구글 트렌드(실시간)', 
            'DAUM': '🟠 다음 인기 뉴스', 
            'NATE': '🔴 네이트 이슈업', 
            'FMKOREA': '⚽ 에펨코리아', 
            'DCINSIDE': '🖼️ 디시인사이드',
            'THEQOO': '🍵 더쿠(HOT)', 
            'INSTIZ': '🎀 인스티즈'
        }

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.datetime.now(kst)
        
        raw_keywords = "논란|사건|사고|폭로|의혹|경고|피해|주의|제보"
        q_encoded = urllib.parse.quote(raw_keywords)

        def process_naver(items, label):
            res = []
            if not items: return res
            for i in items:
                try:
                    p_date = datetime.datetime.strptime(i.get('pubDate'), '%a, %d %b %Y %H:%M:%S +0900').replace(tzinfo=kst)
                    title = BeautifulSoup(i['title'], 'html.parser').get_text()
                    desc = BeautifulSoup(i.get('description', ''), 'html.parser').get_text()
                    target_text = (title + desc).lower().replace(' ', '')
                    if (now - p_date).total_seconds() < self.time_limit:
                        if not any(ex.replace(' ', '').lower() in target_text for ex in self.total_exclude):
                            res.append({'src': label, 'kw': title, 'desc': desc, 'url': i.get('link')})
                except: pass
            return res

        try:
            # 1. 네이버 뉴스 (블로그/카페 API 호출 코드는 아예 삭제됨)
            n_sim = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={q_encoded}&display=30&sort=sim", headers=h).json()
            n_date = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={q_encoded}&display=50&sort=date", headers=h).json()
            pool.extend(process_naver(n_sim.get('items', []), self.src_mapping['NAVER_SIM']))
            pool.extend(process_naver(n_date.get('items', []), self.src_mapping['NAVER_DATE']))

            # 2. 구글 뉴스
            g_rss_url = f"https://news.google.com/rss/search?q={q_encoded}&hl=ko&gl=KR&ceid=KR:ko"
            g_news_res = requests.get(g_rss_url, headers=self.headers)
            g_items = BeautifulSoup(g_news_res.text, 'xml').find_all('item')
            for i in g_items[:30]:
                title = i.title.text
                if not any(ex.replace(' ', '').lower() in title.lower().replace(' ', '') for ex in self.total_exclude):
                    pool.append({'src': self.src_mapping['G_NEWS'], 'kw': title, 'desc': '', 'url': i.link.text})

            # 3. 구글 트렌드
            rss = requests.get("https://trends.google.com/trending/rss?geo=KR", headers=self.headers)
            items = BeautifulSoup(rss.text, 'xml').find_all('item')
            for i in items:
                title = i.title.text
                news_url = i.find('ht:news_item_url')
                link = news_url.text if news_url else i.link.text
                if not any(ex.replace(' ', '').lower() in title.lower().replace(' ', '') for ex in self.total_exclude):
                    pool.append({'src': self.src_mapping['G_TRENDS'], 'kw': title, 'desc': '', 'url': link})

            # 4. 공통 수집 (다음/네이트/커뮤니티)
            def generic_fetch(url, selector, label, base_url=""):
                try:
                    res = requests.get(url, headers=self.headers, timeout=10)
                    soup = BeautifulSoup(res.text, 'html.parser')
                    items = soup.select(selector)
                    out = []
                    for a in items:
                        title = a.text.strip()
                        if title and not any(ex.replace(' ', '').lower() in title.lower().replace(' ', '') for ex in self.total_exclude):
                            link = a.get('href')
                            if link and not link.startswith('http'): link = base_url + link
                            out.append({'src': label, 'kw': title, 'desc': '', 'url': link})
                    return out
                except: return []

            pool.extend(generic_fetch("https://news.daum.net/ranking/popular", ".link_txt", self.src_mapping['DAUM'])[:40])
            pool.extend(generic_fetch("https://news.nate.com/edit/issueup/", ".txt_tit", self.src_mapping['NATE'])[:20])
            pool.extend(generic_fetch("https://www.fmkorea.com/best", ".title.hotdeal_var8 a", self.src_mapping['FMKOREA'], "https://www.fmkorea.com")[:25])
            pool.extend(generic_fetch("https://www.dcinside.com/", ".box_best .list_best li a", self.src_mapping['DCINSIDE'])[:15])
            pool.extend(generic_fetch("https://theqoo.net/hot", ".title a", self.src_mapping['THEQOO'], "https://theqoo.net")[:20])
            pool.extend(generic_fetch("https://www.instiz.net/bbs/list.php?id=pt", ".st_title a", self.src_mapping['INSTIZ'], "https://www.instiz.net")[:20])

        except: pass
        
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return sorted(unique_pool, key=lambda x: 0 if '이슈' in x['src'] or '🔥' in x['src'] else 1)

def run_monitor():
    st.markdown("""
        <style>
            [data-testid="stHeader"], [data-testid="stDecoration"] { display: none !important; }
            .main .block-container { margin-top: 150px !important; max-width: 95% !important; }
            .status-badge { 
                background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 6px; 
                padding: 0.5rem; text-align: center; color: #1e3a8a; font-weight: bold; 
                height: 2.8rem; line-height: 1.8rem; 
            }
        </style>
    """, unsafe_allow_html=True)

    if 'data_pool' not in st.session_state: st.session_state.data_pool = []
    if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

    st.markdown("### 🔍 실시간 종합 뉴스 & 이슈 모니터링")
    
    c1, c2, c3 = st.columns([1, 1, 0.8])
    with c1:
        if st.button("🚀 전체 채널 스캔 (뉴스 중심)", use_container_width=True):
            st.session_state.data_pool = [dict(d, 선택=True) for d in ShuMonitorEngine().fetch_all_routes()]
            st.session_state.editor_key += 1; st.rerun()
    with c2: filter_query = st.text_input("", placeholder="🔍 결과 내 필터링", label_visibility="collapsed")
    with c3: st.markdown(f"<div class='status-badge'>{len(st.session_state.data_pool)}건</div>", unsafe_allow_html=True)

    st.markdown("---")

    if st.session_state.data_pool:
        df = pd.DataFrame(st.session_state.data_pool)
        if filter_query: df = df[df['kw'].str.contains(filter_query, case=False)]
        df['수집시점'] = datetime.datetime.now(pytz.timezone('Asia/Seoul')).strftime('%m/%d %H:%M')

        st.data_editor(
            df,
            column_config={
                "수집시점": st.column_config.TextColumn("시간", width=150),
                "src": st.column_config.TextColumn("출처", width=200),
                "kw": st.column_config.TextColumn("이슈 헤드라인 전문", width=800),
                "url": st.column_config.LinkColumn(" ", display_text="🔗", width=80),
                "선택": st.column_config.CheckboxColumn(" ", width=80)
            },
            column_order=("수집시점", "src", "kw", "url", "선택"),
            hide_index=True, use_container_width=False, height=600,
            key=f"editor_{st.session_state.editor_key}"
        )

if __name__ == "__main__":
    run_monitor()
