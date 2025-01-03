import html2text
import requests
import re
from typing import List, Dict, Tuple


class Scraper:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
        ]
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = True
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = True
        self.html_converter.ignore_tables = False
        self.html_converter.body_width = 0  # Don't wrap text

    def split_text(self, text: str, chunk_size: int = 1000, overlap: int = 20) -> List[str]:
        """
        Split text into overlapping chunks of approximately equal size.
        """
        text = ' '.join(text.split())

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            if end >= len(text):
                chunks.append(text[start:])
                break

            last_period = text.rfind('.', start, end)
            last_space = text.rfind(' ', start, end)

            break_point = last_period if last_period != -1 else last_space

            if break_point == -1:
                break_point = end

            chunks.append(text[start:break_point + 1])
            start = break_point + 1 - overlap

        return chunks

    def validate_link(self, link: str) -> Tuple[str, int]:
        """
        Try different user agents until a successful connection is made.
        """
        status_codes = []
        for user_agent in self.user_agents:
            try:
                response = requests.get(
                    link,
                    headers={"User-Agent": user_agent},
                    timeout=10
                )
                if response.status_code == 200:
                    return response.text, None
                status_codes.append(response.status_code)
            except requests.RequestException as e:
                print(f"Error with user agent {user_agent}: {e}")
        return None, status_codes[0] if status_codes else 500

    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        text = re.sub(r'[\*\[\]#\(\)\{\}]+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        return text

    def extract_text_from_html(self, html_content: str) -> str:
        """Extract meaningful text from HTML content using html2text."""
        text = self.html_converter.handle(html_content)
        return self.clean_text(text)

    def __call__(self, links: List[str]) -> Tuple[List[str], List[Dict]]:
        """
        Process a list of links and return extracted texts and any errors.
        """
        failed_links = []
        all_texts = []

        for link in links:
            try:
                html_content, error = self.validate_link(link)
                if error:
                    failed_links.append({"url": link, "error": error})
                    continue

                text = self.extract_text_from_html(html_content)

                error_patterns = [
                    r"net::ERR_\w+",
                    r"Error:\s.*",
                    r"404 Not Found",
                    r"403 Forbidden"
                ]
                error_found = next((
                    re.search(pattern, text).group(0)
                    for pattern in error_patterns
                    if re.search(pattern, text)
                ), None)

                if error_found:
                    failed_links.append({"url": link, "error": error_found})
                    continue

                texts = self.split_text(text)
                all_texts.extend(texts)

            except Exception as e:
                failed_links.append({"url": link, "error": str(e)})

        return all_texts, failed_links


# # Example usage
# if __name__ == "__main__":
#     links = [
#         'https://www.amazon.com/s?k=gaming+headsets&_encoding=UTF8',
#         'https://www.flipkart.com/womens-footwear/~sports-casual-shoes/pr?sid=osp%2Ciko&p%5B%5D=facets.discount_range_v1%255B%255D%3D60%2525%2Bor%2Bmore&param=292&p%5B%5D=facets.price_range.from%3DMin&p%5B%5D=facets.price_range.to%3D499&param=123&hpid=Q2_sZmamWCSq-8i_9XUI76p7_Hsxr70nj65vMAAFKlc%3D&ctx=eyJjYXJkQ29udGV4dCI6eyJhdHRyaWJ1dGVzIjp7InZhbHVlQ2FsbG91dCI6eyJtdWx0aVZhbHVlZEF0dHJpYnV0ZSI6eyJrZXkiOiJ2YWx1ZUNhbGxvdXQiLCJpbmZlcmVuY2VUeXBlIjoiVkFMVUVfQ0FMTE9VVCIsInZhbHVlcyI6WyJNaW4gNjAlT2ZmIl0sInZhbHVlVHlwZSI6Ik1VTFRJX1ZBTFVFRCJ9fSwiaGVyb1BpZCI6eyJzaW5nbGVWYWx1ZUF0dHJpYnV0ZSI6eyJrZXkiOiJoZXJvUGlkIiwiaW5mZXJlbmNlVHlwZSI6IlBJRCIsInZhbHVlIjoiU0hPSDZUNEgyWVpDR01TSyIsInZhbHVlVHlwZSI6IlNJTkdMRV9WQUxVRUQifX0sInRpdGxlIjp7Im11bHRpVmFsdWVkQXR0cmlidXRlIjp7ImtleSI6InRpdGxlIiwiaW5mZXJlbmNlVHlwZSI6IlRJVExFIiwidmFsdWVzIjpbIldvbWVuJ3MgU2hvZXMiXSwidmFsdWVUeXBlIjoiTVVMVElfVkFMVUVEIn19fX19'
#     ]

#     scraper = Scraper()
#     texts, errors = scraper(links)

#     print("Texts:", len(texts))
#     print("Errors:", errors)
