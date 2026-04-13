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
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        self.fixed_topics = ["북중미 월드컵", "지방선거"]
        self.time_limit = 86400 * 3 
        
        # [VIEW 전용] 타겟 키워드
        self.view_keywords = ["사기", "먹튀", "폐업", "연락두절", "사기사이트", "불법유통", "위조", "도용", "쇼핑몰피해", "서비스종료"]
        
        # [강력 차단] 어뷰징/광고 패턴 (VIEW 영역 집중 타겟)
        self.exclude_ad_keywords = [
            "who is", "who", "인물열전", "ceo스토리", "기업인사", "조언", "상담", 
            "변호사", "법무법인", "선임", "상담문의", "전문가", "무료상담", "승소", "법률사무소",
            "홍보", "마케팅", "기고", "대처법", "준비법", "대응방법", "성공사례", "무료진단",
            "해결사", "카톡문의", "직통전화", "전화번호", "실력있는", "알아보고있다면",
            "e종목", "클릭", "주년", "탄생", "쇼룸", "무료증정", "이벤트", "모집", "체험단"
        ]
        self.base_exclude = ['방송', '출연', '방영', '예능', '드라마', '본방', '시청률', 'mc', '컴백', '데뷔', '무대', '가수', '아이돌', '솔로', '앨범', '차트', '관객수', '박스오피스', '영화관', '개봉', '제작보고회', '회상했다', '회고', '당시', '과거', '추억', '인터뷰', '성공 비결']
        self.total_exclude = [word.lower() for word in (self.base_exclude + self.exclude_ad_keywords)]
        
        self.src_mapping = {
            'NAVER_DATE': '⏱️ 실시간 뉴스', 'NAVER_SIM': '📢 주요 이슈(네이버)',
            'NAVER_VIEW': '🔍 네이버 VIEW(피해/신고)', 'SIGNAL': '📈 급상승 시그널', 
            'G_TRENDS': '🌐 구글 트렌드', 'G_NEWS': '📰 구글 뉴스', 
            'DAUM': '🟠 다음 인기', 'NATE': '🔴 네이트 이슈', 
            'FMKOREA': '⚽ 에펨코리아(포텐)', 'DCINSIDE': '🖼️ 디시인사이드(실베)',
            'THEQOO': '🍵 더쿠(HOT)', 'INSTIZ': '🎀 인스티즈(이슈)'
        }

    def fetch_all_routes(self):
        pool = []
        h = {'X-Naver-Client-Id': self.naver_id, 'X-Naver-Client-Secret': self.naver_secret}
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.datetime.now(kst)
        
        def process_naver(items, label, is_view=False):
            res = []
            for i in items:
                try:
                    date_str = i.get('postdate') if is_view else i.get('pubDate')
                    if is_view:
                        p_date = datetime.datetime.strptime(date_str, '%Y%m%d').replace(tzinfo=kst)
                    else:
                        p_date = datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S +0900').replace(tzinfo=kst)
                    
                    title = BeautifulSoup(i['title'], 'html.parser').get_text()
                    desc = BeautifulSoup(i.get('description', ''), 'html.parser').get_text()
                    # 제목과 본문을 합쳐서 공백 제거 후 소문자로 변환 (필터링 효율 극대화)
                    target_text = (title + desc).lower().replace(' ', '')
                    
                    if (now - p_date).total_seconds() < self.time_limit:
                        # 어뷰징 키워드가 단 하나라도 포함되면 즉시 제외
                        if not any(ex.replace(' ', '').lower() in target_text for ex in self.total_exclude):
                            res.append({'src': label, 'kw': title, 'desc': desc, 'url': i.get('link')})
                except: pass
            return res

        try:
            # 1. 네이버 뉴스
            n_sim = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=20&sort=sim", headers=h).json()
            n_date = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            pool.extend(process_naver(n_sim.get('items', []), self.src_mapping['NAVER_SIM']))
            pool.extend(process_naver(n_date.get('items', []), self.src_mapping['NAVER_DATE']))

            # 2. [강화] 네이버 VIEW 개별 키워드 순회 (검색 단계 필터링 강화)
            for kw in self.view_keywords:
                # 검색 쿼리 자체에 부정 연산자 추가하여 어뷰징 원천 차단 시도
                v_url = f"https://openapi.naver.com/v1/search/blog.json?query={kw} -홍보 -마케팅 -상담 -광고 -모집 -추천&display=15&sort=date"
                v_res = requests.get(v_url, headers=h).json()
                pool.extend(process_naver(v_res.get('items', []), f"{self.src_mapping['NAVER_VIEW']}_{kw}", is_view=True))
            
            # 3. 고정 주제
            for t in self.fixed_topics:
                t_n = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=25&sort=date", headers=h).json()
                pool.extend(process_naver(t_n.get('items', []), f"🔥 {t} 이슈"))
            
            # 4. 구글 트렌드 (링크 수정 로직 유지)
            rss = requests.get("https://trends.google.com/trending/rss?geo=KR", headers=self.headers)
            items = BeautifulSoup(rss.text, 'xml').find_all('item')
            for i in items:
                title = i.title.text
                news_url = i.find('ht:news_item_url')
                link = news_url.text if news_url else i.link.text
                if not any(ex.replace(' ', '').lower() in title.lower().replace(' ', '') for ex in self.total_exclude):
                    pool.append({'src': self.src_mapping['G_TRENDS'], 'kw': title, 'desc': '', 'url': link})

            # 5. 커뮤니티 4종 (선택자 및 경로 유지)
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

            pool.extend(generic_fetch("https://www.fmkorea.com/best", ".title.hotdeal_var8 a", self.src_mapping['FMKOREA'], "https://www.fmkorea.com")[:25])
            pool.extend(generic_fetch("https://www.dcinside.com/", ".box_best .list_best li a", self.src_mapping['DCINSIDE'])[:15])
            pool.extend(generic_fetch("https://theqoo.net/hot", ".title a", self.src_mapping['THEQOO'], "https://theqoo.net")[:20])
            pool.extend(generic_fetch("https://www.instiz.net/bbs/list.php?id=pt", ".st_title a", self.src_mapping['INSTIZ'], "https://www.instiz.net")[:20])
            pool.extend(generic_fetch("https://news.daum.net/ranking/popular", ".link_txt", self.src_mapping['DAUM'])[:30])
            pool.extend(generic_fetch("https://news.nate.com/edit/issueup/", ".txt_tit", self.src_mapping['NATE'])[:15])

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

    st.markdown("---")

    if st.session_state.data_pool:
        df = pd.DataFrame(st.session_state.data_pool)
        if filter_query: df = df[df['kw'].str.contains(filter_query, case=False)]
        now = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
        df['수집시점'] = now.strftime('%m/%d %H:%M')

        edited_df = st.data_editor(
            df,
            column_config={
                "수집시점": st.column_config.TextColumn("시간", width=150),
                "src": st.column_config.TextColumn("출처", width=200),
                "kw": st.column_config.TextColumn("이슈 헤드라인 전문", width=800),
                "url": st.column_config.LinkColumn(" ", display_text="🔗", width=80),
                "선택": st.column_config.CheckboxColumn(" ", width=80)
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
