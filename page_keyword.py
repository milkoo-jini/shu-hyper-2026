import streamlit as st
import time
import re
import requests
from google import genai
from google.genai import types
from collections import deque

def run_keyword():
    st.markdown("<style>div.block-container{padding-top:2rem;}</style>", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 🔐 관리자 인증")
        password = st.text_input("접속 비밀번호", type="password", label_visibility="collapsed", placeholder="비밀번호 입력")
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
        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            return f"'{seed}' 실패 — 사용량 한도 초과"
        elif "403" in err or "PERMISSION_DENIED" in err:
            return f"'{seed}' 실패 — API 키 차단 또는 권한 없음"
        elif "400" in err or "INVALID_ARGUMENT" in err:
            return f"'{seed}' 실패 — 잘못된 요청"
        elif "503" in err or "UNAVAILABLE" in err:
            return f"'{seed}' 실패 — Gemini 서버 일시 불가"
        elif "ConnectionError" in err or "connect" in err.lower():
            return f"'{seed}' 실패 — 네트워크 차단 또는 IP 접근 불가"
        else:
            return f"'{seed}' 실패 — {e}"

    def search_naver_news(query, client_id, client_secret):
        try:
            url = "https://openapi.naver.com/v1/search/news.json"
            headers = {
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret
            }
            params = {"query": query, "display": 5, "sort": "date"}
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
        except:
            return ""

    request_times = deque()

    def wait_for_rate_limit(status_placeholder):
        now = time.time()
        while request_times and now - request_times[0] >= 60:
            request_times.popleft()
        # ✅ 수정: 28 → 10으로 낮춰 429 오류 방지
        if len(request_times) >= 10:
            wait_sec = 60 - (now - request_times[0])
            if wait_sec > 0:
                for remaining in range(int(wait_sec), 0, -1):
                    status_placeholder.warning(f"⏳ API 분당 한도 도달 — {remaining}초 후 재개...")
                    time.sleep(1)
        request_times.append(time.time())

    st.markdown("## 🎯 리스크 키워드 확장")
    st.caption("네이버 뉴스 + Gemini Google Search 기반 위험 키워드 발굴")
    st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

    col_input, col_output = st.columns([1, 2], gap="large")

    with col_input:
        st.markdown("#### 📡 대상 키워드 입력")

        gemini_api_key = st.secrets.get("GEMINI_API_KEY")
        naver_client_id = st.secrets.get("NAVER_ID")
        naver_client_secret = st.secrets.get("NAVER_SECRET")

        target_text = st.text_area(
            "키워드",
            height=340,
            placeholder="정원오\n오월드늑대\n슈퍼주니어사고\n\n한 줄에 하나씩 입력하세요.",
            label_visibility="collapsed"
        )

        seeds_preview = [t.strip() for t in target_text.split('\n') if t.strip()]
        seed_count = len(seeds_preview)
        if seed_count > 0:
            est_sec = seed_count * 7
            est_min = est_sec // 60
            est_sec_rem = est_sec % 60
            if est_min > 0:
                est_str = f"예상 소요 약 {est_min}분 {est_sec_rem}초"
            else:
                est_str = f"예상 소요 약 {est_sec_rem}초"
            st.caption(f"✅ {seed_count}개 입력됨 · {est_str}")
        else:
            st.caption("키워드를 입력해주세요.")

        st.write("")
        analyze_clicked = st.button("🚀 리스크 분석 및 나열", use_container_width=True, type="primary")

    with col_output:
        st.markdown("#### 📋 분석 결과 리스트")

        if analyze_clicked:
            st.session_state.stop_flag = False
            request_times.clear()

            if not target_text.strip():
                st.warning("분석할 단어를 입력하세요.")
                return

            if not gemini_api_key:
                st.error("GEMINI_API_KEY가 설정되지 않았습니다.")
                return

            try:
                client = genai.Client(api_key=gemini_api_key)
            except Exception as e:
                st.error(f"Gemini 클라이언트 초기화 실패: {e}")
                return

            seeds = [t.strip() for t in target_text.split('\n') if t.strip()]
            final_results = []
            seen = set()
            error_logs = []

            progress = st.progress(0)
            status = st.empty()

            for i, seed in enumerate(seeds):
                if st.session_state.stop_flag:
                    status.warning(f"⛔ 분석 중단 — {i}개 시드까지 완료, {len(final_results)}개 키워드 수집됨")
                    break

                progress.progress((i + 1) / len(seeds), text=f"🔍 {seed} 분석 중... ({i+1}/{len(seeds)})")

                try:
                    wait_for_rate_limit(status)

                    news_context = ""
                    if naver_client_id and naver_client_secret:
                        news_context += search_naver_news(
                            query=seed,
                            client_id=naver_client_id,
                            client_secret=naver_client_secret
                        )
                        news_context += search_naver_news(
                            query=f"{seed} 논란 의혹 수사",
                            client_id=naver_client_id,
                            client_secret=naver_client_secret
                        )

                    if news_context.strip():
                        naver_section = f"""
아래는 네이버에서 수집한 최신 뉴스입니다. 이 내용을 참고하되, Google Search로 추가 맥락도 파악하세요.

[네이버 뉴스]
{news_context}
"""
                    else:
                        naver_section = "네이버 뉴스 검색 결과가 없습니다. Google Search로 최신 이슈를 직접 파악하세요."

                    prompt = f"""당신은 2026년 한국 이슈 관제 전문가입니다.

'{seed}'와 관련된 최신 이슈를 파악하고 추가 모니터링이 필요한 확장 키워드를 발굴하세요.

{naver_section}

[판단 기준]
- 실제 뉴스에서 확인된 사실만 키워드로 만들 것
- 확신이 없으면 만들지 말 것
- 10개보다 3개가 낫고 3개보다 1개가 나음
- 억지로 채우지 말 것

[출력 규칙]
- 띄어쓰기 없는 표준어 조합
- 한 줄에 키워드 하나만
- 설명·번호·기호 일절 금지
- 3자 이상 15자 이하
- 실제 포털 검색창에 입력할 수 있는 자연스러운 조합
- 수사·의혹·논란·어뷰징·도덕적 리스크·허위정보·여론 악용 가능성 중심
- 일반 정보성·긍정 뉴스 제외
- 확인되지 않은 내용은 절대 만들지 말 것

[출력 예시]
{seed}수사
{seed}선거법위반
{seed}여론조작의혹"""

                    # ✅ 수정: gemini-2.5-flash → gemini-2.0-flash (403 오류 완화)
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())]
                        )
                    )

                    result_text = response.text.strip()
                    for line in result_text.split('\n'):
                        cleaned = clean_line(line)
                        if cleaned and cleaned not in seen:
                            if 3 <= len(cleaned) <= 15:
                                seen.add(cleaned)
                                final_results.append(cleaned)

                except Exception as e:
                    error_logs.append(handle_api_error(e, seed))

            progress.empty()

            if final_results:
                now_str = time.strftime("%H:%M")
                if not st.session_state.stop_flag:
                    status.success(f"✅ 완료! 총 {len(final_results)}개 키워드 · {now_str}")
                st.text_area(
                    "전체 복사 영역",
                    value="\n".join(final_results),
                    height=480,
                    label_visibility="collapsed"
                )
            else:
                if not st.session_state.stop_flag:
                    status.empty()
                    st.error("결과가 없습니다. 오류 메시지를 확인하세요.")

            if error_logs:
                with st.expander(f"⚠️ 오류 {len(error_logs)}건 확인하기"):
                    for err in error_logs:
                        st.caption(err)

        else:
            st.text_area(
                "결과 대기",
                value="",
                height=480,
                placeholder="왼쪽에서 키워드를 입력하고\n분석 버튼을 눌러주세요.",
                label_visibility="collapsed",
                disabled=True
            )
