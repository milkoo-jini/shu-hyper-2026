import streamlit as st
import requests
import re
import json
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta, timezone
import time

# 제외할 시스템/플랫폼 도메인
EXCLUDE_DOMAINS = {
    'naver.com', 'blog.naver.com', 'cafe.naver.com', 'search.naver.com',
    'map.naver.com', 'shopping.naver.com', 'news.naver.com',
    'daum.net', 'map.daum.net', 'search.daum.net',
    'google.com', 'google.co.kr', 'googleapis.com', 'gstatic.com',
    'kakao.com', 'kakaocorp.com', 'kakaocdn.net', 'daumcdn.net',
    'youtube.com', 'youtu.be',
    'wikipedia.org',
    'cloudflare.com',
    'amazonaws.com',
    'jquery.com',
    'bootstrapcdn.com',
    'fontawesome.com',
    'w3.org',
    'schema.org',
    'mozilla.org',
    'microsoft.com',
    'apple.com',
    'facebook.com', 'fb.com',
    'instagram.com',
    'twitter.com', 'x.com',
    'tiktok.com',
    'pstatic.net',
    'naverusercontent.com',
    'steamusercontent.com',
    'namu.wiki',
}

def is_excluded(domain: str) -> bool:
    d = domain.lower()
    # 정확히 일치하거나 서브도메인으로 끝나는 경우만 제외
    return any(d == ex or d.endswith('.' + ex) for ex in EXCLUDE_DOMAINS)

KST = timezone(timedelta(hours=9))


def is_excluded(domain: str) -> bool:
    d = domain.lower()
    return any(ex in d for ex in EXCLUDE_KEYWORDS)


def parse_cookie(raw: str) -> str:
    """
    Cookie-Editor JSON 배열 또는 일반 문자열 쿠키 모두 처리.
    최종적으로 'key=value; key=value;' 형태 문자열 반환.
    """
    raw = raw.strip()
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            parts = []
            for item in data:
                name = item.get('name', '')
                value = item.get('value', '')
                if name:
                    parts.append(f"{name}={value}")
            return '; '.join(parts)
    except (json.JSONDecodeError, TypeError):
        pass
    return raw


def extract_domains_from_text(text: str) -> list:
    """http/https URL에서 도메인 추출 (정밀 패턴)"""
    url_pattern = re.compile(
        r'https?://([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'
        r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*'
        r'\.[a-zA-Z]{2,})'
    )
    found = url_pattern.findall(text)
    return [d for d in set(found) if not is_excluded(d)]


def run_domain_collector():

    # ── 쿠키 로드 (secrets) ──────────────────────────────────────
    try:
        raw_cookie = st.secrets["NAVER_COOKIE"]
    except KeyError:
        st.error("❌ secrets.toml에 NAVER_COOKIE가 설정되지 않았습니다.")
        st.code("NAVER_COOKIE = '''[ { \"name\": \"NID_AUT\", \"value\": \"...\" } ]'''")
        return

    if not raw_cookie or not raw_cookie.strip():
        st.error("❌ NAVER_COOKIE 값이 비어 있습니다. secrets.toml을 확인해 주세요.")
        return

    cookie_value = parse_cookie(raw_cookie)

    # ── 타이틀 영역 ──────────────────────────────────────────────
    st.markdown("## 🔎 사기 의심 도메인 수집")
    st.markdown(
        "<p style='color:#868e96; margin-top:-0.5rem;'>"
        "네이버 카페 게시글에서 최근 N시간 내 사기 의심 도메인을 추출합니다."
        "</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ── 설정 영역 ────────────────────────────────────────────────
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

    # ── 실행 버튼 ────────────────────────────────────────────────
    run_btn = st.button("🚀 도메인 수집 시작", use_container_width=True, type="primary")

    if not run_btn:
        with st.expander("📌 쿠키 갱신 방법", expanded=False):
            st.markdown("""
            쿠키가 만료되어 오류가 발생하면 아래 방법으로 갱신하세요.

            1. 크롬에 **Cookie-Editor** (`cgagnier` 제작) 확장 프로그램 설치
            2. 네이버 로그인 후 해당 카페 접속
            3. Cookie-Editor 아이콘 클릭 → **Export** → **JSON (Netscape format)** 선택
            4. 복사된 JSON 전체를 Streamlit Cloud **Secrets**의 `NAVER_COOKIE`에 붙여넣기
            5. 저장 후 앱 재시작
            """)
        return

    # ── 헤더 구성 ────────────────────────────────────────────────
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
    results = []

    # ── 실제 API URL ─────────────────────────────────────────────
    list_url = (
        f"https://apis.naver.com/cafe-web/cafe-boardlist-api/v1"
        f"/cafes/25470135/menus/0/articles"
        f"?page=1&pageSize={page_size}&sortBy=TIME&viewType=L"
    )

    try:
        with st.spinner("카페 게시글 목록 불러오는 중..."):
            res = requests.get(list_url, headers=headers, timeout=10)

        # ── 디버그 모드 ──────────────────────────────────────────
        if debug_mode:
            st.markdown("#### 🛠 디버그 정보")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown(
                    f"<div class='status-badge'>HTTP 상태: {res.status_code}</div>",
                    unsafe_allow_html=True
                )
            with col_d2:
                st.markdown(
                    f"<div class='status-badge'>응답 크기: {len(res.text):,} bytes</div>",
                    unsafe_allow_html=True
                )
            with st.expander("원본 응답 (앞 1000자)"):
                st.code(res.text[:1000])

        # ── JSON 파싱 ────────────────────────────────────────────
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

        if articles is None:
            st.error("❌ 게시글 목록을 찾을 수 없습니다. 쿠키가 만료됐거나 접근이 제한됐을 수 있습니다.")
            if debug_mode:
                st.json(data)
            return

        # ── 시간 필터 적용 ───────────────────────────────────────
        filtered = []
        for art in articles:
            ts = (
                art.get('writeDateTimestamp')
                or art.get('lastUpdateDate')
                or art.get('createDate')
                or art.get('writeDate')
                or art.get('regDate')
            )
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

                    if art_time >= cutoff_time:
                        art['_parsed_time'] = art_time
                        filtered.append(art)
                except Exception:
                    filtered.append(art)
            else:
                filtered.append(art)

        st.info(f"📋 총 {len(articles)}개 글 중 최근 {hours_limit}시간 이내 **{len(filtered)}개** 글 분석 시작")

        if not filtered:
            st.warning(f"최근 {hours_limit}시간 내 게시글이 없습니다.")
            return

        # ── 본문 수집 및 도메인 추출 ──────────────────────────────
        prog_bar = st.progress(0)
        status_text = st.empty()

        for i, art in enumerate(filtered):
            article_id = art.get('articleId') or art.get('id')
            title = art.get('subject') or art.get('title') or f"글_{article_id}"
            art_time = art.get('_parsed_time')
            time_str = art_time.strftime('%Y-%m-%d %H:%M') if art_time else "-"

            status_text.caption(f"분석 중... ({i+1}/{len(filtered)}) {title[:30]}...")

            # 본문 API
            content_url = (
                f"https://apis.naver.com/cafe-web/cafe-articleapi/v2"
                f"/cafes/25470135/articles/{article_id}"
            )
            try:
                content_res = requests.get(content_url, headers=headers, timeout=10)

                # 본문 텍스트 추출
                try:
                    content_data = content_res.json()
                    # 본문 HTML 또는 텍스트 탐색
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

        # ── 결과 출력 ────────────────────────────────────────────
        st.markdown("---")

        if not results:
            st.info("ℹ️ 추출된 도메인이 없습니다.")
            return

        df = pd.DataFrame(results).drop_duplicates(subset=['도메인', '링크'])
        df = df.sort_values('작성시간', ascending=False).reset_index(drop=True)

        # 요약 지표
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f"<div class='status-badge'>🌐 추출 도메인: {df['도메인'].nunique()}개</div>",
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f"<div class='status-badge'>📄 분석 게시글: {len(filtered)}개</div>",
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                f"<div class='status-badge'>⏱ 수집 범위: 최근 {hours_limit}시간</div>",
                unsafe_allow_html=True
            )

        st.markdown("#### 📊 수집 결과")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 엑셀 다운로드
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

    except requests.exceptions.Timeout:
        st.error("⏱ 요청 시간이 초과됐습니다. 네트워크 상태를 확인해 주세요.")
    except requests.exceptions.ConnectionError:
        st.error("🔌 서버에 연결할 수 없습니다.")
    except ValueError as e:
        st.error(f"❌ 응답 파싱 오류: {e}\n\n쿠키가 만료됐거나 접근이 제한됐을 수 있습니다.")
        if debug_mode:
            st.code(res.text[:1000])
    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
