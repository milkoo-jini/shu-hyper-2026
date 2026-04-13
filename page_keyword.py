import streamlit as st
import time
from google import genai
from google.genai import types

def run_keyword():
    # --- [수정] 사이드바 비밀번호 설정 ---
    with st.sidebar:
        st.title("🔐 관리자 인증")
        # 팁: 나중에 st.secrets에 저장해서 쓰시면 더 안전합니다.
        password = st.text_input("접속 비밀번호", type="password")

    # 비밀번호가 틀리면 화면 전체를 잠금
        admin_pw = st.secrets.get("ADMIN_PASSWORD", "1234") # 세팅 안됐을 때를 대비한 기본값 1234
        if password == admin_pw:
        # 인증 성공 로직
        if password == "":
            st.info("왼쪽 사이드바에 비밀번호를 입력해주세요.")
        else:
            st.error("비밀번호가 올바르지 않습니다.")
        return

    # --- [수정] 메인 화면 레이아웃 분할 (왼쪽 1 : 오른쪽 2 비율) ---
    col_input, col_output = st.columns([1, 2], gap="large")

    with col_input:
        st.markdown("### 🎯 리스크 확장 설정")
        st.info("AI 분석을 통한 '실질적 위험군' 선별")

        # API 키 로드
        api_key = st.secrets.get("GEMINI_API_KEY")

        # 입력창
        target_text = st.text_area(
            "📡 대상 키워드 입력", 
            height=250, 
            placeholder="정원오\n김병기\n대전늑대",
            help="한 줄에 하나씩 입력하세요."
        )

        # 분석 실행 버튼
        analyze_clicked = st.button("🚀 리스크 분석 및 나열", use_container_width=True)

    with col_output:
        st.markdown("### 📋 분석 결과 리스트")
        
        # 로컬 백업 리스트
        backup_risks = [
            "수사", "경찰수사", "검찰수사", "구속", "영장청구", "선거법위반", "압수수색", "조사결과",
            "논란", "의혹", "비리", "특혜", "거짓해명", "갑질", "여론조작", "뒷광고",
            "전복", "유출", "사고", "인명피해", "사망설", "피해은폐", "현장사진",
            "가짜뉴스", "가짜제보", "허위제보", "AI조작", "밀약설", "음모론"
        ]

        if analyze_clicked:
            if not target_text:
                st.warning("분석할 단어를 입력하세요.")
            else:
                seeds = [t.strip() for t in target_text.split('\n') if t.strip()]
                final_results = []
                
                use_ai = False
                if api_key:
                    try:
                        client = genai.Client(api_key=api_key)
                        client.models.generate_content(model="gemini-2.0-flash", contents="h")
                        use_ai = True
                    except:
                        st.warning("⚠️ API 차단 감지: 로컬 엔진 전환")

                if use_ai:
                    status = st.empty()
                    for seed in seeds:
                        status.text(f"🎯 AI가 '{seed}' 분석 중...")
                        prompt = f"""
                        당신은 2026년 이슈 관제 전문가입니다. '{seed}'와 관련하여 '실질적 리스크'가 있는 키워드만 확장하세요.
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
                    status.success("✅ AI 분석 완료!")
                else:
                    for seed in seeds:
                        for r in backup_risks: final_results.append(f"{seed}{r}")
                    st.success("✅ 로컬 조합 완료!")

                # 결과 출력 칸 (오른쪽 전용)
                result_str = "\n".join(final_results)
                st.text_area("전체 복사 영역", value=result_str, height=600)
        else:
            st.write("왼쪽에서 키워드를 입력하고 버튼을 눌러주세요.")

# 메인 실행부에서 사이드바 화살표 살려두는 설정 확인 필요
