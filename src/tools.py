import re
from bs4 import BeautifulSoup

def clean_text(text):
    if not text:  # Ensure text is not None or empty
        return ""
    soup = BeautifulSoup(text, "html.parser")
    cleaned_text = soup.get_text(" ")
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

