import os
import uuid
from pathlib import Path

import fitz
import pytesseract
from PIL import Image
from fastapi import HTTPException, UploadFile

from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff"}

pytesseract.pytesseract.tesseract_cmd = r"D:\Tesseract_ocrs\tesseract.exe"

class DocumentProcessor:
    """
    Handles:
    - File saving
    - Text extraction from native PDFs
    - OCR fallback for scanned PDFs and images
    - Hindi + English mixed document support
    """
    
    def __init__(self):
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        
    async def save_uploads(self, file: UploadFile) -> tuple[str, str, int]:
        """
        Save uploaded file to disk.
        Returns: (file_path, unique_filename, file_size_bytes)
        """
        ext = Path(file.filename).suffix.lower()
        
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported type '{ext}'. Allowed: {ALLOWED_EXTENSIONS}",
            )
            
        content = await file.read()
        file_size = len(content)
        
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size is {settings.MAX_FILE_SIZE_MB} MB.",
            )
        
        unique_filename = f"{uuid.uuid4()}{ext}"
        save_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
        
        with open(save_path,"wb") as f:
            f.write(content)
            
        return save_path, unique_filename, file_size
    
    def extract_text(self, file_path: str) -> dict:
        """
        Extract text from PDF or image file.
        Returns:
        {
            "text": str,
            "method": "native" | "ocr" | "mixed",
            "page_count": int,
        }
        """
        ext = Path(file_path).suffix.lower()
        
        if ext == ".pdf":
            return self._extract_pdf(file_path)
        else:
            return self._extract_image(file_path)

    def _extract_pdf(self, file_path: str) -> dict:
        """
        Page-by-page extraction.
        Native text if available, OCR if page is scanned.
        """  
        
        doc = fitz.open(file_path)
        pages_text = []
        methods_used = set()
        
        for page_num, page in enumerate(doc):
            native_text = page.get_text("text").strip()
            
            if native_text and len(native_text) > 30:
                pages_text.append(native_text)
                methods_used.add("native")   
            else:
                # Scanned page — render at 300dpi and OCR
                pixel = page.get_pixmap(dpi=300)
                img = Image.frombytes(
                    "RGB",
                    [pixel.width, pixel.height],
                    pixel.samples,
                )
                ocr_text = pytesseract.image_to_string(
                    img,
                    lang="hin+eng",
                    config="--psm 6",
                )
                pages_text.append(ocr_text)
                methods_used.add("ocr")
        
        if methods_used == {"native"}:
            method = "native"
        elif methods_used == {"ocr"}:
            method = "ocr"
        else:
            method = "mixed"
        
        return {
            "text": "\n\n".join(pages_text),
            "method": method,
            "page_count": len(doc),
        }
    
    def _extract_image(self, file_path: str) -> dict:
        """OCR for Image (single image)"""
        img = Image.open(file_path)
        
        #upscaling image
        width, height = img.size
        if width < 1000:
            scale = 1000 / width
            img = img.resize((int(width*scale), int(height*scale)), Image.LANCZOS)
            
        text = pytesseract.image_to_string(
            img,
            lang="hin+eng",
            config="--psm 6",
        )
        
        return {
            "text": text,
            "method": "ocr",
            "page_count": 1,
        }
        
    def detect_language(self, text: str) -> str:
        """
        Detect primary language from Devanagari character ratio.
        Returns: 'hi' | 'en' | 'mixed'
        """
        if not text:
            return "en"
        
        total = len(text.replace(" ", ""))
        if total == 0:
            return "en"
        
        devanagari = sum(1 for c in text if "\u0900" <= c <= "\u097F")
        ratio = devanagari / total
        
        if ratio > 0.4:
            return "hi"
        elif ratio > 0.1:
            return "mixed"
        return "en"
    
document_processor = DocumentProcessor()