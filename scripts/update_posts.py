"""Substack과 네이버 블로그 RSS를 읽어 posts.json(최신 3편)을 만든다.
한 곳이 막히면 그곳 글은 지난번 posts.json에 있던 것을 그대로 쓴다."""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit

FEEDS = [
    ("Substack", ["https://goodmovekr.substack.com/feed",
                  "https://goodmovekr.substack.com/api/v1/archive?sort=new&limit=10"]),
    ("네이버 블로그", ["https://rss.blog.naver.com/goodmove-kr.xml"]),
]
LIMIT = 3
KST = timezone(timedelta(hours=9))
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, application/json;q=0.9, */*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def clean_link(link):
    p = urlsplit(link.strip())
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def from_rss(body, source):
    out = []
    for item in ET.fromstring(body).iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        when = item.findtext("pubDate")
        if not title or not link or not when:
            continue
        try:
            dt = parsedate_to_datetime(when).astimezone(KST)
        except Exception:
            continue
        out.append({"title": title, "url": clean_link(link), "date": dt.strftime("%Y-%m-%d"), "source": source})
    return out


def from_substack_api(body, source):
    out = []
    for p in json.loads(body):
        title, link, when = p.get("title"), p.get("canonical_url"), p.get("post_date")
        if not title or not link or not when:
            continue
        dt = datetime.fromisoformat(when.replace("Z", "+00:00")).astimezone(KST)
        out.append({"title": title.strip(), "url": clean_link(link), "date": dt.strftime("%Y-%m-%d"), "source": source})
    return out


try:
    with open("posts.json", encoding="utf-8") as f:
        previous = json.load(f)
except Exception:
    previous = []

posts = []
for source, urls in FEEDS:
    got = None
    for url in urls:
        try:
            body = fetch(url)
            got = from_substack_api(body, source) if "/api/" in url else from_rss(body, source)
            print(f"[성공] {source}: {url}")
            break
        except Exception as e:
            print(f"[실패] {source}: {url}: {e}", file=sys.stderr)
    if got is None:
        got = [p for p in previous if p.get("source") == source]
        print(f"[유지] {source}: 지난번 글 {len(got)}편을 그대로 씁니다.")
    posts.extend(got)

if not posts:
    print("글을 하나도 얻지 못해 posts.json을 그대로 둡니다.", file=sys.stderr)
    sys.exit(0)

seen, out = set(), []
for p in sorted(posts, key=lambda p: p["date"], reverse=True):
    if p["url"] in seen:
        continue
    seen.add(p["url"])
    out.append(p)
out = out[:LIMIT]
with open("posts.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(json.dumps(out, ensure_ascii=False, indent=2))
