import streamlit as st
import time
import re
import requests
from groq import Groq
from collections import deque

def run_keyword():
    with st.sidebar:
        st.title("🔐 관리자 인증")
        password = st.text_input("접속 비밀번호", type="password")
        st.divider()
        if st.button("⛔ 분석 중단", use_container_width=True):
            st.session_state.stop_flag = True

    if "stop_flag" not in st.session_state:
        st.session_state.stop_flag = False

    admin_pw = st.secrets.get("ADMIN_PASSWORD", "1234")
    if password != admin_pw:
        st.info("왼쪽 사이드바에 비밀번호를 입력해주세요.") if password == "" else st.error("비밀번호가 올바르지 않습니다.")
        return

    def clean_line(line):
        line = re.sub(r'^[\d\.\-\*\#\s]+', '', line)
        return line.strip()

    def handle_api_error(e, seed):
        err = str(e)
        if "429" in err or "rate_limit" in err.lower():
            st.error(f"'{seed}' 실패 — 사용량 한도 초과. 잠시 후 재시도하세요.")
        elif "401" in err or "invalid_api_key" in err.lower():
            st.error(f"'{seed}' 실패 — API 키 오류. 키를 확인하세요.")
        elif "503" in err or "unavailable" in err.lower():
            st.error(f"'{seed}' 실패 — 서버 일시 불가. 잠시 후 재시도하세요.")
        elif "ConnectionError" in err or "connect" in err.lower():
            st.error(f"'{seed}' 실패 — 네트워크 차단 또는 IP 접근 불가.")
        else:
            st.error(f"'{seed}' 실패 — 알 수 없는 오류: {e}")

    def search_naver_news(query, client_id, client_secret):
        url = "https://openapi.naver.com/v1/search/news.json"
        headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret
        }
        params = {
            "query": query,
            "display": 5,
            "sort": "date"
        }
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            return ""

        items = response.json().get("items", [])
        if not items:
            return ""

        news_context = ""
        for item in items:
            title = re.sub(r'<.*?>', '', item.get("title", ""))
            description = re.sub(r'<.*?>', '', item.get("description", ""))
            news_context += f"- {title}: {description}\n"

        return news_context

    request_times = deque()

    def wait_for_rate_limit(status_placeholder):
        now = time.time()
        while request_times and now - request_times[0] >= 60:
            request_times.popleft()
        if len(request_times) >= 30:
            wait_sec = 60 - (now - request_times[0])
            if wait_sec > 0:
                for remaining in range(int(wait_sec), 0, -1):
                    status_placeholder.warning(f"⏳ Groq 분당 한도 도달 — {remaining}초 후 재개...")
                    time.sleep(1)
        request_times.append(time.time())

    col_input, col_output = st.columns([1, 2], gap="large")

    with col_input:
        st.markdown("### 🎯 리스크 확장 설정")
        st.info("네이버 뉴스 검색 기반 실질적 위험 키워드 발굴")

        groq_api_key = st.secrets.get("GROQ_API_KEY")
        naver_client_id = st.secrets.get("NAVER_ID")
        naver_client_secret = st.secrets.get("NAVER_SECRET")

        target_text = st.text_area(
            "📡 대상 키워드 입력", height=250,
            placeholder="정원오\n김병기\n대전늑대",
            help="한 줄에 하나씩 입력하세요."
        )
        analyze_clicked = st.button("🚀 리스크 분석 및 나열", use_container_width=True)

    with col_output:
        st.markdown("### 📋 분석 결과 리스트")

        if analyze_clicked:
            st.session_state.stop_flag = False
            request_times.clear()

            if not target_text.strip():
                st.warning("분석할 단어를 입력하세요.")
                return

            if not groq_api_key:
                st.error("GROQ_API_KEY가 설정되지 않았습니다.")
                return

            if not naver_client_id or not naver_client_secret:
                st.error("NAVER_ID 또는 NAVER_SECRET이 설정되지 않았습니다.")
                return

            try:
                groq_client = Groq(api_key=groq_api_key)
            except Exception as e:
                st.error(f"Groq 클라이언트 초기화 실패: {e}")
                return

            seeds = [t.strip() for t in target_text.split('\n') if t.strip()]
            final_results = []
            seen = set()

            progress = st.progress(0)
            status = st.empty()

            for i, seed in enumerate(seeds):
                if st.session_state.stop_flag:
                    status.warning(f"⛔ 분석 중단 — {i}개 시드까지 완료, {len(final_results)}개 키워드 수집됨")
                    break

                progress.progress((i + 1) / len(seeds), text=f"{seed} 분석 중... ({i+1}/{len(seeds)})")

                try:
                    wait_for_rate_limit(status)

                    # 1단계 네이버 뉴스 검색
                    news_context = search_naver_news(
                        query=f"{seed} 논란 의혹 수사",
                        client_id=naver_client_id,
                        client_secret=naver_client_secret
                    )

                    # 뉴스 없으면 건너뜀
                    if not news_context.strip():
                        st.warning(f"'{seed}' 관련 뉴스를 찾지 못했습니다. 건너뜁니다.")
                        continue

                    # 2단계 Groq로 키워드 발굴
                    prompt = f"""당신은 2026년 한국 이슈 관제 전문가입니다.

아래는 '{seed}'에 대한 최신 네이버 뉴스입니다.

[최신 뉴스]
{news_context}

위 뉴스에서 명확히 확인된 이슈만 기반으로 키워드를 발굴하세요.

[판단 기준]
- 뉴스에 직접 언급된 사실만 키워드로 만들 것
- 확신이 없으면 만들지 말 것
- 10개보다 3개가 낫고, 3개보다 1개가 나음
- 억지로 채우지 말 것

[출력 규칙]
- 띄어쓰기 없는 표준어 조합
- 한 줄에 키워드 하나만
- 설명·번호·기호 일절 금지
- 3자 이상 15자 이하
- 실제 포털 검색창에 입력할 수 있는 자연스러운 조합
- 수사·의혹·논란·어뷰징·도덕적 리스크·허위정보·여론 악용 가능성 중심
- 일반 정보성·긍정 뉴스 제외
- 뉴스에 없는 내용은 절대 만들지 말 것

[출력 예시]
{seed}수사
{seed}선거법위반
{seed}여론조작의혹"""

                    response = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.1
                    )

                    result_text = response.choices[0].message.content
                    for line in result_text.strip().split('\n'):
                        cleaned = clean_line(line)
                        if cleaned and cleaned not in seen:
                            if 3 <= len(cleaned) <= 15:
                                seen.add(cleaned)
                                final_results.append(cleaned)

                except Exception as e:
                    handle_api_error(e, seed)

            progress.empty()

            if final_results:
                if not st.session_state.stop_flag:
                    status.success(f"✅ 완료! 총 {len(final_results)}개 키워드")
                st.text_area("전체 복사 영역", value="\n".join(final_results), height=600)
            else:
                if not st.session_state.stop_flag:
                    status.error("결과가 없습니다. 오류 메시지를 확인하세요.")

        else:
            st.write("왼쪽에서 키워드를 입력하고 버튼을 눌러주세요.")
