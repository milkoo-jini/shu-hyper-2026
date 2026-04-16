import streamlit as st
import requests
import re
import json
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta, timezone
import time


KST = timezone(timedelta(hours=9))
MAX_PAGES = 20
BLOG_ID = "alymppdyi"

# 명백한 정상 도메인 제외 (서브도메인 포함, 피싱 도메인은 제외 안 됨)
EXCLUDE_DOMAINS = {
    # 네이버 계열
    'naver.com', 'naver.me', 'cafe.naver.com', 'blog.naver.com',
    'search.naver.com', 'map.naver.com', 'shopping.naver.com',
    'news.naver.com', 'pstatic.net', 'naverusercontent.com', 'naver.it',
    # 다음/카카오 계열
    'daum.net', 'daumcdn.net', 'kakao.com', 'kakaocorp.com', 'kakaocdn.net',
    'kakaopage.com', 'kko.to',
    # 구글 계열
    'google.com', 'google.co.kr', 'googleapis.com', 'gstatic.com', 'goo.gl',
    # 소셜/미디어
    'youtube.com', 'youtu.be', 'band.us',
    'instagram.com', 'facebook.com', 'fb.com',
    'twitter.com', 'x.com', 'tiktok.com',
    # 백과사전
    'wikipedia.org', 'namu.wiki',
    # 국내 주요 언론사
    'edaily.co.kr', 'chosun.com', 'joins.com', 'joongang.co.kr',
    'hani.co.kr', 'khan.co.kr', 'donga.com', 'mk.co.kr',
    'hankyung.com', 'yna.co.kr', 'yonhapnews.co.kr',
    'newsis.com', 'news1.kr', 'nocutnews.co.kr', 'ohmynews.com',
    'sbs.co.kr', 'kbs.co.kr', 'mbc.co.kr', 'jtbc.co.kr', 'ytn.co.kr',
    'etnews.com', 'dt.co.kr', 'zdnet.co.kr', 'bloter.net', 'asiae.co.kr',
}


def is_excluded(domain: str) -> bool:
    d = domain.lower()
    return any(d == ex or d.endswith('.' + ex) for ex in EXCLUDE_DOMAINS)


# http/https URL 패턴
URL_PATTERN = re.compile(
    r'https?://([a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?'
    r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*'
    r'\.[a-zA-Z]{2,})'
)

# http 없이 텍스트로만 적힌 도메인 패턴 (주요 TLD만)
PLAIN_DOMAIN_PATTERN = re.compile(
    r'\b([a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]'
    r'\.(?:com|net|org|io|kr|co\.kr|shop|site|online|store|info|biz|xyz|top|club))\b'
)


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
    """http/https URL + 텍스트 도메인 모두 추출 (명백한 정상 도메인 제외)"""
    found = set()
    for d in URL_PATTERN.findall(text):
        if not is_excluded(d.lower()):
            found.add(d.lower())
    for d in PLAIN_DOMAIN_PATTERN.findall(text):
        if not is_excluded(d.lower()):
            found.add(d.lower())
    return list(found)


# ─────────────────────────────────────────────────────────────
# 카페 수집
# ─────────────────────────────────────────────────────────────
def collect_cafe(cookie_value: str, hours_limit: int, page_size: int,
                 debug_mode: bool, status_placeholder, stop_flag: callable) -> list:
    """네이버 카페 게시글에서 도메인 수집"""

    base_headers = {
        'User-Agent': (
            'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) '
            'AppleWebKit/605.1.15 (KHTML, like Gecko) '
            'Version/18.5 Mobile/15E148 Safari/604.1'
        ),
        'Cookie': cookie_value,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Origin': 'https://cafe.naver.com',
        'x-cafe-product': 'pc',
        'sec-ch-ua': '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"iOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
    }

    cutoff_time = datetime.now(KST) - timedelta(hours=hours_limit)
    results = []
    page = 1
    stop = False

    while not stop and page <= MAX_PAGES:
        if stop_flag():
            break

        status_placeholder.caption(f"📋 카페 페이지 {page} 수집 중...")

        list_url = (
            f"https://apis.naver.com/cafe-web/cafe-boardlist-api/v1"
            f"/cafes/25470135/menus/0/articles"
            f"?page={page}&pageSize={page_size}&sortBy=TIME&viewType=L"
        )
        list_headers = {
            **base_headers,
            'Referer': 'https://cafe.naver.com/ca-fe/cafes/25470135/articles',
        }

        try:
            res = requests.get(list_url, headers=list_headers, timeout=10)

            if debug_mode and page == 1:
                st.markdown("**🛠 카페 디버그**")
                st.code(f"HTTP {res.status_code} | {len(res.text):,} bytes\n{res.text[:800]}")

            data = res.json()
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
                item = art.get('item', art)
                ts = (
                    item.get('writeDateTimestamp')
                    or item.get('lastUpdateDate')
                    or item.get('createDate')
                    or item.get('writeDate')
                    or item.get('regDate')
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
                    stop = True
                    break

                article_id = item.get('articleId') or item.get('id')
                title = item.get('subject') or item.get('title') or f"글_{article_id}"
                summary = item.get('summary') or ''
                time_str = art_time.strftime('%Y-%m-%d %H:%M') if art_time else "-"

                full_text = title + " " + summary
                domains = extract_domains_from_text(full_text)

                for d in domains:
                    results.append({
                        "출처": "카페",
                        "도메인": d,
                        "작성시간": time_str,
                        "글제목": title,
                        "링크": f"https://cafe.naver.com/f-e/cafes/25470135/articles/{article_id}"
                    })

        except Exception as e:
            st.error(f"❌ 카페 페이지 {page} 오류: {e}")
            stop = True
            break

        page += 1
        time.sleep(0.3)

    return results


# ─────────────────────────────────────────────────────────────
# 블로그 수집
# ─────────────────────────────────────────────────────────────
def _parse_blog_timestamp(ts_str: str) -> datetime | None:
    """블로그 날짜 문자열 → KST datetime"""
    if not ts_str:
        return None
    s = ts_str.strip()

    # "N시간 전" 처리
    m = re.match(r'(\d+)시간\s*전', s)
    if m:
        return datetime.now(KST) - timedelta(hours=int(m.group(1)))

    # "N분 전" 처리
    m = re.match(r'(\d+)분\s*전', s)
    if m:
        return datetime.now(KST) - timedelta(minutes=int(m.group(1)))

    # "방금 전" 처리
    if '방금' in s:
        return datetime.now(KST)

    formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y. %m. %d. %H:%M",
        "%Y.%m.%d.",
        "%Y-%m-%d %H:%M:%S",
        "%Y%m%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=KST)
            return dt.astimezone(KST)
        except ValueError:
            continue
    return None



def _fetch_blog_post_text(blog_id: str, log_no: str, headers: dict) -> str:
    """블로그 본문 HTML에서 텍스트 추출 (도메인 탐지용)"""
    try:
        url = f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}&redirect=Dlog"
        res = requests.get(url, headers=headers, timeout=10)
        # HTML 태그 제거하고 텍스트만 반환
        text = re.sub(r'<[^>]+>', ' ', res.text)
        return text
    except Exception:
        return ""


def collect_blog(cookie_value: str, hours_limit: int,
                 debug_mode: bool, status_placeholder, stop_flag: callable) -> list:
    """네이버 블로그(alymppdyi) 포스팅에서 도메인 수집"""

    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Cookie': cookie_value,
        'Accept': 'application/json, text/html, */*',
        'Accept-Language': 'ko-KR,ko;q=0.9',
        'Referer': f'https://blog.naver.com/{BLOG_ID}',
    }

    cutoff_time = datetime.now(KST) - timedelta(hours=hours_limit)
    results = []
    page = 1
    stop = False

    while not stop and page <= MAX_PAGES:
        if stop_flag():
            break

        status_placeholder.caption(f"📝 블로그 페이지 {page} 수집 중...")

        # 블로그 포스트 목록 API (JSON 반환 엔드포인트)
        list_url = (
            f"https://blog.naver.com/PostTitleListAsync.naver"
            f"?blogId={BLOG_ID}&currentPage={page}&countPerPage=30"
            f"&postListNo=&categoryNo=0&activeStatus=1&blogType=&viewdate="
        )

        try:
            res = requests.get(list_url, headers=headers, timeout=10)

            if debug_mode and page == 1:
                st.markdown("**🛠 블로그 디버그**")
                st.code(f"HTTP {res.status_code} | {len(res.text):,} bytes\n{res.text[:800]}")

            # JSON 응답 파싱
            try:
                data = res.json()
            except Exception:
                # HTML일 경우 스킵
                stop = True
                break

            # 포스트 목록 추출 (네이버 블로그 PostList API 구조)
            posts = None
            for key_path in [
                ['postList'],
                ['result', 'postList'],
                ['message', 'result', 'postList'],
            ]:
                try:
                    node = data
                    for k in key_path:
                        node = node[k]
                    if isinstance(node, list):
                        posts = node
                        break
                except (KeyError, TypeError):
                    continue

            if not posts:
                # 포스트가 없거나 마지막 페이지
                stop = True
                break

            for post in posts:
                from urllib.parse import unquote_plus
                log_no = str(post.get('logNo') or post.get('no') or '')
                raw_title = post.get('title') or post.get('subject') or f"글_{log_no}"
                title = unquote_plus(raw_title)
                add_date = post.get('addDate') or post.get('writeDate') or post.get('regDate') or ''
                summary = unquote_plus(post.get('summary') or post.get('content') or '')

                # 날짜 파싱
                post_time = _parse_blog_timestamp(str(add_date))
                if post_time and post_time < cutoff_time:
                    stop = True
                    break

                time_str = post_time.strftime('%Y-%m-%d %H:%M') if post_time else "-"
                post_url = f"https://blog.naver.com/{BLOG_ID}/{log_no}"

                # 제목 + 요약 + 본문에서 도메인 추출
                # title의 공백 제거 버전도 포함 (예: "bit-ment .com" → "bit-ment.com")
                title_nospace = title.replace(' ', '')
                full_text = title + " " + title_nospace + " " + summary
                if log_no:
                    full_text += " " + _fetch_blog_post_text(BLOG_ID, log_no, headers)
                domains = extract_domains_from_text(full_text)

                for d in domains:
                    results.append({
                        "출처": "블로그",
                        "도메인": d,
                        "작성시간": time_str,
                        "글제목": title,
                        "링크": post_url,
                    })

        except Exception as e:
            st.error(f"❌ 블로그 페이지 {page} 오류: {e}")
            stop = True
            break

        page += 1
        time.sleep(0.4)

    return results


# ─────────────────────────────────────────────────────────────
# 메인 앱
# ─────────────────────────────────────────────────────────────
def run_domain_collector():

    # 세션 상태 초기화
    if 'domain_running' not in st.session_state:
        st.session_state.domain_running = False
    if 'domain_stop' not in st.session_state:
        st.session_state.domain_stop = False

    # 쿠키 로드
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

    # 타이틀
    st.markdown("## 🔎 사기 의심 도메인 수집")
    st.markdown(
        "<p style='color:#868e96; margin-top:-0.5rem;'>"
        "네이버 카페 게시글 및 블로그 포스팅에서 최근 N시간 내 언급된 도메인을 추출합니다."
        "</p>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    # 설정
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
            [1, 2, 3, 6, 12, 24, 48, 72, 168, 720],
            index=3,
            format_func=lambda x: f"최근 {x}시간" if x < 48 else (
                f"최근 {x // 24}일" if x < 720 else "최근 30일"
            )
        )
        page_size = st.selectbox("카페 페이지당 글 수", [15, 30, 50], index=1)
        debug_mode = st.checkbox("디버그 모드", value=False)

    st.markdown("---")

    # 버튼 영역
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        run_btn = st.button(
            "🚀 카페 + 블로그 수집 시작",
            use_container_width=True,
            type="primary"
        )
    with col_btn2:
        stop_btn = st.button("⏹ 수집 중단", use_container_width=True, type="secondary")

    if stop_btn:
        st.session_state.domain_stop = True
        st.session_state.domain_running = False
        st.warning("⏹ 수집이 중단됐습니다.")
        return

    if not run_btn:
        if not st.session_state.domain_running:
            with st.expander("📌 쿠키 갱신 방법", expanded=False):
                st.markdown("""
                1. 크롬에 **Cookie-Editor** (`cgagnier` 제작) 설치
                2. 네이버 로그인 후 해당 카페 접속
                3. Cookie-Editor → **Export** → **JSON (Netscape format)**
                4. 복사한 JSON 전체를 Streamlit Cloud **Secrets**의 `NAVER_COOKIE`에 붙여넣기
                5. 저장 후 앱 재시작
                """)
        return

    # 수집 시작
    st.session_state.domain_running = True
    st.session_state.domain_stop = False

    def stop_flag():
        return st.session_state.domain_stop

    st.info(f"📋 최근 {hours_limit}시간 이내 게시글 수집 중...")

    cafe_status = st.empty()
    cafe_status.caption("📋 카페 수집 준비 중...")
    blog_status = st.empty()
    blog_status.caption("📝 블로그 수집 준비 중...")

    cafe_results = []
    blog_results = []

    # 카페 수집
    cafe_results = collect_cafe(
        cookie_value, hours_limit, page_size,
        debug_mode, cafe_status, stop_flag
    )
    cafe_status.caption(f"✅ 카페 수집 완료 ({len(cafe_results)}건)")

    # 블로그 수집
    blog_results = collect_blog(
        cookie_value, hours_limit,
        debug_mode, blog_status, stop_flag
    )
    blog_status.caption(f"✅ 블로그 수집 완료 ({len(blog_results)}건)")

    st.session_state.domain_running = False

    # 결과 출력
    st.markdown("---")

    all_results = cafe_results + blog_results

    if not all_results:
        st.info("ℹ️ 추출된 도메인이 없습니다.")
        return

    df = pd.DataFrame(all_results).drop_duplicates(subset=['도메인', '링크'])
    df = df.sort_values('작성시간', ascending=False).reset_index(drop=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='status-badge'>🌐 추출 도메인: {df['도메인'].nunique()}개</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='status-badge'>📄 분석 게시글: {df['글제목'].nunique()}개</div>", unsafe_allow_html=True)
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


# 앱 진입점
run_domain_collector()
