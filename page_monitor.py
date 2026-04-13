import streamlit as st
import pandas as pd
import datetime, re, requests, io
from bs4 import BeautifulSoup
import pytz

class ShuMonitorEngine:
    def __init__(self):
        try:
            self.naver_id = st.secrets["NAVER_ID"]
            self.naver_secret = st.secrets["NAVER_SECRET"]
        except:
            self.naver_id = self.naver_secret = None
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        self.fixed_topics = ["북중미 월드컵", "지방선거"]
        self.time_limit = 86400 * 3 
        
        # 제외 단어 리스트
        self.exclude_ad_keywords = [
            "who is", "who", "인물열전", "ceo스토리", "기업인사", "조언", "상담", 
            "변호사", "법무법인", "선임", "상담문의", "전문가", "무료상담", "승소", 
            "법률사무소", "홍보", "마케팅", "기고",
            "e종목", "클릭", "주년", "탄생", "쇼룸"
        ]
        self.base_exclude = ['방송', '출연', '방영', '예능', '드라마', '본방', '시청률', 'mc', '컴백', '데뷔', '무대', '가수', '아이돌', '솔로', '앨범', '차트', '관객수', '박스오피스', '영화관', '개봉', '제작보고회', '회상했다', '회고', '당시', '과거', '추억', '인터뷰', '성공 비결']
        self.total_exclude = [word.lower() for word in (self.base_exclude + self.exclude_ad_keywords)]
        
        self.src_mapping = {
            'NAVER_DATE': '⏱️ 실시간 뉴스', 'NAVER_SIM': '📢 주요 이슈(네이버)',
            'SIGNAL': '📈 급상승 시그널', 'G_TRENDS': '🌐 구글 트렌드',
            'G_NEWS': '📰 구글 뉴스', 'DAUM': '🟠 다음 인기',
            'NATE': '🔴 네이트 이슈', 'ZUM': '🔵 줌 실검',
            'FMKOREA': '⚽ 에펨코리아(베스트)', 'DCINSIDE': '🖼️ 디시인사이드'
        }

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.datetime.now(kst)
        
        # 필터링 통합 함수
        def process_naver(items, label):
            res = []
            for i in items:
                try:
                    p_date = datetime.datetime.strptime(i['pubDate'], '%a, %d %b %Y %H:%M:%S +0900').replace(tzinfo=kst)
                    title = BeautifulSoup(i['title'], 'html.parser').get_text()
                    desc = i.get('description', '')
                    target_text = (title + desc).lower().replace(' ', '')
                    if (now - p_date).total_seconds() < self.time_limit:
                        # [핵심] 고정 주제도 여기서 걸러집니다
                        if not any(ex.replace(' ', '').lower() in target_text for ex in self.total_exclude):
                            res.append({'src': label, 'kw': title, 'desc': desc, 'url': i['link']})
                except: pass
            return res

        try:
            # 1. 네이버 기본 뉴스
            n_sim = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=20&sort=sim", headers=h).json()
            n_date = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            pool.extend(process_naver(n_sim.get('items', []), self.src_mapping['NAVER_SIM']))
            pool.extend(process_naver(n_date.get('items', []), self.src_mapping['NAVER_DATE']))
            
            # 2. 고정 주제 (이제 검역소 process_naver를 똑같이 통과함)
            for t in self.fixed_topics:
                t_n = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=25&sort=date", headers=h).json()
                pool.extend(process_naver(t_n.get('items', []), f"🔥 {t} 이슈"))
            
            # 3. 시그널, 구글 등 기타 채널
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            pool.extend([{'src': self.src_mapping['SIGNAL'], 'kw': i['keyword'], 'desc': '', 'url': f"https://search.naver.com/search.naver?query={i['keyword']}"} for i in sig.get('top10', [])])
            for target in ['G_TRENDS', 'G_NEWS']:
                url = "https://trends.google.com/trending/rss?geo=KR" if target == 'G_TRENDS' else "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
                rss = requests.get(url, headers=self.headers)
                items = BeautifulSoup(rss.text, 'xml').find_all('item')
                for i in items:
                    try:
                        p_date = datetime.datetime.strptime(i.pubDate.text[:25].strip(), '%a, %d %b %Y %H:%M:%S')
                        p_date = pytz.utc.localize(p_date).astimezone(kst)
                        if (now - p_date).total_seconds() < self.time_limit:
                            if not any(ex.replace(' ', '').lower() in i.title.text.lower().replace(' ', '') for ex in self.total_exclude):
                                pool.append({'src': self.src_mapping[target], 'kw': i.title.text, 'desc': '', 'url': i.link.text})
                    except: pass
            
            def generic_fetch(url, selector, label, base_url=""):
                res = requests.get(url, headers=self.headers)
                soup = BeautifulSoup(res.text, 'html.parser')
                items = soup.select(selector)
                out = []
                for a in items:
                    title = a.text.strip()
                    if not any(ex.replace(' ', '').lower() in title.lower().replace(' ', '') for ex in self.total_exclude):
                        link = a.get('href')
                        if link and not link.startswith('http'): link = base_url + link
                        out.append({'src': label, 'kw': title, 'desc': '', 'url': link})
                return out

            pool.extend(generic_fetch("https://news.daum.net/ranking/popular", ".link_txt", self.src_mapping['DAUM'])[:30])
            pool.extend(generic_fetch("https://news.nate.com/edit/issueup/", ".txt_tit", self.src_mapping['NATE'])[:15])
            pool.extend(generic_fetch("https://www.fmkorea.com/best", ".title.hotdeal_var8 a", self.src_mapping['FMKOREA'], "https://www.fmkorea.com")[:20])
            pool.extend(generic_fetch("https://www.dcinside.com/", ".box_best .list_best li a", self.src_mapping['DCINSIDE'])[:15])

        except: pass
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            if skel not in seen:
                seen.add(skel); unique_pool.append(item)
        return sorted(unique_pool, key=lambda x: 0 if '이슈' in x['src'] or '🔥' in x['src'] else 1)

def run_monitor():
    # 상단 가려짐 방지 강화 CSS
    st.markdown("""
        <style>
            [data-testid="stHeader"], [data-testid="stDecoration"] { 
                display: none !important; 
            }
            .main .block-container {
                margin-top: 150px !important;
                padding-top: 0px !important;
                max-width: 95% !important;
            }
            .status-badge { 
                background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 6px; 
                padding: 0.5rem; text-align: center; color: #1e3a8a; font-weight: bold; 
                height: 2.8rem; line-height: 1.8rem; 
            }
        </style>
    """, unsafe_allow_html=True)

    if 'data_pool' not in st.session_state: st.session_state.data_pool = []
    if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

    st.markdown("### 🔍 실시간 이슈 모니터링")
    
    c1, c2, c3 = st.columns([1, 1, 0.8])
    with c1:
        if st.button("🚀 전체 채널 스캔", use_container_width=True):
            st.session_state.data_pool = [dict(d, 선택=True) for d in ShuMonitorEngine().fetch_all_routes()]
            st.session_state.editor_key += 1; st.rerun()
    with c2: filter_query = st.text_input("", placeholder="🔍 결과 내 필터링", label_visibility="collapsed")
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
        if filter_query: df = df[df['kw'].str.contains(filter_query, case=False)]
        now = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
        df['수집시점'] = now.strftime('%m/%d %H:%M')

        edited_df = st.data_editor(
            df,
            column_config={
                "수집시점": st.column_config.TextColumn("시간", width=80),
                "src": st.column_config.TextColumn("출처", width=120),
                "kw": st.column_config.TextColumn("이슈 헤드라인 전문", width=2500),
                "url": st.column_config.LinkColumn(" ", display_text="🔗", width=40),
                "선택": st.column_config.CheckboxColumn(" ", width=40)
            },
            column_order=("수집시점", "src", "kw", "url", "선택"),
            hide_index=True, 
            use_container_width=False,
            height=600,
            key=f"editor_{st.session_state.editor_key}"
        )

        if not edited_df[edited_df['선택'] == True].empty:
            output = io.BytesIO()
            edited_df[edited_df['선택'] == True].drop(columns=['선택']).to_excel(output, index=False, engine='openpyxl')
            st.download_button(label="📊 선택 항목 엑셀 추출", data=output.getvalue(), file_name="Shu_Issue_Report.xlsx", use_container_width=True)

if __name__ == "__main__":
    run_monitor()
