import os, psutil, asyncio, json
import requests
from xml.etree import ElementTree
from typing import List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

site = "https://ai-dinar-makeup-official-website.vercel.app" 

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
    os.makedirs("knowledge", exist_ok=True)

    # Membuat satu file knowledge untuk semua hasil
    knowledge_file = os.path.join("knowledge", "dinar_makeup_LLM_Knowladge.txt")
    
    try:
        with open(knowledge_file, "w", encoding="utf-8") as combined_f:
            for i in range(0, len(urls), max_concurrent):
                batch = urls[i: i+max_concurrent]
                tasks = [crawler.arun(url=u, config=crawl_cfg, session_id=f"session_{i+j}") for j,u in enumerate(batch)]
                log_memory(f"Before batch {i//max_concurrent+1}: ")
                results = await asyncio.gather(*tasks, return_exceptions=True)
                log_memory(f"After batch {i//max_concurrent+1}: ")

                for url, res in zip(batch, results):
                    if isinstance(res, Exception) or not res.success:
                        print(f"❌ Failed: {url} – {getattr(res,'error_message',res)}")
                    else:
                        print(f"✅ Success: {url}")

                        # Menulis pemisah antara halaman
                        combined_f.write("\n===========================================================================================================================================")
                        combined_f.write("\n===========================================================================================================================================\n")
                        combined_f.write("===========================================================================================================================================")

                        # Menulis metadata
                        meta = {
                            "url": res.url,
                            "status": res.status_code,
                            "links": res.links,
                            "media": res.media,
                        }
                        combined_f.write("\n\n==================================================================== Meta JSON Halaman \n\n")
                        combined_f.write(json.dumps(meta, indent=2))
                        
                        # Menulis konten markdown
                        md = res.markdown if isinstance(res.markdown, str) else res.markdown.raw_markdown
                        combined_f.write("\n\n==================================================================== Content Halaman \n\n")
                        combined_f.write(md)

                        # combined_f.write("\n\n==================================================================== HTML Halaman \n\n")
                        # # combined_f.write(res.cleaned_html)
                        # combined_f.write(res.html)

    finally:
        print("Closing crawler...")
        await crawler.close()
        log_memory("Final: ")
        print(f"Peak mem usage: {peak_memory//(1024*1024)} MB")
        print(f"All results have been combined into: {knowledge_file}")

def get_pydantic_ai_docs_urls():
    sitemap_url = site + "/sitemap.xml"
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