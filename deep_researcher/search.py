"""Web search + page fetch.

Search backend: Serper (if SERPER_API_KEY is set) → DuckDuckGo fallback.
Fetch: httpx + BeautifulSoup, trimmed to FETCH_CHAR_LIMIT chars.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import List

import httpx
from bs4 import BeautifulSoup


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


@dataclass
class Page:
    url: str
    title: str
    text: str


_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 mvp-deep-researcher"
)


async def search(query: str, num: int = 5) -> List[SearchResult]:
    if os.environ.get("SERPER_API_KEY"):
        return await _serper(query, num)
    return await asyncio.to_thread(_ddg, query, num)


async def _serper(query: str, num: int) -> List[SearchResult]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": os.environ["SERPER_API_KEY"],
                "Content-Type": "application/json",
            },
            json={"q": query, "num": num},
        )
        resp.raise_for_status()
        data = resp.json()
    return [
        SearchResult(
            title=item.get("title", ""),
            url=item.get("link", ""),
            snippet=item.get("snippet", ""),
        )
        for item in data.get("organic", [])[:num]
    ]


def _ddg(query: str, num: int) -> List[SearchResult]:
    # duckduckgo-search is sync — called via asyncio.to_thread above
    from duckduckgo_search import DDGS

    with DDGS() as ddgs:
        hits = list(ddgs.text(query, max_results=num))
    return [
        SearchResult(
            title=h.get("title", ""),
            url=h.get("href", ""),
            snippet=h.get("body", ""),
        )
        for h in hits
    ]


async def fetch_many(urls: List[str], char_limit: int = 6000) -> List[Page]:
    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        coros = [_fetch_one(client, u, char_limit) for u in urls]
        results = await asyncio.gather(*coros, return_exceptions=True)
    return [r for r in results if isinstance(r, Page) and r.text]


async def _fetch_one(client: httpx.AsyncClient, url: str, char_limit: int) -> Page | None:
    try:
        resp = await client.get(url)
        resp.raise_for_status()
    except Exception:
        return None

    content_type = resp.headers.get("content-type", "")
    if "html" not in content_type and "text" not in content_type:
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    title = (soup.title.string.strip() if soup.title and soup.title.string else url)

    text = " ".join(soup.get_text(separator=" ").split())
    return Page(url=url, title=title, text=text[:char_limit])
