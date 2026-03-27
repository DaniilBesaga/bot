import re

def clean_text(text: str) -> str:
    text = text.replace("\r", "\n")
    # replace 3 or more consecutive newline characters with 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # replace 2 or more consecutive whitespace characters with a single space
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()