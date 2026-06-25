"""
Scrapy spider for Japanese corporate profile pages.

Deployed on AWS ECS Fargate; output lands in S3 bronze zone.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterator

import scrapy


class CorporateProfileSpider(scrapy.Spider):
    name = "corporate_profile"
    allowed_domains: list[str] = []
    custom_settings = {
        "DOWNLOAD_DELAY": 1.5,
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "FEED_EXPORT_ENCODING": "utf-8",
    }

    def __init__(self, seed_urls: str = "", *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.start_urls = [u.strip() for u in seed_urls.split(",") if u.strip()]

    def parse(self, response: scrapy.http.Response) -> Iterator[dict[str, Any]]:
        company_name = response.css("h1.company-name::text").get("").strip()
        corporate_number = response.css("[data-corporate-number]::attr(data-corporate-number)").get()

        yield {
            "source": "corporate_profile",
            "crawl_url": response.url,
            "crawl_timestamp": datetime.now(timezone.utc).isoformat(),
            "content_hash": hashlib.sha256(response.body).hexdigest(),
            "company_name": company_name,
            "corporate_number": corporate_number,
            "address": self._extract_text(response, ".address"),
            "employee_count": self._extract_int(response, ".employee-count"),
            "business_description": self._extract_text(response, ".business-description"),
            "raw_html_length": len(response.body),
        }

        for link in response.css("a.company-link::attr(href)").getall():
            yield response.follow(link, callback=self.parse)

    @staticmethod
    def _extract_text(response: scrapy.http.Response, selector: str) -> str | None:
        value = response.css(f"{selector}::text").get()
        return value.strip() if value else None

    @staticmethod
    def _extract_int(response: scrapy.http.Response, selector: str) -> int | None:
        text = response.css(f"{selector}::text").get()
        if not text:
            return None
        digits = "".join(c for c in text if c.isdigit())
        return int(digits) if digits else None
