import html2text
import requests
from typing import List, Dict, Tuple
import re


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

    def validate_link(self, link: str) -> Tuple[str, int]:
        """
        Try different user agents until a successful connection is made.
        """
        status_codes = []
        for user_agent in self.user_agents:
            try:
                response = requests.get(
                    link, headers={"User-Agent": user_agent}, timeout=10
                )
                if response.status_code == 200:
                    return response.text, None
                status_codes.append(response.status_code)
            except requests.RequestException as e:
                print(f"Error with user agent {user_agent}: {e}")
        return None, status_codes[0] if status_codes else 500

    def __call__(self, links: List[str]) -> Tuple[List[Dict], List[Dict]]:
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

                text = self.html_converter.handle(html_content)

                error_patterns = [
                    r"net::ERR_\w+",
                    r"Error:\s.*",
                    r"404 Not Found",
                    r"403 Forbidden",
                ]
                error_found = next(
                    (
                        re.search(pattern, text).group(0)
                        for pattern in error_patterns
                        if re.search(pattern, text)
                    ),
                    None,
                )

                if error_found:
                    failed_links.append({"url": link, "error": error_found})
                    continue

                corrected_text = text.encode("latin1").decode("utf-8")

                # texts = self.split_text(text)
                all_texts.append({"url": link, "content": corrected_text})
                # all_texts.extend(texts)

            except Exception as e:
                failed_links.append({"url": link, "error": str(e)})

        return all_texts, failed_links


# # Example usage
if __name__ == "__main__":
    #     text = "Boundary nodes\n  * Internet Identity\n\n\n\n### Smart Contracts serve the web\n\nThe Internet Computer is the only blockchain that can host a entire dapp â\x80\x93 frontend, backend and data."
    #     corrected_text = text.encode("latin1").decode("utf-8")
    #     print(corrected_text)

    links = ["https://internetcomputer.org/how-it-works"]

    scraper = Scraper()
    texts, errors = scraper(links)
    print("Texts:", texts)
    print("Errors:", errors)
