# File: backend/services/ocr_service.py
import pytesseract
from PIL import Image
import io
import fitz  # PyMuPDF

class OCRService:
    """
    Service to extract text from various file types (images, PDFs).
    """
    def extract_text_from_bytes(self, file_bytes: bytes, mime_type: str) -> str:
        """
        Extracts text from a file's byte content based on its MIME type.
        """
        try:
            if "pdf" in mime_type:
                return self._extract_text_from_pdf(file_bytes)
            elif "image" in mime_type:
                return self._extract_text_from_image(file_bytes)
            else:
                # For plain text files, just decode
                return file_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Error during text extraction for mime type {mime_type}: {e}")
            return ""

    def _extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Performs OCR on image bytes.
        """
        image = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(image)

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        Extracts text from each page of a PDF and combines it.
        """
        text = ""
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
        return text

ocr_service = OCRService()
