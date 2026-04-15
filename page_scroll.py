import streamlit as st
import requests
import re
import pandas as pd
from io import BytesIO
import time

# 페이지 설정
st.set_page_config(page_title="도메인 자동 수집기", layout="wide")

st.title("🔎 카페 게시글 도메인 자동 수집")
st.caption("이 도구는 서버에서 직접 데이터를 가져오므로 노트북 보안 정책의 영향을 받지 않습니다.")

# 1. 입력 섹션
with st.sidebar:
    st.header("🔑 연결 설정")
    st.markdown("엣지 브라우저에서 복사한 **Cookie** 값을 넣어주세요.")
    cookie_input = st.text_area("네이버 쿠키(Cookie) 입력", height=200, help="F12 -> Network -> Cookie 항목 복사")

# 2. 수집 로직 함수
def collect_cafe_data(cookies_str):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
        'Cookie': cookies_str,
        'Referer': 'https://cafe.naver.com/ca-fe/cafes/25470135/articles'
    }
    
    results = []
    # 최신글 15개를 가져오는 네이버 카페 API 주소
    list_url = "https://cafe.naver.com/ca-fe/cafes/25470135/articles?query=&searchBy=0&sortBy=date&page=1&size=15"
    
    try:
        response = requests.get(list_url, headers=headers)
        articles = response.json()['result']['articles']
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, art in enumerate(articles):
            article_id = art['articleId']
            title = art['subject']
            status_text.text(f"⏳ {i+1}/15 분석 중: {title[:20]}...")
            
            # 본문 내용 가져오기
            content_url = f"https://cafe.naver.com/ca-fe/cafes/25470135/articles/{article_id}"
            content_res = requests.get(content_url, headers=headers)
            
            # 도메인 추출 (정규식)
            domain_pattern = re.compile(r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?')
            found = domain_pattern.findall(content_res.text)
            
            if found:
                for d in set(found):
                    # 불필요한 공통 도메인 필터링
                    if not any(ex in d.lower() for ex in ['naver', 'daum', 'google', 'kakaocorp', 'pstatic', 'postfiles', 'cafe', 'adpost', 'apple']):
                        results.append({
                            "발견된 도메인": d,
                            "글제목": title,
                            "글번호": article_id,
                            "링크": f"https://cafe.naver.com/notouch7/{article_id}"
                        })
            
            progress_bar.progress((i + 1) / len(articles))
            time.sleep(0.3) # 서버 부하 방지
            
        status_text.text("✅ 수집 완료!")
        return results
    except Exception as e:
        st.error(f"오류 발생: 쿠키가 만료되었거나 형식이 잘못되었습니다. ({e})")
        return None

# 3. 실행 버튼 및 결과 출력
if st.button("🚀 자동 수집 시작"):
    if not cookie_input:
        st.warning("먼저 사이드바에 네이버 쿠키를 입력해주세요!")
    else:
        with st.spinner("네이버 서버와 통신 중..."):
            data = collect_cafe_data(cookie_input)
            
            if data:
                df = pd.DataFrame(data)
                st.success(f"총 {len(df)}개의 의심 도메인을 찾았습니다!")
                st.dataframe(df, use_container_width=True)
                
                # 엑셀 다운로드 버튼
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='추출결과')
                
                st.download_button(
                    label="📥 분석 결과 엑셀 다운로드",
                    data=output.getvalue(),
                    file_name=f"domain_report_{time.strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.balloons()
            else:
                st.info("새로 발견된 도메인이 없습니다.")
