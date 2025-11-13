import os
import uuid
import base64
import mimetypes
from pathlib import Path
from typing import Tuple
from io import BytesIO

def process_uploaded_file(uploaded_file) -> Tuple[str, str, str, str, str]:
    """
    Save the uploaded file to disk, extract its text (where possible),
    and return:
      (extracted_text, saved_file_path, extension, base64_string, file_kind)

    file_kind is: "image" if image type; otherwise "file".
    """
    original_name = uploaded_file.name
    ext = original_name.lower().rsplit(".", 1)[-1] if "." in original_name else ""
    UPLOAD_ROOT = Path("static") / f"uploads/{ext}"
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    file_path = UPLOAD_ROOT / safe_name

    # Write bytes to disk
    with open(file_path, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    # Read bytes back for base64 encoding
    file_bytes = file_path.read_bytes()
    base64_string = base64.b64encode(file_bytes).decode("utf-8")

    # Determine MIME type
    mime_type, encoding = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    # Decide file_kind
    if mime_type.startswith("image/"):
        file_kind = "image"
    else:
        file_kind = "file"

    # Extract text depending on file type
    try:
        if ext == "txt":
            content = file_path.read_text(encoding="utf-8", errors="ignore")

        elif ext == "pdf":
            from PyPDF2 import PdfReader
            reader = PdfReader(BytesIO(file_bytes))
            content = "\n".join(page.extract_text() or "" for page in reader.pages)

        elif ext == "docx":
            from docx import Document
            doc = Document(BytesIO(file_bytes))
            content = "\n".join(p.text for p in doc.paragraphs)

        # elif file_kind == "image":
        #     # Use OCR for image text extraction (optional)
        #     from PIL import Image
        #     import pytesseract
        #     img = Image.open(BytesIO(file_bytes))
        #     content = pytesseract.image_to_string(img)

        else:
            # For other files where text extraction not implemented
            content = ""

        return content, str(file_path), ext, base64_string, file_kind

    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise ValueError(f"Error processing file {original_name}: {str(e)}")
