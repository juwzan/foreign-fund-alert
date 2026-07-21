"""금융감독원 보도자료 게시판(B0000188)에서 "외국인 증권투자 동향" 제목검색 결과를 조회.

목록/상세 페이지 모두 서버가 완성된 HTML을 그대로 내려주므로(별도 XHR/JSON API,
로그인/세션 불필요) requests + BeautifulSoup만으로 충분하다.
"""
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.fss.or.kr"
LIST_URL = f"{BASE_URL}/fss/bbs/B0000188/list.do"
VIEW_URL = f"{BASE_URL}/fss/bbs/B0000188/view.do"
MENU_NO = "200218"
SEARCH_CND = "1"  # 제목검색
SEARCH_WRD = "외국인 증권투자 동향"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT_SEC = 20


def _cell_text(td):
    label = td.find("span", class_="only-m")
    if label:
        label.decompose()
    return td.get_text(strip=True)


def fetch_list(page_index=1):
    """목록 조회 -> [{no, ntt_id, title, dept, date, view_url}], 최신순(번호 내림차순)."""
    params = {
        "menuNo": MENU_NO,
        "bbsId": "",
        "cl1Cd": "",
        "pageIndex": page_index,
        "sdate": "",
        "edate": "",
        "searchCnd": SEARCH_CND,
        "searchWrd": SEARCH_WRD,
    }
    resp = requests.get(LIST_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT_SEC)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    rows = []
    for tr in soup.select("table tbody tr"):
        cells = tr.find_all("td")
        if len(cells) < 4:
            continue
        no_text = _cell_text(cells[0])
        if not no_text.isdigit():
            continue
        title_link = cells[1].find("a")
        if not title_link or not title_link.get("href"):
            continue
        href = title_link["href"]
        query = dict(p.split("=", 1) for p in href.split("?", 1)[1].split("&") if "=" in p)
        ntt_id = query.get("nttId")
        if not ntt_id:
            continue
        rows.append({
            "no": int(no_text),
            "ntt_id": ntt_id,
            "title": title_link.get_text(strip=True),
            "dept": _cell_text(cells[2]) if len(cells) > 2 else "",
            "date": _cell_text(cells[3]) if len(cells) > 3 else "",
            "view_url": f"{VIEW_URL}?nttId={ntt_id}&menuNo={MENU_NO}",
        })

    rows.sort(key=lambda r: r["no"], reverse=True)
    return rows


def fetch_detail(ntt_id):
    """상세 조회 -> {body_text, attachments:[{name, url}]}.

    본문(div.dbdata)에 보도자료 요약 텍스트가 이미 들어있어 PDF/HWP를 열 필요가 없다.
    """
    params = {"nttId": ntt_id, "menuNo": MENU_NO}
    resp = requests.get(VIEW_URL, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT_SEC)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    body_div = soup.select_one("div.dbdata")
    body_text = _extract_body_text(body_div) if body_div else ""

    attachments = []
    for item in soup.select(".file-list__set__item"):
        link = item.find("a", href=lambda h: h and "fileDown.do" in h)
        if not link:
            continue
        name_span = item.select_one("span.name")
        name = str(name_span.contents[0]).strip() if name_span and name_span.contents else link.get_text(strip=True)
        attachments.append({"name": name, "url": urljoin(BASE_URL, link["href"])})

    return {"body_text": body_text, "attachments": attachments}


def _extract_body_text(tag):
    for br in tag.find_all("br"):
        br.replace_with("\n")
    lines = [line.strip() for line in tag.get_text().splitlines()]

    cleaned = []
    prev_blank = False
    for line in lines:
        if line == "":
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False
        cleaned.append(line)
    return "\n".join(cleaned).strip()
