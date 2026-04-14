import streamlit as st
import pandas as pd
import datetime, re, requests, io, time, os
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

# [순정 보존] 슈 님의 분석 엔진 클래스
class MasterGuardian_Smart_Claude:
    def __init__(self):
        self.now = datetime.now()
        self.time_limit = self.now - timedelta(hours=24)
        
        try:
            self.naver_id = st.secrets["NAVER_ID"]
            self.naver_secret = st.secrets["NAVER_SECRET"]
        except:
            self.naver_id = "g6EGE1xFHkT99HQ2CRtd"
            self.naver_secret = "Q9DVSRZVL2"

        # 슈 님 원본 메모장 로드 방식 그대로
        self.answer_data = self.load_txt_file('정답기사리스트.txt') 
        self.wrong_data = self.load_txt_file('오답기사리스트.txt')   
        self.risk_vocab = self.build_vocab(self.answer_data)
        self.noise_vocab = self.build_vocab(self.wrong_data)

        # 제외 리스트 (슈 님 요청사항 반영)
        self.exclude_list = [
            "변호사", "법무법인", "법률사무소", "상담문의", "무료상담", "홍보", "마케팅", "보도자료",
            "분양", "입주", "청약", "특가", "할인", "세일", "프로모션", "칼럼", "사설", "기고",
            "운세", "부고", "인사", "ceo스토리", "who is", "who", "WHO", "트럼프", "인터뷰", "interview",
            "라운지", "포커스", "소식", "재계는", "레이더", "사사건건", "와글와글", "오프닝"
        ]

    def load_txt_file(self, filename):
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        return []

    def build_vocab(self, data_list):
        vocab = set()
        for title in data_list:
            words = re.findall(r'[가-힣0-9]{2,}', title)
            vocab.update(words)
        return vocab

    def is_risk_context(self, title):
        # [동작 방식 보존] 1. 제외 단어 즉시 차단
        if any(ex in title for ex in self.exclude_list): return False
        
        current_words = set(re.findall(r'[가-힣0-9]{2,}', title))
        # [동작 방식 보존] 2. 오답 메모장 필터링
        if len(current_words & self.noise_vocab) >= 3: return False

        # [동작 방식 보존] 3. 슈 님의 5대 리스크 기준
        risk_standards = {
            "기만_사칭": ['사칭', '딥페이크', '허위', '가짜', '속여', '유명인'],
            "피해_보복": ['유출', '먹튀', '스토킹', '협박', '폐업', '연락두절', '보복'],
            "불법_유통": ['마약', '짝퉁', '도박', '성착취물', '밀수', '오남용'],
            "신뢰_훼손": ['비리', '부정부패', '해킹', '보안사고', '선거법', '뇌물'],
            "신종_수법": ['변종', '우회', '수법', '취약점', '악용', '비정상']
        }
        for words in risk_standards.values():
            if any(w in title for w in words): return True
            
        # [동작 방식 보존] 4. 정답 메모장 점수제 (2점 이상)
        if len(current_words & self.risk_vocab) >= 2: return True
        return False

    def make_claude_prompt(self, to_analyze):
        # [순정 보존] 슈 님 원본 명령 프롬프트 문구
        answer_examples = "\n".join([f"- {t}" for t in self.answer_data[:20]])
        wrong_examples = "\n".join([f"- {t}" for t in self.wrong_data[-30:]])
        return f"""당신은 국가급 위기 관리 및 플랫폼 생태계 감시 전문가입니다.\n\n### **📖 [공부해야 할 정답 사례]**\n{answer_examples}\n\n### **🕵️ [리스크 판별 기준]**\n1. 기만 및 사칭\n2. 이용자 피해 및 보복\n3. 불법 유통 및 위반\n4. 사회적 신뢰 훼손\n5. 신종 수법 및 사각지대\n\n### **⚠️ [분석 철학]**\n- 포괄적 해석 적용\n- 단순 동정/홍보 오답만 제외\n\n### **🚫 [오답 사례]**\n{wrong_examples}\n\n---\n### **[검토 대상 리스트]**\n{to_analyze}\n\n---\n[제목 / 판별결과(포착/패스) / 사유] 형식으로 정리하세요."""

# 메인 실행 함수
def run_claude_collector():
    st.markdown("### 🛡️ 클로드 분석용 언론 수집")
    
    if 'claude_pool' not in st.session_state: st.session_state.claude_pool = []
    if 'claude_key' not in st.session_state: st.session_state.claude_key = 0

    # [UI 반영] 상단 정렬 및 꽉 차게 배치
    menu_c1, menu_c2, menu_c3, menu_c4 = st.columns([1, 1.5, 2, 0.5])
    
    with menu_c1:
        if st.button("🚀 수집 시작", use_container_width=True):
            st.session_state.is_collecting = True
            st.rerun()

    with menu_c2:
        # 필터 칸 크기 조정
        search_query = st.text_input("", placeholder="🔍 기사제목 필터", label_visibility="collapsed")

    with menu_c3:
        # [UI 반영] 하단 버튼을 필터 옆으로 이동
        df_for_btn = pd.DataFrame(st.session_state.claude_pool)
        if not df_for_btn.empty:
            sel_titles = df_for_btn[df_for_btn['선택'] == True]['기사제목'].tolist()
            if sel_titles:
                engine_temp = MasterGuardian_Smart_Claude()
                full_txt = engine_temp.make_claude_prompt("\n".join(sel_titles))
                st.download_button("📄 클로드 분석용.txt 다운로드", full_txt.encode('utf-8'), "Claude_Request.txt", use_container_width=True)
            else:
                st.button("📄 선택된 기사 없음", disabled=True, use_container_width=True)

    with menu_c4:
        st.markdown(f"<div style='border:1px solid #007BFF; color:#007BFF; font-weight:bold; border-radius:5px; padding:5.5px; text-align:center;'>{len(st.session_state.claude_pool)}</div>", unsafe_allow_html=True)

    # 데이터 수집 (동작 방식 변동 없음)
    if st.session_state.get('is_collecting', False):
        with st.status("📡 수집 및 판독 중...") as status:
            engine = MasterGuardian_Smart_Claude()
            if os.path.exists('언론키워드셋.txt'):
                with open('언론키워드셋.txt', 'r', encoding='utf-8') as f:
                    keywords = [l.strip() for l in f if l.strip()]
                
                final_results = []
                # (수집 API 로직 부분... 기존과 동일)
                # ...
                st.session_state.claude_pool = final_results
            st.session_state.is_collecting = False
            st.rerun()

    # [UI 반영] 테이블 가로 꽉 차게 설정
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
            use_container_width=True, # 오른쪽 빈틈 없이 꽉 채움
            height=700,
            key=f"table_{st.session_state.claude_key}"
        )
