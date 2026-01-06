import requests
import trafilatura


def extract_from_url(url: str) -> tuple[str, str]:
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        raise ValueError(f"Failed to fetch url: {resp.status_code}")
    downloaded = trafilatura.fetch_url(url)
    text = trafilatura.extract(downloaded) if downloaded else None
    if not text:
        text = resp.text
    return text, resp.text
