import re
from typing import List


def clean_text(text: str) -> str:
    """Clean and normalize extracted text."""
    text = re.sub(r"[\*\[\]#\(\)\{\}]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[^\w\s.,!?-]", "", text)
    text = re.sub(r"\n\s*\n", "\n", text)
    return text


def split_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks of approximately equal size.
    """
    text = " ".join(text.split())

    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            chunks.append(text[start:])
            break

        last_period = text.rfind(".", start, end)
        last_space = text.rfind(" ", start, end)

        break_point = last_period if last_period != -1 else last_space

        if break_point == -1:
            break_point = end

        chunks.append(text[start : break_point + 1])
        start = break_point + 1 - overlap

    return chunks
