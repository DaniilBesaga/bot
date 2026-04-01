import fitz

class PdfLoader:
    @staticmethod
    def open_pdf(path: str) -> fitz.Document:
        return fitz.open(path)

    @staticmethod
    def iter_pages(pdf: fitz.Document):
        for i in range(len(pdf)):
            yield i, pdf[i]

    @staticmethod
    def get_page_size(page: fitz.Page) -> tuple[float, float]:
        rect = page.rect
        return (rect.width, rect.height)

    @staticmethod
    def render_page_to_image(page: fitz.Page) -> fitz.Pixmap:
        return page.get_pixmap(dpi=300)