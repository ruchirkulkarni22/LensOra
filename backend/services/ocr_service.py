# File: backend/services/ocr_service.py
import pytesseract
from PIL import Image, ImageEnhance
import io
import fitz  # PyMuPDF
import docx # python-docx

class OCRService:
    """
    An advanced service to flawlessly extract text from various file types,
    including scanned PDFs, images with pre-processing, and DOCX files.
    """
    def extract_text_from_bytes(self, file_bytes: bytes, mime_type: str) -> str:
        """
        Routes the file content to the correct extraction method based on its MIME type.
        """
        try:
            if "pdf" in mime_type:
                return self._extract_text_from_pdf(file_bytes)
            elif "image" in mime_type:
                return self._extract_text_from_image(file_bytes)
            elif "openxmlformats-officedocument.wordprocessingml.document" in mime_type:
                return self._extract_text_from_docx(file_bytes)
            else:
                # Fallback for plain text files
                return file_bytes.decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Error during text extraction for mime type {mime_type}: {e}")
            return ""

    def _extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Performs OCR on image bytes after applying pre-processing filters to improve accuracy.
        """
        image = Image.open(io.BytesIO(image_bytes))
        
        # 1. Convert to grayscale - this is a standard and highly effective step for OCR.
        image = image.convert('L')
        
        # 2. Increase contrast - makes the text stand out from the background.
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)
        
        print("Pre-processed image for OCR. Now extracting text.")
        # Perform OCR on the cleaned-up image
        return pytesseract.image_to_string(image)

    def _extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        Extracts text from a PDF. It handles both text-based and scanned (image-based) PDFs.
        """
        full_text = ""
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for i, page in enumerate(doc):
                # First, try to get text directly. This is fast and works for non-scanned PDFs.
                text = page.get_text()
                if not text.strip(): # If there's no embedded text, it's likely a scan.
                    print(f"Page {i+1} appears to be a scanned image. Performing OCR.")
                    # Render the page to a high-resolution image
                    pix = page.get_pixmap(dpi=300)
                    img_bytes = pix.tobytes("png")
                    # Use our enhanced image OCR method on the rendered page
                    text = self._extract_text_from_image(img_bytes)
                
                full_text += text + "\n"
        return full_text

    def _extract_text_from_docx(self, docx_bytes: bytes) -> str:
        """
        Extracts text from a .docx file.
        """

        document = docx.Document(io.BytesIO(docx_bytes))
        return "\n".join([para.text for para in document.paragraphs])

ocr_service = OCRService()

