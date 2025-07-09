import os, sys, psutil, asyncio, json
import requests
from xml.etree import ElementTree
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def crawl_parallel(urls: List[str], max_concurrent: int = 3):
    process = psutil.Process(os.getpid())
    peak_memory = 0
    def log_memory(prefix=""):
        nonlocal peak_memory
        mem = process.memory_info().rss
        peak_memory = max(peak_memory, mem)
        print(f"{prefix} Memory: {mem//(1024*1024)} MB (Peak {peak_memory//(1024*1024)} MB)")

    browser_cfg = BrowserConfig(headless=True, verbose=False, extra_args=["--disable-gpu","--no-sandbox"])
    crawl_cfg = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)

    crawler = AsyncWebCrawler(config=browser_cfg)
    await crawler.start()
    os.makedirs("output", exist_ok=True)

    try:
        for i in range(0, len(urls), max_concurrent):
            batch = urls[i: i+max_concurrent]
            tasks = [crawler.arun(url=u, config=crawl_cfg, session_id=f"session_{i+j}") for j,u in enumerate(batch)]
            log_memory(f"Before batch {i//max_concurrent+1}: ")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            log_memory(f"After batch {i//max_concurrent+1}: ")

            for url, res in zip(batch, results):
                safe_name = url.replace("://","_").replace("/","_")
                if isinstance(res, Exception) or not res.success:
                    print(f"❌ Failed: {url} – {getattr(res,'error_message',res)}")
                else:
                    print(f"✅ Success: {url}")
                    with open(os.path.join("output", f"{safe_name}.html"), "w", encoding="utf-8") as f:
                        f.write(res.html)
                    if res.cleaned_html:
                        with open(os.path.join("output", f"{safe_name}_clean.html"), "w", encoding="utf-8") as f:
                            f.write(res.cleaned_html)
                    if res.markdown:
                        md = res.markdown if isinstance(res.markdown, str) else res.markdown.raw_markdown
                        with open(os.path.join("output", f"{safe_name}.md"), "w", encoding="utf-8") as f:
                            f.write(md)
                    with open(os.path.join("output", f"{safe_name}_meta.json"), "w", encoding="utf-8") as f:
                        meta = {
                            "url": res.url,
                            "status": res.status_code,
                            "links": res.links,
                            "media": res.media,
                        }
                        f.write(json.dumps(meta, indent=2))

    finally:
        print("Closing crawler...")
        await crawler.close()
        log_memory("Final: ")
        print(f"Peak mem usage: {peak_memory//(1024*1024)} MB")

def get_pydantic_ai_docs_urls():
    sitemap_url = "https://ai-dinar-makeup-official-website.vercel.app/sitemap.xml"
    try:
        resp = requests.get(sitemap_url)
        resp.raise_for_status()
        root = ElementTree.fromstring(resp.content)
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        return [loc.text for loc in root.findall('.//ns:loc', ns)]
    except Exception as e:
        print("Error fetching sitemap:", e)
        return []

async def main():
    urls = get_pydantic_ai_docs_urls()
    print(f"Found {len(urls)} URLs") if urls else print("No URLs")
    await crawl_parallel(urls, max_concurrent=10)

if __name__ == "__main__":
    asyncio.run(main())
