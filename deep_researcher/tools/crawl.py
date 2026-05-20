"""Crawl tool.

Fetches a single URL (or a small batch) and optionally follows in-domain
links one hop deep, returning extracted Pages. Used when the tool selector
identifies a specific authoritative source to read rather than searching.
"""
from __future__ import annotations

import asyncio
from typing import Iterable, List
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from ..search import Page, _USER_AGENT, _fetch_one


async def crawl_url(
    url: str,
    *,
    follow_links: int = 0,
    char_limit: int = 6000,
    timeout: float = 15.0,
) -> List[Page]:
    """Fetch `url`. If follow_links > 0, also fetch that many same-host links."""
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        pages: List[Page] = []
        seed = await _fetch_one(client, url, char_limit)
        if seed is None:
            return []
        pages.append(seed)

        if follow_links > 0:
            try:
                child_urls = await _same_host_links(url, client, limit=follow_links)
                children = await _follow(client, child_urls, char_limit)
            except Exception:
                children = []
            pages.extend(children)
        return pages


async def crawl_urls(
    urls: Iterable[str],
    char_limit: int = 6000,
    max_concurrency: int = 0,
) -> List[Page]:
    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        if max_concurrency and max_concurrency > 0:
            sem = asyncio.Semaphore(max_concurrency)

            async def fetch_limited(url: str) -> Page | None:
                async with sem:
                    return await _fetch_one(client, url, char_limit)

            coros = [fetch_limited(u) for u in urls]
        else:
            coros = [_fetch_one(client, u, char_limit) for u in urls]
        results = await asyncio.gather(*coros, return_exceptions=True)
    return [r for r in results if isinstance(r, Page) and r.text]


async def _same_host_links(url: str, client: httpx.AsyncClient, *, limit: int) -> List[str]:
    try:
        resp = await client.get(url)
        resp.raise_for_status()
    except Exception:
        return []
    base_host = urlparse(url).netloc
    soup = BeautifulSoup(resp.text, "lxml")
    seen: set[str] = set()
    out: List[str] = []
    for a in soup.find_all("a", href=True):
        full = urljoin(url, a["href"]).split("#", 1)[0]
        if not full.startswith(("http://", "https://")):
            continue
        if urlparse(full).netloc != base_host:
            continue
        if full == url or full in seen:
            continue
        seen.add(full)
        out.append(full)
        if len(out) >= limit:
            break
    return out


async def _follow(
    client: httpx.AsyncClient, urls: List[str], char_limit: int
) -> List[Page]:
    coros = [_fetch_one(client, u, char_limit) for u in urls]
    results = await asyncio.gather(*coros, return_exceptions=True)
    return [r for r in results if isinstance(r, Page) and r.text]
