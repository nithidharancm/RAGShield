import hashlib
from datetime import datetime, timezone


def calculate_sha256(file_bytes):
    """Calculate the SHA-256 hash of a file."""

    return hashlib.sha256(file_bytes).hexdigest()


def create_provenance(document_id, filename, tenant_id, file_bytes):
    """Create basic provenance information for a document."""

    return {
        "document_id": document_id,
        "filename": filename,
        "tenant_id": tenant_id,
        "sha256": calculate_sha256(file_bytes),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "status": "PENDING_SCAN"
    }