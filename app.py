with st.sidebar:
    st.title("🚀 QA1 업무 대시보드")
    st.markdown("---")
    
    # 1. 메인 메뉴
    menu_main = st.radio("메뉴 선택", [
        "클로드 분석용 언론 수집",
        "실시간 이슈 모니터링", 
        "리스크 키워드 확장"
    ], index=1, key="main_menu", on_change=reset_tool)
    
    st.markdown("---")
    
    # 2. 도구 메뉴
    menu_tool = st.radio("도구", ["단어 조합 생성기"], 
                         index=None, key="tool_menu", on_change=reset_main, label_visibility="collapsed")
    
    st.markdown("---")

    # [핵심] 보안 메뉴 선택 여부 확인
    is_secure_selected = (menu_main == "리스크 키워드 확장") or (st.session_state.get("tool_menu") == "단어 조합 생성기")

    # 3. [원본 복구] 관리자 인증 섹션
    if is_secure_selected:
        if not st.session_state.admin_mode:
            st.write("🔒 관리자 모드") # 이모지 및 텍스트 원복
            # 라벨 숨김 및 엔터키 연동 (on_change)
            st.text_input("PW", type="password", placeholder="비밀번호 입력 후 Enter", 
                         key="admin_pw_entry", on_change=check_admin_pw, label_visibility="collapsed")
            if st.button("인증", use_container_width=True):
                check_admin_pw()
        else:
            st.write("🔓 관리자 인증 완료") # 이모지 및 문구 원복
            if st.button("잠금", use_container_width=True):
                st.session_state.admin_mode = False
                st.rerun()
        st.markdown("---")

    st.caption("v2.1 Hybrid Engine (AI + Local)")
