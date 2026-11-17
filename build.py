"""Build the Korean blog directory from RSS and Atom feeds."""
import concurrent.futures
import json
import hashlib
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path
from urllib.parse import urljoin, urlsplit

OUT = Path("public")
CACHE = Path("snapshot.json")
KST = timezone(timedelta(hours=9))
STYLE_VERSION = hashlib.sha256(Path("style.css").read_bytes()).hexdigest()[:12]


def fetch(url):
    data = subprocess.check_output([
        "curl", "-fsSL", "--user-agent", "JagunbaeFeeds/1.0 (+https://blogs.jagunbae.com/)",
        "--max-time", "30", "--retry", "1", url,
    ])
    root = ET.fromstring(data)
    for el in root.iter():
        el.tag = el.tag.split("}")[-1]
    channel = root.find("channel")
    if channel is None:
        if root.tag != "feed":
            raise ValueError("RSS/Atom 채널 없음")
        channel = root
    posts = {}
    for item in channel.findall("item") + channel.findall("entry"):
        links = [el.get("href") or el.text for el in item.findall("link") if el.get("rel", "alternate") == "alternate"]
        date = next((item.findtext(k) for k in ("pubDate", "published", "date", "updated") if item.findtext(k)), None)
        if not date or not links or not links[0]:
            continue
        link = urljoin(url, links[0].strip())
        if urlsplit(link).scheme not in ("http", "https"):
            continue
        try:
            dt = datetime.fromisoformat(date.replace("Z", "+00:00"))
        except ValueError:
            dt = parsedate_to_datetime(date)
        posts[link] = [int((dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp()), item.findtext("title") or "제목 없음", link]
    return {"name": channel.findtext("title") or urlsplit(url).hostname, "posts": sorted(posts.values(), reverse=True)[:50]}


def anchor(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def page(path, title, content, updated_at):
    period = "오전" if updated_at.hour < 12 else "오후"
    hour = updated_at.hour % 12 or 12
    updated_label = (
        f"{updated_at.year}년 {updated_at.month}월 {updated_at.day}일 "
        f"{period} {hour}시 {updated_at.minute:02d}분 {updated_at.second:02d}초"
    )
    file = OUT / path / "index.html"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(f'''<!doctype html>
<html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · 글 쓰는 블로그</title>
<link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="/style.css?v={STYLE_VERSION}">
<header><h1><a href="/">글 쓰는 블로그</a></h1><p><a href="https://jagunbae.com">작은배</a>가 모은 글 쓰는 이웃들.</p>
</header><main>{content}</main>
<footer>마지막 업데이트: <time datetime="{updated_at.isoformat()}">{updated_label}</time><p>문의나 제안이 있다면 언제든 <a href="https://letterbird.co/kang">이메일 주세요</a>.</p></footer></html>''')


def author(url):
    return '/authors/' + urlsplit(url).hostname + '/'


def listing(rows):
    result = []
    for date, title, link, url, name in rows:
        day = datetime.fromtimestamp(date, KST).strftime('%Y-%m-%d')
        result.append(f'<li>{anchor(link,title)}<small><time>{day}</time> · {anchor(author(url),name)}</small></li>')
    return '<ol>' + ''.join(result) + '</ol>' if result else '<p>아직 수집된 글이 없습니다.</p>'


def main():
    authors = json.loads(Path("feeds.json").read_text())
    saved = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    fresh = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        jobs = {pool.submit(fetch, url): url for url in authors}
        for job in concurrent.futures.as_completed(jobs):
            url = jobs[job]
            try:
                saved[url] = job.result()
                fresh += 1
                print(url, saved[url]["name"], len(saved[url]["posts"]))
            except Exception as exc:
                print(url, exc)
    if not fresh:
        raise RuntimeError("모든 피드 갱신 실패")
    updated_at = datetime.now(KST)
    all_posts = {}
    blogs = []
    for url in authors:
        feed = saved.get(url, {"name": urlsplit(url).hostname, "posts": []})
        name = authors[url].lstrip("@")
        rows = [(*post, url, name) for post in feed["posts"]]
        all_posts.update({row[2]: row for row in rows})
        domain = urlsplit(url).netloc
        page(author(url).strip('/'), name, f'<h2>{escape(name)}</h2><p>{anchor("https://" + domain, domain)} · {anchor(url,"RSS")}</p>'+listing(rows), updated_at)
        blogs.append((name, anchor(author(url),name)))
    directory = ''.join(f'<li>{a}</li>' for _,a in sorted(blogs))
    (OUT / "blogs" / "index.html").unlink(missing_ok=True)
    page("", "피드", '<h2>피드</h2><details><summary>블로그 둘러보기</summary><ul class="authors">'+directory+'</ul></details>'+listing(sorted(all_posts.values(), reverse=True)[:100]), updated_at)
    (OUT/"style.css").write_bytes(Path("style.css").read_bytes())
    (OUT/"CNAME").write_text("blogs.jagunbae.com\n")
    CACHE.write_text(json.dumps({u:saved[u] for u in authors if u in saved}, ensure_ascii=False,indent=1)+'\n')


if __name__ == "__main__":
    main()
