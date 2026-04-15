import streamlit as st
import pandas as pd
from itertools import product
import io

def run_combiner():
    # 상단 헤더 및 안내 (app.py에서 인증 후 진입함)
    st.header("🧩 단어 조합 생성기")
    st.info("각 그룹에 단어를 입력하세요. 세로로 나열된 칸에 한 줄에 하나씩 입력하면 됩니다.")

    # 1. 그룹 개수 관리 (기본 2개)
    if 'combo_group_count' not in st.session_state:
        st.session_state.combo_group_count = 2

    # 2. 제어 버튼 (그룹 추가/제거)
    col_add, col_del = st.columns(2)
    with col_add:
        if st.button("➕ 그룹 추가", use_container_width=True):
            st.session_state.combo_group_count += 1
            st.rerun()
    with col_del:
        if st.button("➖ 그룹 제거", use_container_width=True) and st.session_state.combo_group_count > 1:
            st.session_state.combo_group_count -= 1
            st.rerun()

    st.markdown("---")

    # 3. 입력 섹션 (요청하신 대로 세로로 길게 나열)
    all_inputs = []
    for i in range(st.session_state.combo_group_count):
        is_last = (i == st.session_state.combo_group_count - 1)
        label = f"📍 마지막 그룹 (접미사)" if is_last else f"그룹 {i+1}"
        
        # 각 입력창을 세로로 배치
        user_input = st.text_area(label, placeholder="단어를 한 줄에 하나씩 입력하세요", key=f"comb_in_{i}", height=150)
        
        words = [w.strip() for w in user_input.split('\n') if w.strip()]
        if words:
            all_inputs.append(words)

    st.markdown("---")

    # 4. 결과 생성 및 엑셀 다운로드
    if st.button("🚀 조합 생성 및 엑셀 다운로드", type="primary", use_container_width=True):
        if len(all_inputs) < st.session_state.combo_group_count:
            st.error("모든 그룹에 최소 하나 이상의 단어를 입력해야 조합이 가능합니다.")
        else:
            # 데카르트 곱(Cartesian Product)으로 모든 조합 생성
            combinations = list(product(*all_inputs))
            results = [" ".join(combo) for combo in combinations]
            
            df = pd.DataFrame(results, columns=["조합 결과"])
            st.success(f"총 {len(results):,}개의 조합이 생성되었습니다.")
            
            # 결과 미리보기 데이터프레임
            st.dataframe(df, use_container_width=True)

            # 엑셀 파일 생성 (xlsxwriter 활용)
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
