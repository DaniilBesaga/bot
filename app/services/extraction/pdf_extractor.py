import fitz

class PdfExtractor:
    def extract(self, path: str) -> dict:
        doc = fitz.open(path)
        pages = []

        for i, page in enumerate(doc):
            text = page.get_text("text", sort = True)
            pages.append({
                "page": i + 1,
                "text": text
            })

        full_text = "\n\n".join(p["text"] for p in pages)

        return {
            "text": full_text,
            "pages": pages
        }