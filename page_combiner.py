import streamlit as st
import pandas as pd
from itertools import product
import io

def run_combiner():
    # 1. st.secrets에서 비밀번호 가져오기
    # .secrets["설정한_이름"]으로 가져옵니다.
    try:
        SECRET_PASSWORD = st.secrets["COMBINER_PW"]
    except KeyError:
        st.error("Streamlit Secrets에 'COMBINER_PW'가 설정되지 않았습니다.")
        return

    st.header("🧩 단어 조합 생성기")

    # 2. 비밀번호 체크 로직
    if "combiner_authenticated" not in st.session_state:
        st.session_state.combiner_authenticated = False

    if not st.session_state.combiner_authenticated:
        # 안내 문구 수정 (비밀번호 입력창)
        password_input = st.text_input("액세스 비밀번호를 입력하세요", type="password")
        if st.button("확인"):
            if password_input == SECRET_PASSWORD:
                st.session_state.combiner_authenticated = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
        return 

    # 3. 본 기능 (인증 후 노출)
    st.info("각 칸에 단어를 입력하세요. 마지막 칸의 단어는 항상 문장 맨 뒤에 위치합니다.")

    if 'combo_group_count' not in st.session_state:
        st.session_state.combo_group_count = 2

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("➕ 추가"):
            st.session_state.combo_group_count += 1
            st.rerun()
    with col2:
        if st.button("➖ 제거") and st.session_state.combo_group_count > 1:
            st.session_state.combo_group_count -= 1
            st.rerun()

    all_inputs = []
    for i in range(st.session_state.combo_group_count):
        is_last = (i == st.session_state.combo_group_count - 1)
        label = f"📍 마지막 그룹 (접미사)" if is_last else f"그룹 {i+1}"
        
        user_input = st.text_area(label, placeholder="한 줄에 하나씩 입력", key=f"comb_in_{i}")
        words = [w.strip() for w in user_input.split('\n') if w.strip()]
        if words:
            all_inputs.append(words)

    if st.button("🚀 조합 생성 및 엑셀 다운로드", type="primary"):
        if len(all_inputs) < st.session_state.combo_group_count:
            st.error("모든 칸에 최소 하나 이상의 단어를 입력해야 합니다.")
        else:
            combinations = list(product(*all_inputs))
            results = [" ".join(combo) for combo in combinations]
            
            df = pd.DataFrame(results, columns=["조합 결과"])
            st.success(f"총 {len(results)}개의 조합이 생성되었습니다.")
            st.dataframe(df, use_container_width=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 엑셀 파일 다운로드",
                data=buffer.getvalue(),
                file_name="word_combinations.xlsx",
                mime="application/vnd.ms-excel"
            )
