import asyncio
import logging
import os
import re
import time
from collections import deque
from urllib.parse import urljoin, urlparse

import aiohttp
from playwright.async_api import async_playwright

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class WebScraper:
    def __init__(self, base_url, base_path, max_depth=3, max_urls=100, rate_limit=1):
        self.base_url = base_url
        self.base_path = base_path
        self.max_depth = max_depth
        self.max_urls = max_urls
        self.rate_limit = rate_limit
        self.all_urls = set()
        self.visited = set()
        self.queue = deque([(base_url, 0)])  # (url, depth)
        self.last_request_time = 0

    async def fetch_robots_txt(self):
        robots_url = urljoin(self.base_url, "/robots.txt")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(robots_url) as response:
                    if response.status == 200:
                        return await response.text()
            except aiohttp.ClientError:
                logger.warning(f"Could not fetch robots.txt from {robots_url}")
        return ""

    def is_allowed(self, url, robots_txt):
        # Implement robots.txt parsing and checking here
        # This is a simplified check and should be replaced with a proper robots.txt parser
        return "Disallow: " + urlparse(url).path not in robots_txt

    def is_valid_url(self, url):
        try:
            result = urlparse(url)
            return (
                all([result.scheme, result.netloc])
                and result.netloc == urlparse(self.base_url).netloc
            )
        except ValueError:
            return False

    def save_to_disk(self, url, content):
        parsed_url = urlparse(url)
        path = parsed_url.path
        if not path or path.endswith("/"):
            path += "index.html"

        file_path = os.path.join(self.base_path, parsed_url.netloc, path.lstrip("/"))

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Saved: {file_path}")

    def rate_limit_request(self):
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last_request)
        self.last_request_time = time.time()

    async def scrape(self, page):
        while self.queue and len(self.visited) < self.max_urls:
            url, depth = self.queue.popleft()

            if depth > self.max_depth or url in self.visited:
                continue

            logger.info(f"Scraping: {url} (Depth: {depth})")
            self.rate_limit_request()

            try:
                await page.goto(url, wait_until="networkidle")
                self.visited.add(url)

                content = await page.content()
                self.save_to_disk(url, content)

                if depth < self.max_depth:
                    new_urls = set(re.findall(r'href=[\'"]?([^\'" >]+)', content))
                    for new_url in new_urls:
                        full_url = urljoin(self.base_url, new_url)
                        if (
                            self.is_valid_url(full_url)
                            and full_url not in self.visited
                            and full_url not in self.all_urls
                        ):
                            self.all_urls.add(full_url)
                            self.queue.append((full_url, depth + 1))

            except Exception as e:
                logger.error(f"Error scraping {url}: {str(e)}")

    async def run(self):
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)
            page = await browser.new_page()

            await self.scrape(page)

            await browser.close()


def main():
    base_url = "https://www.espn.com"  # Replace with your target website
    base_path = "scraped_data"  # Replace with your desired save location

    scraper = WebScraper(base_url, base_path, max_depth=3, max_urls=100, rate_limit=1)

    asyncio.run(scraper.run())


if __name__ == "__main__":
    main()
