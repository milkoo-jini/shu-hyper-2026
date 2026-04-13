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
        self.fixed_topics = ["월드컵", "지방선거"]
        self.exclude_ad_keywords = ["Who Is", "인물열전", "CEO스토리", "기업인사", "조언", "상담", "변호사", "법무법인", "선임", "상담문의", "전문가", "무료상담", "승소", "법률사무소", "홍보", "마케팅", "기고"]
        
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
        
        try:
            # 1-4. 네이버 영역 (24시간 필터)
            n_sim = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=20&sort=sim", headers=h).json()
            n_date = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            
            def process_naver(items, label):
                res = []
                for i in items:
                    try:
                        p_date = datetime.datetime.strptime(i['pubDate'], '%a, %d %b %Y %H:%M:%S +0900').replace(tzinfo=pytz.FixedOffset(540))
                        if (now - p_date).total_seconds() < 86400:
                            res.append({'src': label, 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'desc': i.get('description', ''), 'url': i['link']})
                    except: pass
                return res

            pool.extend(process_naver(n_sim.get('items', []), self.src_mapping['NAVER_SIM']))
            pool.extend(process_naver(n_date.get('items', []), self.src_mapping['NAVER_DATE']))

            for t in self.fixed_topics:
                t_n = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=25&sort=date", headers=h).json()
                pool.extend(process_naver(t_n.get('items', []), f"🔥 {t} 이슈"))

            # 5. 시그널 (실시간이므로 필터 생략 가능하나 구조 유지)
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            pool.extend([{'src': self.src_mapping['SIGNAL'], 'kw': i['keyword'], 'desc': '', 'url': f"https://search.naver.com/search.naver?query={i['keyword']}"} for i in sig.get('top10', [])])

            # 6. 구글 트렌드 & 뉴스 (RSS 날짜 필터)
            for target in ['G_TRENDS', 'G_NEWS']:
                url = "https://trends.google.com/trending/rss?geo=KR" if target == 'G_TRENDS' else "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
                rss = requests.get(url, headers=self.headers)
                items = BeautifulSoup(rss.text, 'xml').find_all('item')
                for i in items:
                    try:
                        p_date = datetime.datetime.strptime(i.pubDate.text[:25].strip(), '%a, %d %b %Y %H:%M:%S')
                        if (datetime.datetime.utcnow() - p_date).total_seconds() < 86400:
                            pool.append({'src': self.src_mapping[target], 'kw': i.title.text, 'desc': '', 'url': i.link.text})
                    except: pass

            # 7-8. 다음 & 네이트 (오늘 올라온 랭킹/이슈 기사 위주)
            d_res = requests.get("https://news.daum.net/ranking/popular", headers=self.headers)
            pool.extend([{'src': self.src_mapping['DAUM'], 'kw': a.text.strip(), 'desc': '', 'url': a.get('href')} for a in BeautifulSoup(d_res.text, 'html.parser').select('.link_txt')[:30]])
            
            nate = requests.get("https://news.nate.com/edit/issueup/", headers=self.headers)
            pool.extend([{'src': self.src_mapping['NATE'], 'kw': a.text.strip(), 'desc': '', 'url': "https://news.nate.com/edit/issueup/"} for a in BeautifulSoup(nate.text, 'html.parser').select('.txt_tit')[:15]])

            # 9-11. 커뮤니티 & 줌 (최신순 필터링)
            fm = requests.get("https://www.fmkorea.com/best", headers=self.headers)
            # 커뮤니티는 보통 베스트가 하루 단위로 갱신되므로 상위 20개만 수집
            pool.extend([{'src': self.src_mapping['FMKOREA'], 'kw': a.get_text().strip(), 'desc': '', 'url': 'https://www.fmkorea.com' + a.get('href')} for a in BeautifulSoup(fm.text, 'html.parser').select('.title.hotdeal_var8 a')[:20]])
            
            dc = requests.get("https://www.dcinside.com/", headers=self.headers)
            pool.extend([{'src': self.src_mapping['DCINSIDE'], 'kw': a.get_text().strip(), 'desc': '', 'url': a.get('href')} for a in BeautifulSoup(dc.text, 'html.parser').select('.box_best .list_best li a')[:15]])
            
            zum = requests.get("https://zum.com/#!/home", headers=self.headers)
            pool.extend([{'src': self.src_mapping['ZUM'], 'kw': a.text.strip(), 'desc': '', 'url': "https://zum.com/"} for a in BeautifulSoup(zum.text, 'html.parser').select('.issue_keyword .txt')[:10]])

        except: pass
        
        # [통합 필터링] 연예/회상 + 슈 님의 노이즈 키워드 + 중복 제거
        total_exclude = list(set(['방송', '출연', '방영', '예능', '드라마', '본방', '시청률', 'MC', '컴백', '데뷔', '무대', '가수', '아이돌', '솔로', '앨범', '차트', '관객수', '박스오피스', '영화관', '개봉', '제작보고회', '회상했다', '회고', '당시', '과거', '추억', '인터뷰', '성공 비결'] + self.exclude_ad_keywords))
        
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            full_text = (item['kw'] + item.get('desc', '')).replace(' ', '')
            if skel not in seen and not any(ex in full_text for ex in total_exclude):
                seen.add(skel); unique_pool.append(item)
        return sorted(unique_pool, key=lambda x: 0 if '이슈' in x['src'] or '🔥' in x['src'] else 1)

# --- UI 레이아웃 (기존 규격 엄수) ---
st.set_page_config(layout="wide", page_title="이슈 모니터링")
st.markdown("""<style>
    .block-container { padding-top: 1.5rem !important; }
    .stTextInput > div > div > input { height: 2.5rem !important; border-radius: 6px !important; }
    .stButton > button { height: 2.5rem !important; font-weight: 700 !important; border-radius: 6px !important; }
    .status-badge { background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 6px; padding: 0.5rem; text-align: center; color: #1e3a8a; font-weight: bold; height: 2.5rem; line-height: 1.5rem; }
    h3 { margin-top: -10px !important; margin-bottom: 5px !important; color: #1e3a8a; font-size: 1.5rem !important; }
    hr { margin: 1.2rem 0 !important; border-top: 1px solid #eee !important; }
    #MainMenu, header {visibility: hidden;}
</style>""", unsafe_allow_html=True)

if 'data_pool' not in st.session_state: st.session_state.data_pool = []
if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

c1, c2, c3, c4 = st.columns([2.5, 1, 1, 0.8])
with c1: st.markdown("### 🔍 실시간 통합 이슈 모니터링")
with c2:
    if st.button("🚀 전체 채널 스캔", use_container_width=True):
        st.session_state.data_pool = [dict(d, 선택=True) for d in ShuMonitorEngine().fetch_all_routes()]
        st.session_state.editor_key += 1; st.rerun()
with c3: filter_query = st.text_input("", placeholder="🔍 결과 내 필터링", label_visibility="collapsed")
with c4:
    count = len(st.session_state.data_pool)
    st.markdown(f"<div class='status-badge'>{count} 건</div>", unsafe_allow_html=True)

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
    df['수집시점'] = now.strftime('%-m/%-d %H:%M')

    edited_df = st.data_editor(
        df,
        column_config={
            "수집시점": st.column_config.TextColumn("수집시점", width=85),
            "src": st.column_config.TextColumn("출처", width=65),
            "kw": st.column_config.TextColumn("이슈 헤드라인 전문", width="large"),
            "url": st.column_config.LinkColumn("원문", display_text="🔗", width=65),
            "선택": st.column_config.CheckboxColumn("선택", width=65)
        },
        column_order=("수집시점", "src", "kw", "url", "선택"),
        hide_index=True, use_container_width=True, key=f"editor_{st.session_state.editor_key}"
    )

    if not edited_df[edited_df['선택'] == True].empty:
        output = io.BytesIO()
        edited_df[edited_df['선택'] == True].drop(columns=['선택']).to_excel(output, index=False)
        st.download_button(label="📊 선택 항목 엑셀 추출", data=output.getvalue(), file_name="Shu_Issue_Report.xlsx", use_container_width=True)
