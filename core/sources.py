"""Agent 1: acquire open news feeds and primary-source releases (stdlib only)."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.request import Request, urlopen
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import hashlib
import re
import time
import xml.etree.ElementTree as ET

USER_AGENT = "OPEN-WORLD-Research-Desk/2.0 (RSS reader; personal, non-commercial)"
ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"


def fetch_bytes(url: str, timeout: float = 13.0) -> bytes:
    if urlsplit(url).scheme != "https":
        raise ValueError("Only HTTPS data sources are permitted")
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, text/xml, */*"})
    with urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise OSError(f"HTTP {resp.status}")
        return resp.read(2_200_000)


def clean(txt: str, cap=460) -> str:
    txt = re.sub(r"<[^>]+>", " ", txt or "")
    return re.sub(r"\s+", " ", unescape(txt)).strip()[:cap]


def normalized_url(raw: str) -> str:
    try:
        u = urlsplit(raw.strip())
        if u.scheme not in ("http", "https"):
            return ""
        params = [(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if not (k.lower().startswith('utm_') or k.lower() in ('fbclid','gclid','mc_cid','mc_eid'))]
        return urlunsplit((u.scheme, u.netloc.lower(), u.path, urlencode(params), ""))
    except ValueError:
        return ""


def parse_date(raw):
    if not raw:
        return None
    try:
        stamp = parsedate_to_datetime(raw)
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError):
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except (TypeError, ValueError, OverflowError):
            return None


def get(node, *paths):
    for path in paths:
        val = node.findtext(path)
        if val:
            return val.strip()
    return ""


def parse_feed(data: bytes, source: dict, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    root = ET.fromstring(data)
    items = root.findall(".//item")
    atom = False
    if not items:
        items = root.findall(".//" + ATOM + "entry")
        atom = True
    out = []
    for element in items[:85]:
        if atom:
            link = ""
            for tag in element.findall(ATOM + "link"):
                if tag.attrib.get("rel", "alternate") == "alternate":
                    link = tag.attrib.get("href", "")
                    break
            title = get(element, ATOM + "title")
            desc = get(element, ATOM + "summary", ATOM + "content")
            published = get(element, ATOM + "published", ATOM + "updated")
        else:
            link = get(element, "link")
            title = get(element, "title")
            desc = get(element, "description", "{http://purl.org/rss/1.0/modules/content/}encoded")
            published = get(element, "pubDate", DC + "date", "date")
        link = normalized_url(link)
        title = clean(title, 245)
        if not (title and link):
            continue
        published_at = parse_date(published)
        if not published_at:
            # A missing article date is NOT publication time; preserve uncertainty.
            continue
        date = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if date > now + timedelta(minutes=10) or date < now - timedelta(days=5):
            continue
        out.append({
            "id": hashlib.sha256((source["name"] + "|" + link).encode()).hexdigest()[:18],
            "title": title, "summary": clean(desc), "url": link,
            "source": source["name"], "source_type": source.get("type", "media"),
            "published_at": published_at, "language": "original", "collected_at": now.isoformat().replace("+00:00", "Z")
        })
    return out


def collect(feeds, now=None, fetcher=fetch_bytes, max_workers=7):
    now = now or datetime.now(timezone.utc)
    results, status = [], []
    def task(source):
        start = time.monotonic()
        try:
            articles = parse_feed(fetcher(source["url"]), source, now)
            return articles, {"name":source["name"],"ok":True,"count":len(articles),"elapsed_ms":int((time.monotonic()-start)*1000)}
        except Exception as exc:
            return [], {"name":source["name"],"ok":False,"count":0,"error":str(exc)[:150],"elapsed_ms":int((time.monotonic()-start)*1000)}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(task, source): source for source in feeds}
        for future in as_completed(futures):
            articles, health = future.result()
            results.extend(articles)
            status.append(health)
    dedup = {v["id"]:v for v in results}
    return list(dedup.values()), sorted(status,key=lambda x:x["name"])
