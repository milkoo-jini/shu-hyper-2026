import streamlit as st
import time
import re
from groq import Groq
from tavily import TavilyClient
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

    # 분당 30건 제한 제어
    # 최근 1분 안에 호출된 시각을 기록
    # 30건 도달 시 가장 오래된 호출로부터 60초가 지날 때까지 대기
    request_times = deque()

    def wait_for_rate_limit(status_placeholder):
        now = time.time()
        # 1분 지난 기록 제거
        while request_times and now - request_times[0] >= 60:
            request_times.popleft()
        # 30건 도달 시 대기
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
        st.info("최신 뉴스 검색 기반 실질적 위험 키워드 발굴")

        groq_api_key = st.secrets.get("GROQ_API_KEY")
        tavily_api_key = st.secrets.get("TAVILY_API_KEY")

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

            if not tavily_api_key:
                st.error("TAVILY_API_KEY가 설정되지 않았습니다.")
                return

            try:
                groq_client = Groq(api_key=groq_api_key)
                tavily_client = TavilyClient(api_key=tavily_api_key)
            except Exception as e:
                st.error(f"클라이언트 초기화 실패: {e}")
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
                    # Groq 분당 30건 제한 대기
                    wait_for_rate_limit(status)

                    # 1단계 Tavily로 최신 뉴스 검색
                    search_result = tavily_client.search(
                        query=f"{seed} 최신 뉴스 논란 의혹 2026",
                        search_depth="basic",
                        max_results=5,
                        include_answer=True
                    )

                    # 검색 결과 텍스트 추출
                    news_context = ""
                    if search_result.get("answer"):
                        news_context += f"요약: {search_result['answer']}\n\n"
                    for r in search_result.get("results", []):
                        news_context += f"- {r.get('title', '')}: {r.get('content', '')[:200]}\n"

                    # 2단계 Groq로 키워드 발굴
                    prompt = f"""당신은 2026년 한국 이슈 관제 전문가입니다.

아래는 '{seed}'에 대한 최신 뉴스 검색 결과입니다.

[최신 뉴스]
{news_context}

위 뉴스 맥락을 바탕으로 추가로 모니터링이 필요한 확장 키워드를 발굴하세요.

[출력 규칙]
- 띄어쓰기 없는 표준어 조합
- 한 줄에 키워드 하나만
- 설명·번호·기호 일절 금지
- 수사·의혹·논란·어뷰징·도덕적 리스크·허위정보·여론 악용 가능성 중심
- 최근 이슈에서 파생될 수 있는 키워드 포함
- 일반 정보성·긍정 뉴스 제외

[출력 예시]
{seed}수사
{seed}구속
{seed}선거법위반"""

                    response = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3
                    )

                    result_text = response.choices[0].message.content
                    for line in result_text.strip().split('\n'):
                        cleaned = clean_line(line)
                        if cleaned and cleaned not in seen:
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
