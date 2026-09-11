def chunk_text(text, chunk_size=500, overlap=50):
    """
    Split document text into overlapping chunks.

    chunk_size = approximate number of characters per chunk
    overlap = number of characters repeated between chunks
    """

    if not text:
        return []

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - overlap

    return chunks