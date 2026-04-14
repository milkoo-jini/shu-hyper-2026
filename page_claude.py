def run_claude_collector():
    st.markdown("### 🛡️ 클로드 분석용 언론 수집")
    
    # 세션 상태 초기화 (동작 방식 유지)
    if 'claude_pool' not in st.session_state: st.session_state.claude_pool = []
    if 'claude_key' not in st.session_state: st.session_state.claude_key = 0

    # [UI 변경] 필터 칸 50% 축소 + 다운로드 버튼 나란히 배치
    menu_c1, menu_c2, menu_c3, menu_c4 = st.columns([1, 2, 2, 0.5])
    
    with menu_c1:
        if st.button("🚀 수집 시작", use_container_width=True):
            st.session_state.is_collecting = True
            st.rerun()

    with menu_c2:
        # 필터 칸 (절반 크기 느낌으로 배치)
        search_query = st.text_input("", placeholder="🔍 기사제목 필터", label_visibility="collapsed")

    with menu_c3:
        # [반영] 하단 내보내기 3개를 없애고, 여기에 '클로드 분석용.txt' 버튼만 배치
        sel_df = pd.DataFrame(st.session_state.claude_pool)
        if not sel_df.empty:
            sel_titles = sel_df[sel_df['선택'] == True]['기사제목'].tolist()
            if sel_titles:
                engine_temp = MasterGuardian_Smart_Claude()
                full_txt = engine_temp.make_claude_prompt("\n".join(sel_titles))
                st.download_button("📄 클로드 분석용.txt 다운로드", full_txt.encode('utf-8'), "Claude_Request.txt", use_container_width=True)
            else:
                st.button("📄 선택된 기사 없음", disabled=True, use_container_width=True)

    with menu_c4:
        # 건수 표시
        st.markdown(f"<div style='border:1px solid #007BFF; color:#007BFF; font-weight:bold; border-radius:5px; padding:5.5px; text-align:center;'>{len(st.session_state.claude_pool)}</div>", unsafe_allow_html=True)

    # ... (데이터 수집 로직 부분은 슈 님의 기존 코드와 동일하게 유지) ...

    # [UI 변경] 테이블 오른쪽 끝까지 꽉 차게 설정
    if st.session_state.claude_pool:
        df = pd.DataFrame(st.session_state.claude_pool)
        if search_query:
            df = df[df['기사제목'].str.contains(search_query, case=False, na=False)]
        
        st.data_editor(
            df,
            column_config={
                "수집시간": st.column_config.TextColumn("시간", width=85),
                "수집키워드": st.column_config.TextColumn("키워드", width=100),
                "기사제목": st.column_config.TextColumn("분석 대상 헤드라인"),
                "링크": st.column_config.LinkColumn(" ", display_text="🔗", width=40),
                "선택": st.column_config.CheckboxColumn(" ", width=40),
            },
            column_order=("수집시간", "수집키워드", "기사제목", "링크", "선택"),
            hide_index=True, 
            use_container_width=True, # 이 옵션이 오른쪽 빈 칸 없이 꽉 채워줍니다.
            height=700,
            key=f"table_{st.session_state.claude_key}"
        )
