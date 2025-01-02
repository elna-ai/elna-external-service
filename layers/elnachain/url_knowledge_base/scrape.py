from langchain_community.document_loaders import AsyncChromiumLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import re
import requests


class Scraper:
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
        ]

    def validate_link(self, link):
        status_codes = []  # Collect status codes for each failed user agent
        for user_agent in self.user_agents:
            try:
                response = requests.get(
                    link, headers={"User-Agent": user_agent}, timeout=10)
                if response.status_code == 200:
                    return user_agent, None
                status_codes.append(response.status_code)
            except requests.RequestException as e:
                print(e)
        return None, status_codes[0]

    def __call__(self, links):
        failed_links = []
        all_texts = []

        for link in links:
            try:
                user_agent, error = self.validate_link(link)
                if error:
                    failed_links.append({"url": link, "error": error})
                    continue

                loader = AsyncChromiumLoader([link], user_agent=user_agent)
                html = loader.load()

                html2text = Html2TextTransformer()
                docs_transformed = html2text.transform_documents(html)

                text = "\n".join(doc.page_content for doc in docs_transformed)
                text = re.sub(r'\s+', ' ', text).strip()

                error_patterns = [
                    r"net::ERR_\w+",
                    r"Error:\s.*",
                ]
                error_found = next((re.search(pattern, text).group(
                    0) for pattern in error_patterns if re.search(pattern, text)), None)

                if error_found:
                    failed_links.append({"url": link, "error": error_found})
                    continue

                # Split the text into chunks
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=20,
                    length_function=len,
                    is_separator_regex=False
                )
                texts = text_splitter.split_text(text)
                all_texts.extend(texts)

            except Exception as e:
                failed_links.append({"url": link, "error": str(e)})

        return all_texts, failed_links


# # Example usage
# links = [
#     'https://www.amazon.com/s?k=gaming+headsets&_encoding=UTF8'
# ]

# scraper = Scraper()
# texts, errors = scraper(links)

# print("Texts:", texts)
# print("Errors:", errors)
