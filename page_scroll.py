import streamlit as st
import requests
import re
import json
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta, timezone
import time

# 정확한 도메인 일치 방식 (서브도메인 포함)
def is_excluded(domain: str) -> bool:
    return False  # 모든 도메인을 통과시킴


def parse_cookie(raw: str) -> str:
    raw = raw.strip()
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            parts = [f"{item['name']}={item['value']}" for item in data if item.get('name')]
            return '; '.join(parts)
    except (json.JSONDecodeError, TypeError):
        pass
    return raw


def extract_domains_from_text(text: str) -> list:
    # 1. HTML 태그 제거 (주소 사이에 낀 <br>, <div> 등을 공백으로 치환하여 연결성 확보)
    # 네이버 본문은 HTML 형태라 이 작업이 없으면 주소가 중간에 끊길 수 있습니다.
    clean_text = re.sub(r'<[^>]*>', ' ', text)
    
    # 2. 더 넓은 범위의 URL 패턴 (http가 없거나 복잡한 파라미터가 있어도 수집)
    url_pattern = re.compile(
        r'(?:https?://)?(?:[a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?::\d+)?(?:/[^\s<>"\']*)?'
    )
    
    found = url_pattern.findall(clean_text)
    
    cleaned_results = []
    if found:
        for f in set(found):
            # 주소 끝에 붙은 불필요한 기호(마침표, 괄호, 따옴표 등) 깔끔하게 정리
            clean_url = f.strip('.,;)"\'/ ')
            
            # 너무 짧은 텍스트(예: ".com")는 제외하고 유효한 것만 추가
            if '.' in clean_url and len(clean_url) > 5:
                # is_excluded가 무조건 False를 뱉으므로 모든 도메인이 통과됩니다.
                domain_part = clean_url.replace('https://', '').replace('http://', '').split('/')[0].split(':')[0]
                if not is_excluded(domain_part):
                    cleaned_results.append(clean_url)
                
    return list(set(cleaned_results)) # 최종 중복 제거


def run_domain_collector():

    # ── 쿠키 로드 ────────────────────────────────────────────────
    try:
        raw_cookie = st.secrets["NAVER_COOKIE"]
    except KeyError:
        st.error("❌ secrets.toml에 NAVER_COOKIE가 설정되지 않았습니다.")
        st.code("NAVER_COOKIE = '''[ { \"name\": \"NID_AUT\", \"value\": \"...\" } ]'''")
        return

    if not raw_cookie or not raw_cookie.strip():
        st.error("❌ NAVER_COOKIE 값이 비어 있습니다.")
        return

    cookie_value = parse_cookie(raw_cookie)

    # ── 타이틀 ───────────────────────────────────────────────────
    st.markdown("## 🔎 사기 의심 도메인 수집")
    st.markdown(
        "<p style='color:#868e96; margin-top:-0.5rem;'>"
        "네이버 카페 게시글에서 최근 N시간 내 사기 의심 도메인을 추출합니다."
        "</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── 설정 ─────────────────────────────────────────────────────
    col_l, col_r = st.columns([3, 1])
    with col_l:
        st.markdown("#### 📋 수집 안내")
        st.markdown(
            "<p style='color:#495057; font-size:0.9rem;'>"
            "secrets에 저장된 네이버 계정 쿠키를 사용합니다.<br>"
            "쿠키가 만료된 경우 <b>.streamlit/secrets.toml</b>을 업데이트 해주세요."
            "</p>",
            unsafe_allow_html=True
        )
    with col_r:
        st.markdown("#### ⚙️ 수집 설정")
        hours_limit = st.selectbox(
            "수집 범위",
            [6, 12, 24],
            index=1,
            format_func=lambda x: f"최근 {x}시간"
        )
        page_size = st.selectbox("페이지당 글 수", [15, 30, 50], index=1)
        debug_mode = st.checkbox("디버그 모드", value=False)

    st.markdown("---")

    run_btn = st.button("🚀 도메인 수집 시작", use_container_width=True, type="primary")

    if not run_btn:
        with st.expander("📌 쿠키 갱신 방법", expanded=False):
            st.markdown("""
            1. 크롬에 **Cookie-Editor** (`cgagnier` 제작) 설치
            2. 네이버 로그인 후 해당 카페 접속
            3. Cookie-Editor → **Export** → **JSON (Netscape format)**
            4. 복사한 JSON 전체를 Streamlit Cloud **Secrets**의 `NAVER_COOKIE`에 붙여넣기
            5. 저장 후 앱 재시작
            """)
        return

    # ── 헤더 ─────────────────────────────────────────────────────
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Cookie': cookie_value,
        'Referer': 'https://cafe.naver.com/notouch7',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Origin': 'https://cafe.naver.com',
    }

    cutoff_time = datetime.now(KST) - timedelta(hours=hours_limit)
    filtered = []

    # ── 페이지 자동 순회 (12시간 이내 글만) ──────────────────────
    st.info(f"📋 최근 {hours_limit}시간 이내 게시글 수집 중...")
    page_status = st.empty()

    page = 1
    stop = False

    while not stop and page <= MAX_PAGES:
        page_status.caption(f"페이지 {page} 불러오는 중...")
        list_url = (
            f"https://apis.naver.com/cafe-web/cafe-boardlist-api/v1"
            f"/cafes/25470135/menus/0/articles"
            f"?page={page}&pageSize={page_size}&sortBy=TIME&viewType=L"
        )

        try:
            res = requests.get(list_url, headers=headers, timeout=10)

            if debug_mode and page == 1:
                st.markdown("#### 🛠 디버그 정보")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.markdown(f"<div class='status-badge'>HTTP 상태: {res.status_code}</div>", unsafe_allow_html=True)
                with col_d2:
                    st.markdown(f"<div class='status-badge'>응답 크기: {len(res.text):,} bytes</div>", unsafe_allow_html=True)
                with st.expander("원본 응답 (앞 1000자)"):
                    st.code(res.text[:1000])

            data = res.json()

            # 응답 구조 자동 탐색
            articles = None
            for key_path in [
                ['message', 'result', 'articleList'],
                ['message', 'result', 'articles'],
                ['result', 'articleList'],
                ['result', 'articles'],
                ['articleList'],
                ['articles'],
            ]:
                try:
                    node = data
                    for k in key_path:
                        node = node[k]
                    if isinstance(node, list):
                        articles = node
                        break
                except (KeyError, TypeError):
                    continue

            if not articles:
                stop = True
                break

            for art in articles:
                ts = (
                    art.get('writeDateTimestamp')
                    or art.get('lastUpdateDate')
                    or art.get('createDate')
                    or art.get('writeDate')
                    or art.get('regDate')
                )
                art_time = None
                if ts:
                    try:
                        if isinstance(ts, (int, float)) and ts > 1e10:
                            art_time = datetime.fromtimestamp(ts / 1000, tz=KST)
                        elif isinstance(ts, (int, float)):
                            art_time = datetime.fromtimestamp(ts, tz=KST)
                        else:
                            art_time = datetime.fromisoformat(
                                str(ts).replace('Z', '+00:00')
                            ).astimezone(KST)
                    except Exception:
                        pass

                if art_time and art_time < cutoff_time:
                    stop = True  # 12시간 넘은 글 나오면 중단
                    break

                art['_parsed_time'] = art_time
                filtered.append(art)

        except Exception as e:
            st.error(f"❌ 페이지 {page} 오류: {e}")
            stop = True
            break

        page += 1
        time.sleep(0.3)

    page_status.empty()

    if not filtered:
        st.warning(f"최근 {hours_limit}시간 내 게시글이 없습니다.")
        return

    st.success(f"총 {page-1}페이지에서 **{len(filtered)}개** 글 발견 → 본문 분석 시작")

    # ── 본문 수집 및 도메인 추출 ──────────────────────────────────
    results = []
    prog_bar = st.progress(0)
    status_text = st.empty()

    for i, art in enumerate(filtered):
        article_id = art.get('articleId') or art.get('id')
        title = art.get('subject') or art.get('title') or f"글_{article_id}"
        art_time = art.get('_parsed_time')
        time_str = art_time.strftime('%Y-%m-%d %H:%M') if art_time else "-"

        status_text.caption(f"본문 분석 중... ({i+1}/{len(filtered)}) {title[:30]}...")

        content_url = (
            f"https://apis.naver.com/cafe-web/cafe-articleapi/v2"
            f"/cafes/25470135/articles/{article_id}"
        )
        try:
            content_res = requests.get(content_url, headers=headers, timeout=10)
            try:
                content_data = content_res.json()
                body = ""
                for path in [
                    ['message', 'result', 'article', 'contentHtml'],
                    ['message', 'result', 'article', 'content'],
                    ['result', 'article', 'contentHtml'],
                    ['result', 'article', 'content'],
                ]:
                    try:
                        node = content_data
                        for k in path:
                            node = node[k]
                        body = str(node)
                        break
                    except (KeyError, TypeError):
                        continue
                text_to_scan = body if body else content_res.text
            except Exception:
                text_to_scan = content_res.text

            domains = extract_domains_from_text(text_to_scan)
            for d in domains:
                results.append({
                    "도메인": d,
                    "작성시간": time_str,
                    "글제목": title,
                    "링크": f"https://cafe.naver.com/notouch7/{article_id}"
                })
        except Exception:
            pass

        prog_bar.progress((i + 1) / len(filtered))
        time.sleep(0.3)

    status_text.empty()

    # ── 결과 출력 ────────────────────────────────────────────────
    st.markdown("---")

    if not results:
        st.info("ℹ️ 추출된 도메인이 없습니다.")
        return

    df = pd.DataFrame(results).drop_duplicates(subset=['도메인', '링크'])
    df = df.sort_values('작성시간', ascending=False).reset_index(drop=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='status-badge'>🌐 추출 도메인: {df['도메인'].nunique()}개</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='status-badge'>📄 분석 게시글: {len(filtered)}개</div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='status-badge'>⏱ 수집 범위: 최근 {hours_limit}시간</div>", unsafe_allow_html=True)

    st.markdown("#### 📊 수집 결과")
    st.dataframe(df, use_container_width=True, hide_index=True)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='사기도메인')
    output.seek(0)

    now_str = datetime.now(KST).strftime('%Y%m%d_%H%M')
    st.download_button(
        label="📥 엑셀 다운로드",
        data=output.getvalue(),
        file_name=f"사기의심도메인_{now_str}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
