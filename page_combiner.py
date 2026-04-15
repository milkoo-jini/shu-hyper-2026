import streamlit as st
import pandas as pd
from itertools import product
import io

def run_combiner():
    # 1. Streamlit Secrets에서 비밀번호 로드
    try:
        SECRET_PASSWORD = st.secrets["COMBINER_PW"]
    except KeyError:
        st.error("🚨 환경 설정(Secrets)에 'COMBINER_PW'가 등록되지 않았습니다.")
        return

    # 2. 인증 상태 확인 및 비밀번호 입력 UI
    if "combiner_authenticated" not in st.session_state:
        st.session_state.combiner_authenticated = False

    if not st.session_state.combiner_authenticated:
        # 화면 중앙에 정갈하게 배치하기 위한 컬럼 구성
        _, center_col, _ = st.columns([1, 2, 1])
        with center_col:
            st.subheader("🔐 도구 액세스 제한")
            pw_input = st.text_input("비밀번호를 입력하세요", type="password", key="pw_field")
            if st.button("접속하기", use_container_width=True):
                if pw_input == SECRET_PASSWORD:
                    st.session_state.combiner_authenticated = True
                    st.rerun()
                else:
                    st.error("비밀번호가 일치하지 않습니다.")
        return

    # 3. 메인 기능 (인증 성공 시 노출)
    st.header("🧩 단어 조합 생성기")
    st.info("각 그룹에 단어를 입력하면 모든 가능한 조합을 생성합니다. 마지막 그룹은 항상 문장 끝에 붙습니다.")

    # 그룹 개수 관리
    if 'combo_group_count' not in st.session_state:
        st.session_state.combo_group_count = 2

    # 제어 버튼 (세로 배치)
    col_add, col_del = st.columns([1, 1])
    with col_add:
        if st.button("➕ 그룹 추가", use_container_width=True):
            st.session_state.combo_group_count += 1
            st.rerun()
    with col_del:
        if st.button("➖ 그룹 제거", use_container_width=True) and st.session_state.combo_group_count > 1:
            st.session_state.combo_group_count -= 1
            st.rerun()

    st.markdown("---")

    # 4. 입력 섹션 (세로 정렬)
    all_inputs = []
    for i in range(st.session_state.combo_group_count):
        is_last = (i == st.session_state.combo_group_count - 1)
        label = f"📍 마지막 그룹 (접미사)" if is_last else f"그룹 {i+1}"
        
        user_input = st.text_area(label, placeholder="한 줄에 단어 하나씩 입력", key=f"comb_in_{i}", height=150)
        words = [w.strip() for w in user_input.split('\n') if w.strip()]
        if words:
            all_inputs.append(words)

    st.markdown("---")

    # 5. 실행 및 결과
    if st.button("🚀 조합 생성 및 엑셀 다운로드", type="primary", use_container_width=True):
        if len(all_inputs) < st.session_state.combo_group_count:
            st.error("모든 그룹에 내용을 입력해야 조합이 가능합니다.")
        else:
            combinations = list(product(*all_inputs))
            results = [" ".join(combo) for combo in combinations]
            
            df = pd.DataFrame(results, columns=["조합 결과"])
            st.success(f"성공! 총 {len(results):,}개의 조합이 만들어졌습니다.")
            
            # 결과 미리보기
            st.dataframe(df, use_container_width=True)

            # 엑셀 다운로드 파일 생성
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 엑셀 파일 다운로드",
                data=buffer.getvalue(),
                file_name="word_combinations.xlsx",
                mime="application/vnd.ms-excel",
                use_container_width=True
            )

    # 사이드바 하단에 로그아웃 버튼 살짝 추가 (편의성)
    if st.sidebar.button("🔓 도구 잠그기"):
        st.session_state.combiner_authenticated = False
        st.rerun()
