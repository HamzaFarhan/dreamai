import asyncio
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import Page, async_playwright

from dreamai.md_utils import urls_to_md

logger.add("crawler.log", rotation="10 MB")


class DAICrawler:
    def __init__(
        self,
        start_url: str,
        url_prefix: str = "",
        max_depth: int = 3,
        max_links: int = 100,
        file_path: str = "crawled_data.json",
        overwrite: bool = True,
        rate_limit: float = 0.5,
    ):
        if overwrite:
            Path(file_path).unlink(missing_ok=True)
        self.start_url = start_url
        self.url_prefix = url_prefix
        self.max_depth = max_depth
        self.max_links = max_links
        self.rate_limit = rate_limit
        self.visited = set()
        self.file_path = file_path

    async def extract_data(self, page: Page) -> dict:
        data = {}
        data["title"] = await page.title()
        description = await page.evaluate(
            "document.querySelector('meta[name=\"description\"]')?.content"
        )
        if description:
            data["meta_description"] = description
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        main_content = (
            soup.find("main") or soup.find(id="content") or soup.find(class_="content")
        )
        if main_content:
            data["main_content"] = main_content.get_text(strip=True)
        else:
            data["main_content"] = soup.body.get_text(strip=True) if soup.body else ""
        data["headings"] = []
        for heading in soup.find_all(["h1", "h2", "h3"]):
            data["headings"].append(
                {"level": heading.name, "text": heading.get_text(strip=True)}
            )
        data["links"] = []
        for link in soup.find_all("a", href=True):
            data["links"].append({"text": link.get_text(strip=True), "href": link["href"]})
        data["images"] = []
        for img in soup.find_all("img", src=True):
            data["images"].append({"src": img["src"], "alt": img.get("alt", "")})
        return data

    async def crawl(self, page: Page, url: str, depth: int = 0):
        if depth > self.max_depth:
            logger.info(f"Max depth reached for URL: {url}")
            return

        if len(self.visited) >= self.max_links:
            logger.info(f"Max links reached. Stopping crawl for URL: {url}")
            return

        if not url.startswith(self.url_prefix):
            logger.info(f"URL {url} does not match the prefix {self.url_prefix}. Skipping.")
            return

        if url in self.visited:
            logger.info(f"URL {url} already visited. Skipping.")
            return

        parsed_url = urlparse(url)
        if parsed_url.fragment or parsed_url.query:
            logger.info(f"Skipping irrelevant URL: {url}")
            return

        logger.info(f"Scraping: {url} (Depth: {depth})")
        await asyncio.sleep(self.rate_limit)  # Simple rate limiting

        try:
            await page.goto(url, wait_until="networkidle")
            self.visited.add(url)
            md_data = [md.model_dump() for md in urls_to_md(url)]
            try:
                current_data = json.loads(Path(self.file_path).read_text())
            except Exception:
                current_data = []
            current_data.extend(md_data)
            with open(self.file_path, "w") as f:
                json.dump(current_data, f, indent=2)

            links = await page.query_selector_all("a")
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    if href:
                        full_url = urljoin(url, href)
                        if urlparse(full_url).netloc == urlparse(self.start_url).netloc:
                            await self.crawl(page, full_url, depth + 1)
                except Exception as e:
                    logger.warning(f"Error processing link on {url}: {e}")
                    continue

        except Exception as e:
            logger.exception(f"Error scraping {url}: {str(e)}")

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await self.crawl(page, self.start_url)
            await browser.close()
