import streamlit as st
import requests
import re
import pandas as pd
from io import BytesIO
import time

def run_domain_collector(): # app.py에서 호출할 수 있도록 함수로 정의
    st.title("🔎 카페 게시글 도메인 자동 수집")
    
    st.markdown("### 🔑 연결 설정")
    cookie_input = st.text_area("네이버 쿠키(Cookie) 입력", height=150)

    if st.button("🚀 자동 수집 시작", use_container_width=True):
        if not cookie_input:
            st.warning("먼저 네이버 쿠키를 입력해주세요!")
            return

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
            'Cookie': cookie_input,
            'Referer': 'https://cafe.naver.com/ca-fe/cafes/25470135/articles'
        }
        
        results = []
        # 카페 API 주소
        list_url = "https://cafe.naver.com/ca-fe/cafes/25470135/articles?query=&searchBy=0&sortBy=date&page=1&size=15"
        
        try:
            with st.spinner("서버에서 데이터 분석 중..."):
                response = requests.get(list_url, headers=headers)
                articles = response.json()['result']['articles']
                
                prog = st.progress(0)
                for i, art in enumerate(articles):
                    article_id = art['articleId']
                    title = art['subject']
                    
                    content_url = f"https://cafe.naver.com/ca-fe/cafes/25470135/articles/{article_id}"
                    content_res = requests.get(content_url, headers=headers)
                    
                    domain_pattern = re.compile(r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?')
                    found = domain_pattern.findall(content_res.text)
                    
                    if found:
                        for d in set(found):
                            if not any(ex in d.lower() for ex in ['naver', 'daum', 'google', 'kakaocorp', 'pstatic', 'cafe']):
                                results.append({"도메인": d, "글제목": title, "링크": f"https://cafe.naver.com/notouch7/{article_id}"})
                    prog.progress((i + 1) / len(articles))
                    time.sleep(0.3)
                
                if results:
                    df = pd.DataFrame(results)
                    st.success(f"✅ {len(df)}개 발견!")
                    st.dataframe(df, use_container_width=True)
                    
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False)
                    st.download_button("📥 엑셀 다운로드", output.getvalue(), "result.xlsx", use_container_width=True)
                else:
                    st.info("발견된 도메인이 없습니다.")
        except Exception as e:
            st.error(f"쿠키 오류 또는 접근 제한: {e}")
