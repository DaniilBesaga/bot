from app.services.extraction.pdf_extractor import PdfExtractor
# from app.services.extraction.docx_extractor import DocxExtractor
# from app.services.extraction.txt_extractor import TxtExtractor


class ExtractorFactory:
    @staticmethod
    def get_extractor(file_path: str):
        lower = file_path.lower()

        if lower.endswith(".pdf"):
            return PdfExtractor()
        if lower.endswith(".docx"):
            # return DocxExtractor()
            pass
        if lower.endswith(".txt"):
            # return TxtExtractor()
            pass

        raise ValueError(f"Unsupported file type: {file_path}")