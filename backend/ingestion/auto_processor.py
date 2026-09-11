import threading
import time
from pathlib import Path
from uuid import uuid4

from database.metadata import (
    save_document_metadata,
    update_document_metadata,
)

from database.vector_store import add_document

from ingestion.provenance import create_provenance
from ingestion.scanner import scan_document
from ingestion.text_extractor import extract_text

from ml.training.auto_trainer import (
    auto_retrain,
    should_retrain,
)


# ---------------------------------------------------------
# Folders
# ---------------------------------------------------------

INBOX_FOLDER = Path("data/inbox")
DOCUMENT_FOLDER = Path("data/documents")
QUARANTINE_FOLDER = Path("data/quarantine")


# ---------------------------------------------------------
# Supported files and tenants
# ---------------------------------------------------------

SUPPORTED_EXTENSIONS = {".txt", ".pdf"}

VALID_TENANTS = {
    "tenant_a",
    "tenant_b",
    "tenant_c",
}


# ---------------------------------------------------------
# Processor state
# ---------------------------------------------------------

PROCESSOR_STARTED = False
PROCESSOR_LOCK = threading.Lock()

# Files currently being processed
PROCESSING_FILES = set()

# Prevent the same file from being processed again
PROCESSED_FILES = set()

FILE_LOCK = threading.Lock()


# ---------------------------------------------------------
# Check whether a file is ready
# ---------------------------------------------------------

def is_file_ready(file_path: Path):
    """
    Make sure the file has finished being written.

    The file must:
    1. Exist
    2. Not be empty
    3. Have the same size during two checks
    """

    if not file_path.exists():
        return False

    try:
        first_size = file_path.stat().st_size

        if first_size == 0:
            return False

        # Wait briefly before checking again
        time.sleep(1)

        if not file_path.exists():
            return False

        second_size = file_path.stat().st_size

        if first_size != second_size:
            return False

        return True

    except OSError:
        return False


# ---------------------------------------------------------
# Process one document
# ---------------------------------------------------------

def process_file(
    file_path: Path,
    tenant_id: str
):
    """
    Process one file through Layer 1.

    File
      ↓
    Wait until completely written
      ↓
    Extract text
      ↓
    Security scanner
      ↓
    APPROVED → ChromaDB
    QUARANTINED → quarantine folder
    """

    # -----------------------------------------------------
    # Check extension
    # -----------------------------------------------------

    if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:

        print(
            f"[RAGShield] Skipping unsupported file: "
            f"{file_path.name}"
        )

        return

    # -----------------------------------------------------
    # Prevent duplicate processing
    # -----------------------------------------------------

    file_key = str(
        file_path.resolve()
    )

    with FILE_LOCK:

        if file_key in PROCESSED_FILES:
            return

        if file_key in PROCESSING_FILES:
            return

        PROCESSING_FILES.add(
            file_key
        )

    try:

        # -------------------------------------------------
        # Wait until file is completely written
        # -------------------------------------------------

        if not is_file_ready(file_path):
            return

        # -------------------------------------------------
        # Read file
        # -------------------------------------------------

        file_bytes = file_path.read_bytes()

        if not file_bytes:
            return

        # -------------------------------------------------
        # Generate document ID
        # -------------------------------------------------

        document_id = str(
            uuid4()
        )

        # -------------------------------------------------
        # Extract text
        # -------------------------------------------------

        text = extract_text(
            file_path.name,
            file_bytes
        )

        # -------------------------------------------------
        # Create provenance
        # -------------------------------------------------

        metadata = create_provenance(
            document_id=document_id,
            filename=file_path.name,
            tenant_id=tenant_id,
            file_bytes=file_bytes,
        )

        # -------------------------------------------------
        # Store original document
        # -------------------------------------------------

        DOCUMENT_FOLDER.mkdir(
            parents=True,
            exist_ok=True
        )

        stored_filename = (
            f"{document_id}_{file_path.name}"
        )

        stored_path = (
            DOCUMENT_FOLDER /
            stored_filename
        )

        stored_path.write_bytes(
            file_bytes
        )

        metadata["stored_filename"] = (
            stored_filename
        )

        metadata["text_length"] = len(text)

        save_document_metadata(
            metadata
        )

        # -------------------------------------------------
        # LAYER 1 — INGESTION SECURITY
        # -------------------------------------------------

        print(
            f"[RAGShield] Scanning: "
            f"{file_path.name}"
        )

        scan_result = scan_document(
            text
        )

        # -------------------------------------------------
        # Save scan result
        # -------------------------------------------------

        update_document_metadata(
            document_id,
            {
                "risk_score":
                    scan_result["risk_score"],

                "detected_signals":
                    scan_result["detected_signals"],

                "status":
                    scan_result["status"],

                "ml_prediction":
                    scan_result["ml_prediction"],

                "ml_malicious_probability":
                    scan_result[
                        "ml_malicious_probability"
                    ],
            },
        )

        # -------------------------------------------------
        # MALICIOUS → QUARANTINE
        # -------------------------------------------------

        if scan_result["status"] == "QUARANTINED":

            QUARANTINE_FOLDER.mkdir(
                parents=True,
                exist_ok=True
            )

            quarantine_path = (
                QUARANTINE_FOLDER /
                stored_filename
            )

            stored_path.replace(
                quarantine_path
            )

            print(
                f"[RAGShield] QUARANTINED: "
                f"{file_path.name}"
            )

        # -------------------------------------------------
        # SAFE → VECTOR DATABASE
        # -------------------------------------------------

        else:

            vector_result = add_document(
                document_id=document_id,
                tenant_id=tenant_id,
                filename=file_path.name,
                text=text,
            )

            print(
                f"[RAGShield] APPROVED: "
                f"{file_path.name}"
            )

            print(
                f"[RAGShield] Vector store: "
                f"{vector_result}"
            )

        # -------------------------------------------------
        # Mark as successfully processed
        # -------------------------------------------------

        with FILE_LOCK:

            PROCESSED_FILES.add(
                file_key
            )

        # -------------------------------------------------
        # Remove from inbox
        # -------------------------------------------------

        file_path.unlink(
            missing_ok=True
        )

    except Exception as error:

        print(
            f"[RAGShield] Failed to process "
            f"{file_path.name}: {error}"
        )

    finally:

        with FILE_LOCK:

            PROCESSING_FILES.discard(
                file_key
            )


# ---------------------------------------------------------
# Automatic ML retraining
# ---------------------------------------------------------

def check_auto_retraining():

    try:

        # Check whether enough trusted samples exist
        if not should_retrain():
            return

        print()
        print(
            "[RAGShield ML] "
            "Retraining threshold reached."
        )

        # Start controlled retraining
        result = auto_retrain()

        print(
            "[RAGShield ML] "
            f"Auto-training result: {result}"
        )

    except Exception as error:

        print(
            "[RAGShield ML] "
            f"Automatic retraining failed: {error}"
        )


# ---------------------------------------------------------
# Scan inbox once
# ---------------------------------------------------------

def scan_inbox_once():

    INBOX_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    for tenant_id in sorted(
        VALID_TENANTS
    ):

        tenant_folder = (
            INBOX_FOLDER /
            tenant_id
        )

        tenant_folder.mkdir(
            parents=True,
            exist_ok=True
        )

        for file_path in sorted(
            tenant_folder.iterdir()
        ):

            if file_path.is_file():

                process_file(
                    file_path,
                    tenant_id
                )

    # -----------------------------------------------------
    # Check ML auto-training after processing documents
    # -----------------------------------------------------

    check_auto_retraining()


# ---------------------------------------------------------
# Background watcher
# ---------------------------------------------------------

def watcher_loop():

    print(
        "[RAGShield] Automatic document "
        "processor started."
    )

    while True:

        try:

            scan_inbox_once()

        except Exception as error:

            print(
                f"[RAGShield] Auto processor error: "
                f"{error}"
            )

        # Check every 3 seconds
        time.sleep(3)


# ---------------------------------------------------------
# Start processor
# ---------------------------------------------------------

def start_auto_processor():

    global PROCESSOR_STARTED

    with PROCESSOR_LOCK:

        if PROCESSOR_STARTED:
            return

        processor_thread = threading.Thread(
            target=watcher_loop,
            daemon=True,
            name="ragshield-document-processor",
        )

        processor_thread.start()

        PROCESSOR_STARTED = True