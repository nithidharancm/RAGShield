import json
from pathlib import Path


# Location of our simple JSON database
DATABASE_FILE = Path("data/documents_metadata.json")


def load_documents():
    """Load all document metadata from the JSON database."""

    if not DATABASE_FILE.exists():
        return []

    with open(DATABASE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_document_metadata(metadata):
    """Add a new document to the JSON database."""

    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    documents = load_documents()

    documents.append(metadata)

    with open(DATABASE_FILE, "w", encoding="utf-8") as file:
        json.dump(documents, file, indent=4)


def get_document(document_id):
    """Find one document using its ID."""

    documents = load_documents()

    for document in documents:
        if document["document_id"] == document_id:
            return document

    return None


def update_document_metadata(document_id, updates):
    """Update information about an existing document."""

    documents = load_documents()

    for document in documents:
        if document["document_id"] == document_id:
            document.update(updates)

            with open(DATABASE_FILE, "w", encoding="utf-8") as file:
                json.dump(documents, file, indent=4)

            return document

    return None