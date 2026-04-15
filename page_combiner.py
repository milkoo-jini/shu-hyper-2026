import streamlit as st
import pandas as pd
from itertools import product
import io
def run_combiner():
    st.header("🧩 단어 조합 생성기")
    st.info("각 그룹에 단어를 입력하세요. 추가 버튼을 누르면 옆으로 새로운 그룹이 생성됩니다.")
    # 1. 그룹 개수 관리
    if 'combo_group_count' not in st.session_state:
        st.session_state.combo_group_count = 2
    # 2. 제어 버튼
    col_btn1, col_btn2 = st.columns([1, 1])
    with col_btn1:
        if st.button("➕ 그룹 추가(오른쪽으로)", use_container_width=True):
            st.session_state.combo_group_count += 1
            st.rerun()
    with col_btn2:
        if st.button("➖ 그룹 제거", use_container_width=True) and st.session_state.combo_group_count > 1:
            st.session_state.combo_group_count -= 1
            st.rerun()
    st.markdown("---")
    # 3. 입력 섹션 (입력창은 세로로 길게, 배치는 가로로 나란히)
    # 그룹 개수만큼 컬럼을 생성하여 옆으로 나열합니다.
    cols = st.columns(st.session_state.combo_group_count)
    all_inputs = []
    for i, col in enumerate(cols):
        with col:
            is_last = (i == st.session_state.combo_group_count - 1)
            label = f"📍 마지막 그룹" if is_last else f"그룹 {i+1}"
            
            # 입력창 자체는 세로로 길게(height=300) 설정
            user_input = st.text_area(
                label, 
                placeholder="단어를 한 줄에\n하나씩 입력", 
                key=f"comb_in_{i}", 
                height=300  # 세로로 길게 조절
            )
            
            words = [w.strip() for w in user_input.split('\n') if w.strip()]
            if words:
                all_inputs.append(words)
    st.markdown("---")
    # 4. 결과 생성 및 엑셀 다운로드
    if st.button("🚀 조합 생성 및 엑셀 다운로드", type="primary", use_container_width=True):
        if len(all_inputs) < st.session_state.combo_group_count:
            st.error("모든 그룹에 내용을 입력해야 합니다.")
        else:
            combinations = list(product(*all_inputs))
            results = [" ".join(combo) for combo in combinations]
            
            df = pd.DataFrame(results, columns=["조합 결과"])
            st.success(f"총 {len(results):,}개의 조합이 생성되었습니다.")
            st.dataframe(df, use_container_width=True)
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
