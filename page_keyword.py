import streamlit as st
import time
import re
from google import genai
from google.genai import types

def run_keyword():
    with st.sidebar:
        st.title("🔐 관리자 인증")
        password = st.text_input("접속 비밀번호", type="password")

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
            st.error(f"'{seed}' 실패 — 사용량 한도 초과. 잠시 후 재시도하세요.")
        elif "403" in err or "PERMISSION_DENIED" in err:
            st.error(f"'{seed}' 실패 — API 키 차단 또는 권한 없음. 키를 확인하세요.")
        elif "400" in err or "INVALID_ARGUMENT" in err:
            st.error(f"'{seed}' 실패 — 잘못된 요청입니다.")
        elif "503" in err or "UNAVAILABLE" in err:
            st.error(f"'{seed}' 실패 — Gemini 서버 일시 불가. 잠시 후 재시도하세요.")
        elif "ConnectionError" in err or "connect" in err.lower():
            st.error(f"'{seed}' 실패 — 네트워크 차단 또는 IP 접근 불가.")
        else:
            st.error(f"'{seed}' 실패 — 알 수 없는 오류: {e}")

    col_input, col_output = st.columns([1, 2], gap="large")

    with col_input:
        st.markdown("### 🎯 리스크 확장 설정")
        st.info("최신 뉴스 검색 기반 실질적 위험 키워드 발굴")
        api_key = st.secrets.get("GEMINI_API_KEY")
        target_text = st.text_area(
            "📡 대상 키워드 입력", height=250,
            placeholder="정원오\n김병기\n대전늑대",
            help="한 줄에 하나씩 입력하세요."
        )
        analyze_clicked = st.button("🚀 리스크 분석 및 나열", use_container_width=True)

    with col_output:
        st.markdown("### 📋 분석 결과 리스트")

        if analyze_clicked:
            if not target_text.strip():
                st.warning("분석할 단어를 입력하세요.")
                return

            if not api_key:
                st.error("API 키가 설정되지 않았습니다. secrets에 GEMINI_API_KEY를 확인하세요.")
                return

            try:
                client = genai.Client(api_key=api_key)
            except Exception as e:
                handle_api_error(e, "API 초기화")
                return

            seeds = [t.strip() for t in target_text.split('\n') if t.strip()]
            final_results = []
            seen = set()

            progress = st.progress(0)
            status = st.empty()

            for i, seed in enumerate(seeds):
                progress.progress((i + 1) / len(seeds), text=f"{seed} 분석 중... ({i+1}/{len(seeds)})")

                prompt = f"""당신은 2026년 한국 이슈 관제 전문가입니다.

[1단계] Google 검색을 통해 '{seed}'와 관련된 최근 이슈·뉴스를 먼저 파악하세요.

[2단계] 파악한 이슈 맥락을 바탕으로, 추가로 모니터링이 필요한 확장 키워드를 발굴하세요.

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

                try:
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())]
                        )
                    )
                    for line in response.text.strip().split('\n'):
                        cleaned = clean_line(line)
                        if cleaned and cleaned not in seen:
                            seen.add(cleaned)
                            final_results.append(cleaned)

                except Exception as e:
                    handle_api_error(e, seed)

                time.sleep(0.5)

            progress.empty()

            if final_results:
                status.success(f"✅ 완료! 총 {len(final_results)}개 키워드")
                st.text_area("전체 복사 영역", value="\n".join(final_results), height=600)
            else:
                status.error("결과가 없습니다. 오류 메시지를 확인하세요.")

        else:
            st.write("왼쪽에서 키워드를 입력하고 버튼을 눌러주세요.")
