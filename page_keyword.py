import streamlit as st
import time
from google import genai
from google.genai import types

def run_keyword():
    st.markdown("### 🎯 리스크 어뷰징 정밀 확장")
    st.info("AI가 최신 이슈를 분석하여 '실질적 위험군'만 골라 세로로 나열합니다.")

    # 1. API 키 로드 (시크릿)
    api_key = st.secrets.get("GEMINI_API_KEY")

    # 2. 입력창
    target_text = st.text_area("📡 대상 키워드 입력 (한 줄에 하나씩)", height=150, placeholder="정원오\n김병기\n대전늑대")

    # 3. 로컬 백업 리스트 (API 차단 대비용 필수 표준어)
    backup_risks = [
        "수사", "경찰수사", "검찰수사", "구속", "영장청구", "선거법위반", "압수수색", "조사결과",
        "논란", "의혹", "비리", "특혜", "거짓해명", "갑질", "여론조작", "뒷광고",
        "전복", "유출", "사고", "인명피해", "사망설", "피해은폐", "현장사진",
        "가짜뉴스", "가짜제보", "허위제보", "AI조작", "밀약설", "음모론"
    ]

    if st.button("🚀 리스크 분석 및 세로 나열", use_container_width=True):
        if not target_text:
            st.warning("분석할 단어를 입력하세요.")
            return

        seeds = [t.strip() for t in target_text.split('\n') if t.strip()]
        final_results = []
        
        # API 상태 체크
        use_ai = False
        if api_key:
            try:
                client = genai.Client(api_key=api_key)
                client.models.generate_content(model="gemini-2.0-flash", contents="h")
                use_ai = True
            except:
                st.warning("⚠️ API 차단 감지: 로컬 엔진으로 전환합니다.")

        # 키워드 생성
        if use_ai:
            status = st.empty()
            for seed in seeds:
                status.text(f"🎯 AI가 '{seed}'의 실질적 리스크 선별 중...")
                prompt = f"""
                당신은 2026년 이슈 관제 전문가입니다. '{seed}'와 관련하여 '실질적 리스크'가 있는 키역드만 확장하세요.
                [필수] 어뷰징, 리스크, 위험성, 사법논란, 악의적 변형 키워드 중심
                [제외] 단순 근황, 긍정 뉴스, 일반 정보
                [규칙] 띄어쓰기 없는 표준어 조합, 세로로 하나씩만 나열(설명금지)
                """
                try:
                    response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                    final_results.append(response.text.strip())
                except:
                    for r in backup_risks: final_results.append(f"{seed}{r}")
                time.sleep(1)
            status.success("✅ AI 정밀 분석 완료!")
        else:
            for seed in seeds:
                for r in backup_risks: final_results.append(f"{seed}{r}")
            st.success("✅ 로컬 표준어 조합 완료!")

        # 4. 세로 나열 결과창
        st.markdown("---")
        result_str = "\n".join(final_results)
        st.text_area("📋 결과 리스트 (전체 복사)", value=result_str, height=500)
