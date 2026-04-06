import fitz
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class OCR:

    @classmethod
    def extract_text_from_image_region(cls, page: fitz.Page, bbox: tuple[float, float, float, float], lang: str = 'rus+eng+ron') -> str:
        """
        Вырезает область страницы по bbox и распознает на ней текст с помощью Tesseract.
        """
        # 1. Создаем объект Rect из ваших координат
        rect = fitz.Rect(bbox)
        
        # 2. Рендерим только нужный кусок страницы (clip=rect)
        # Увеличиваем разрешение (matrix) для лучшего качества OCR
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=rect)
        
        # 3. Конвертируем PyMuPDF Pixmap в формат PIL Image
        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
        
        # 4. Распознаем текст
        # P.S. Убедитесь, что у вас установлены языковые пакеты для Tesseract (например, русский)
        recognized_text = pytesseract.image_to_string(img, lang=lang)
        
        return recognized_text.strip()
    
