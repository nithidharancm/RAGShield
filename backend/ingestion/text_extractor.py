from pathlib import Path
from pypdf import PdfReader


def extract_text(filename, file_bytes):
    """Extract text from TXT or PDF files."""

    extension = Path(filename).suffix.lower()

    # TXT file
    if extension == ".txt":
        return file_bytes.decode("utf-8", errors="replace")

    # PDF file
    if extension == ".pdf":
        # pypdf needs a file-like object
        import io

        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)

        text = ""

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

        return text

    # We only support TXT and PDF for now
    raise ValueError("Only TXT and PDF files are supported.")