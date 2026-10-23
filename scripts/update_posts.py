"""Substack과 네이버 블로그 RSS를 읽어 posts.json(최신 3편)을 만든다."""
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit

FEEDS = [
    ("Substack", "https://goodmovekr.substack.com/feed"),
    ("네이버 블로그", "https://rss.blog.naver.com/goodmove-kr.xml"),
]
LIMIT = 3
KST = timezone(timedelta(hours=9))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (goodmovekr.github.io feed reader)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def clean_link(link):
    p = urlsplit(link.strip())
    return urlunsplit((p.scheme, p.netloc, p.path, "", ""))


posts = []
ok = 0
for source, url in FEEDS:
    try:
        root = ET.fromstring(fetch(url))
    except Exception as e:  # 한쪽이 실패해도 다른 쪽으로 진행
        print(f"[실패] {source}: {e}", file=sys.stderr)
        continue
    ok += 1
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        when = item.findtext("pubDate")
        if not title or not link or not when:
            continue
        try:
            dt = parsedate_to_datetime(when).astimezone(KST)
        except Exception:
            continue
        posts.append({"title": title, "url": clean_link(link), "ts": dt.timestamp(),
                      "date": dt.strftime("%Y-%m-%d"), "source": source})
    print(f"[성공] {source}")

if ok == 0:
    print("두 곳 모두 읽지 못해 posts.json을 그대로 둡니다.", file=sys.stderr)
    sys.exit(0)

posts.sort(key=lambda p: p["ts"], reverse=True)
out = [{k: p[k] for k in ("title", "url", "date", "source")} for p in posts[:LIMIT]]
with open("posts.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
    f.write("\n")
print(json.dumps(out, ensure_ascii=False, indent=2))
