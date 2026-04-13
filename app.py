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
        try:
            n_sim = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=20&sort=sim", headers=h).json()
            pool.extend([{'src': self.src_mapping['NAVER_SIM'], 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'desc': i.get('description', ''), 'url': i['link']} for i in n_sim.get('items', [])])
            n_date = requests.get("https://openapi.naver.com/v1/search/news.json?query=논란 사건 사고&display=50&sort=date", headers=h).json()
            pool.extend([{'src': self.src_mapping['NAVER_DATE'], 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'desc': i.get('description', ''), 'url': i['link']} for i in n_date.get('items', [])])
            
            for t in self.fixed_topics:
                t_n = requests.get(f"https://openapi.naver.com/v1/search/news.json?query={t}&display=25&sort=date", headers=h).json()
                src_name = f"⚽ {t}" if t == "월드컵" else f"🗳️ {t} 이슈"
                pool.extend([{'src': src_name, 'kw': BeautifulSoup(i['title'], 'html.parser').get_text(), 'desc': i.get('description', ''), 'url': i['link']} for i in t_n.get('items', [])])
            
            # 11개 채널 수집 로직 (유지)
            sig = requests.get("https://api.signal.bz/news/realtime", headers=self.headers).json()
            pool.extend([{'src': self.src_mapping['SIGNAL'], 'kw': i['keyword'], 'desc': '', 'url': f"https://search.naver.com/search.naver?query={i['keyword']}"} for i in sig.get('top10', [])])
            nate = requests.get("https://news.nate.com/edit/issueup/", headers=self.headers)
            pool.extend([{'src': self.src_mapping['NATE'], 'kw': a.text.strip(), 'desc': '', 'url': "https://news.nate.com/edit/issueup/"} for a in BeautifulSoup(nate.text, 'html.parser').select('.txt_tit')[:10]])
            zum = requests.get("https://zum.com/#!/home", headers=self.headers)
            pool.extend([{'src': self.src_mapping['ZUM'], 'kw': a.text.strip(), 'desc': '', 'url': "https://zum.com/"} for a in BeautifulSoup(zum.text, 'html.parser').select('.issue_keyword .txt')[:10]])
            g_trends = requests.get("https://trends.google.com/trending/rss?geo=KR", headers=self.headers)
            pool.extend([{'src': self.src_mapping['G_TRENDS'], 'kw': i.title.text, 'desc': '', 'url': i.link.text if i.link else ""} for i in BeautifulSoup(g_trends.text, 'xml').find_all('item')[:10]])
            d_res = requests.get("https://news.daum.net/ranking/popular", headers=self.headers)
            pool.extend([{'src': self.src_mapping['DAUM'], 'kw': a.text.strip(), 'desc': '', 'url': a.get('href')} for a in BeautifulSoup(d_res.text, 'html.parser').select('.link_txt')[:30]])
            g_news = requests.get("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", headers=self.headers)
            pool.extend([{'src': self.src_mapping['G_NEWS'], 'kw': i.title.text, 'desc': '', 'url': i.link.text} for i in BeautifulSoup(g_news.text, 'xml').find_all('item')[:15]])
            fm = requests.get("https://www.fmkorea.com/best", headers=self.headers)
            pool.extend([{'src': self.src_mapping['FMKOREA'], 'kw': a.get_text().strip(), 'desc': '', 'url': 'https://www.fmkorea.com' + a.get('href')} for a in BeautifulSoup(fm.text, 'html.parser').select('.title.hotdeal_var8 a')[:20]])
            dc = requests.get("https://www.dcinside.com/", headers=self.headers)
            pool.extend([{'src': self.src_mapping['DCINSIDE'], 'kw': a.get_text().strip(), 'desc': '', 'url': a.get('href')} for a in BeautifulSoup(dc.text, 'html.parser').select('.box_best .list_best li a')[:15]])
        except: pass
        
        exclude_kws = ['방송', '출연', '방영', '예능', '드라마', '본방', '시청률', 'MC', '컴백', '데뷔', '무대', '가수', '아이돌', '솔로', '앨범', '차트', '관객수', '박스오피스', '영화관', '개봉', '제작보고회', '회상했다', '회고', '당시', '과거', '추억', '인터뷰', '성공 비결']
        seen, unique_pool = set(), []
        for item in pool:
            skel = re.sub(r'\s+', '', item['kw'])
            full_text = (item['kw'] + item.get('desc', '')).replace(' ', '')
            if skel not in seen and not any(ex in full_text for ex in exclude_kws):
                seen.add(skel); unique_pool.append(item)
        return sorted(unique_pool, key=lambda x: 0 if x['src'] in ['⚽ 월드컵', '🗳️ 지방선거 이슈'] else 1)

# --- [UI: 정밀 스타일링 및 박스 필터 적용] ---
st.set_page_config(layout="wide", page_title="이슈 모니터링")
st.markdown("""<style>
    .block-container { padding-top: 1.5rem !important; }
    /* 컨트롤 영역 박스화 */
    .control-panel { 
        background-color: #f8f9fc; 
        border: 1px solid #e3e6f0; 
        border-radius: 10px; 
        padding: 1.2rem; 
        margin-bottom: 1.5rem; 
    }
    .stTextInput > div > div > input { height: 2.6rem !important; border-radius: 8px !important; border: 1px solid #d1d3e2 !important; }
    .stButton > button { height: 2.6rem !important; font-weight: 700 !important; border-radius: 8px !important; }
    .status-box { background-color: #ffffff; border: 1px solid #e3e6f0; border-radius: 8px; padding: 0.5rem; text-align: center; color: #4e73df; font-weight: 800; height: 2.6rem; line-height: 1.5rem; }
    h3 { margin-top: -5px !important; margin-bottom: 10px !important; color: #2e59d9; font-size: 1.6rem !important; }
    hr { margin: 1rem 0 !important; opacity: 0.3; }
    #MainMenu, header {visibility: hidden;}
</style>""", unsafe_allow_html=True)

if 'data_pool' not in st.session_state: st.session_state.data_pool = []
if 'editor_key' not in st.session_state: st.session_state.editor_key = 0

# [상단 박스 영역 시작]
with st.container():
    st.markdown('<div class="control-panel">', unsafe_allow_html=True)
    
    # 1층: 타이틀 및 주요 도구
    c1, c2, c3, c4 = st.columns([2.5, 1, 1.2, 0.8])
    with c1: st.markdown("### 🛡️ ISSUE COMMAND CENTER")
    with c2:
        if st.button("🚀 실시간 통합 스캔", use_container_width=True):
            st.session_state.data_pool = [dict(d, 선택=True) for d in ShuMonitorEngine().fetch_all_routes()]
            st.session_state.editor_key += 1; st.rerun()
    with c3: filter_query = st.text_input("", placeholder="🔍 결과 내 키워드 필터링", label_visibility="collapsed")
    with c4:
        count = len(st.session_state.data_pool)
        st.markdown(f"<div class='status-box'>{count} 건</div>", unsafe_allow_html=True)

    # 2층: 미세 조정 버튼 (색감을 연하게 배경과 분리)
    _, b1, b2 = st.columns([8.2, 0.9, 0.9])
    with b1:
        if st.button("전체선택", use_container_width=True, help="모든 항목 체크"):
            for item in st.session_state.data_pool: item['선택'] = True
            st.session_state.editor_key += 1; st.rerun()
    with b2:
        if st.button("선택해제", use_container_width=True, help="모든 체크 해제"):
            for item in st.session_state.data_pool: item['선택'] = False
            st.session_state.editor_key += 1; st.rerun()
            
    st.markdown('</div>', unsafe_allow_html=True)
# [상단 박스 영역 종료]

# [데이터 리스트 영역]
if st.session_state.data_pool:
    df = pd.DataFrame(st.session_state.data_pool)
    if filter_query: df = df[df['kw'].str.contains(filter_query, case=False)]
    
    now = datetime.datetime.now(pytz.timezone('Asia/Seoul'))
    df['수집시점'] = now.strftime('%-m/%-d %H:%M')

    # 데이터 에디터 (폭 85-65-65-65 엄수)
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

    # 엑셀 다운로드 (하단 배치)
    if not edited_df[edited_df['선택'] == True].empty:
        output = io.BytesIO()
        edited_df[edited_df['선택'] == True].drop(columns=['선택']).to_excel(output, index=False)
        st.download_button(label="📊 선택 항목 엑셀 리포트 생성", data=output.getvalue(), file_name="Shu_Issue_Report.xlsx", use_container_width=True)
