from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingestion.provenance import create_provenance
from ingestion.text_extractor import extract_text
from ingestion.scanner import scan_document

from database.metadata import (
    save_document_metadata,
    get_document,
    update_document_metadata,
)

from database.vector_store import (
    add_document,
    add_baseline_document,
)
from retrieval.authorization import get_authorized_tenant
from retrieval.search import (
    tenant_scoped_search,
    baseline_search,
)
from retrieval.input_guard import detect_input_threats

from generation.generator import (
    generate_answer,
    generate_baseline_answer,
)
from generation.guard import inspect_output
from ingestion.auto_processor import start_auto_processor


# ---------------------------------------------------------
# Search request model
# ---------------------------------------------------------

class SearchRequest(BaseModel):
    user_id: str
    query: str
    ragshield_enabled: bool = True


# ---------------------------------------------------------
# Create FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="RAGShield",
    description="Three-stage security pipeline for RAG systems",
    version="0.5.0"
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Document storage folders
# ---------------------------------------------------------

DOCUMENT_FOLDER = Path("data/documents")
QUARANTINE_FOLDER = Path("data/quarantine")


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------

# ---------------------------------------------------------
# Automatic Document Processor
# ---------------------------------------------------------

@app.on_event("startup")
def start_ragshield_processor():
    start_auto_processor()


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "project": "RAGShield"
    }


# ---------------------------------------------------------
# Document Upload
# ---------------------------------------------------------

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    tenant_id: str = Form(...),
    ragshield_enabled: bool = Form(True)
):
    """
    Upload a document and record its provenance.

    Documents start as PENDING_SCAN.
    They are NOT trusted yet.
    """

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required."
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in [".txt", ".pdf"]:
        raise HTTPException(
            status_code=400,
            detail="Only TXT and PDF files are supported."
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    document_id = str(uuid4())

    # -----------------------------------------------------
    # Extract text
    # -----------------------------------------------------

    try:
        extracted_text = extract_text(
            file.filename,
            file_bytes
        )

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not extract text: {error}"
        )

    # -----------------------------------------------------
    # Create document folder
    # -----------------------------------------------------

    DOCUMENT_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    # -----------------------------------------------------
    # Save original file
    # -----------------------------------------------------

    stored_filename = f"{document_id}_{file.filename}"

    stored_path = DOCUMENT_FOLDER / stored_filename

    with open(stored_path, "wb") as saved_file:
        saved_file.write(file_bytes)

    # -----------------------------------------------------
    # Create provenance metadata
    # -----------------------------------------------------

    metadata = create_provenance(
        document_id=document_id,
        filename=file.filename,
        tenant_id=tenant_id,
        file_bytes=file_bytes
    )

    metadata["stored_filename"] = stored_filename
    metadata["text_length"] = len(extracted_text)
    metadata["ragshield_enabled"] = ragshield_enabled
    metadata["mode"] = (
        "RAGSHIELD" if ragshield_enabled else "BASELINE"
    )

    # -----------------------------------------------------
    # Baseline comparison copy
    # -----------------------------------------------------
    # Every uploaded document is also indexed into the separate
    # baseline collection. This copy is intentionally untrusted
    # and is used ONLY when RAGShield is OFF.
    #
    # IMPORTANT: indexing here does NOT mean the document passed
    # Layer 1. The protected collection is still populated only
    # after the normal RAGShield scan approves the document.

    try:
        baseline_vector_result = add_baseline_document(
            document_id=document_id,
            tenant_id=tenant_id,
            filename=file.filename,
            text=extracted_text
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Baseline comparison indexing failed: {error}"
        )

    # -----------------------------------------------------
    # RAGShield OFF: bypass Layer 1
    # -----------------------------------------------------
    # The raw document is already available in the isolated
    # baseline collection, so no ingestion security is executed.

    if not ragshield_enabled:

        metadata.update({
            "status": "BASELINE_INDEXED",
            "security_bypassed": True,
            "risk_score": None,
            "detected_signals": [],
            "ml_prediction": "NOT_RUN",
            "ml_malicious_probability": None,
        })

        save_document_metadata(metadata)

        return {
            "document_id": document_id,
            "filename": file.filename,
            "tenant_id": tenant_id,
            "sha256": metadata["sha256"],
            "status": "BASELINE_INDEXED",
            "ragshield_enabled": False,
            "mode": "BASELINE",
            "security_bypassed": True,
            "risk_score": None,
            "ml_prediction": "NOT_RUN",
            "ml_malicious_probability": None,
            "detected_signals": [],
            "vector_store": baseline_vector_result,
            "layer_trace": {
                "layer_1": "BYPASSED",
                "layer_2": "NOT_RUN",
                "layer_3": "NOT_RUN",
            },
            "message": (
                "RAGShield is OFF. The document bypassed "
                "ingestion security and was added to the "
                "baseline comparison collection."
            )
        }

    # -----------------------------------------------------
    # RAGShield ON: keep the original secure upload flow
    # -----------------------------------------------------
    # A baseline comparison copy already exists, but the secure
    # copy still starts as PENDING_SCAN and must pass Layer 1
    # before it can enter the protected vector collection.

    metadata["security_bypassed"] = False

    save_document_metadata(metadata)

    return {
        "document_id": document_id,
        "filename": file.filename,
        "tenant_id": tenant_id,
        "sha256": metadata["sha256"],
        "status": metadata["status"],
        "ragshield_enabled": True,
        "mode": "RAGSHIELD",
        "security_bypassed": False,
        "layer_trace": {
            "layer_1": "PENDING_SCAN",
            "layer_2": "NOT_RUN",
            "layer_3": "NOT_RUN",
        }
    }


# ---------------------------------------------------------
# Stage 1: Ingestion Security Scan
# ---------------------------------------------------------

@app.post("/documents/{document_id}/scan")
def scan_uploaded_document(document_id: str):
    """
    Run the Stage 1 security scanner.

    The scanner combines:
    - Rule-based detection
    - ML poisoning detection
    - Corpus anomaly detection

    Only APPROVED documents are allowed into ChromaDB.
    QUARANTINED documents are moved to the quarantine folder.
    """

    # -----------------------------------------------------
    # STEP 1: Find document metadata
    # -----------------------------------------------------

    document = get_document(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    # -----------------------------------------------------
    # Baseline documents deliberately bypass Layer 1
    # -----------------------------------------------------

    if document.get("ragshield_enabled", True) is False:
        return {
            "document_id": document_id,
            "status": document.get(
                "status",
                "BASELINE_INDEXED"
            ),
            "ragshield_enabled": False,
            "mode": "BASELINE",
            "security_bypassed": True,
            "risk_score": None,
            "ml_prediction": "NOT_RUN",
            "ml_malicious_probability": None,
            "detected_signals": [],
            "layer_trace": {
                "layer_1": "BYPASSED",
                "layer_2": "NOT_RUN",
                "layer_3": "NOT_RUN",
            },
            "message": (
                "RAGShield is OFF. Layer 1 was bypassed; "
                "the document is already available in the "
                "separate baseline vector collection."
            )
        }

    # -----------------------------------------------------
    # STEP 2: Only scan PENDING_SCAN documents
    # -----------------------------------------------------

    if document["status"] != "PENDING_SCAN":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Document cannot be scanned because its "
                f"current status is {document['status']}."
            )
        )

    # -----------------------------------------------------
    # STEP 3: Find original file
    # -----------------------------------------------------

    stored_filename = document["stored_filename"]

    stored_path = DOCUMENT_FOLDER / stored_filename

    if not stored_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Original document file not found."
        )

    # -----------------------------------------------------
    # STEP 4: Read original file
    # -----------------------------------------------------

    try:
        with open(stored_path, "rb") as file:
            file_bytes = file.read()

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read document: {error}"
        )

    # -----------------------------------------------------
    # STEP 5: Extract text
    # -----------------------------------------------------

    try:
        text = extract_text(
            document["filename"],
            file_bytes
        )

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not extract text: {error}"
        )

    # -----------------------------------------------------
    # STEP 6: Run RAGShield security scanner
    # -----------------------------------------------------

    try:
        scan_result = scan_document(text)

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Security scan failed: {error}"
        )

    # -----------------------------------------------------
    # STEP 7: Save complete scan results
    # -----------------------------------------------------

    update_document_metadata(
        document_id,
        {
            "risk_score": scan_result["risk_score"],
            "detected_signals": scan_result[
                "detected_signals"
            ],
            "status": scan_result["status"],
            "ml_prediction": scan_result[
                "ml_prediction"
            ],
            "ml_malicious_probability": scan_result[
                "ml_malicious_probability"
            ]
        }
    )

    # -----------------------------------------------------
    # STEP 8: QUARANTINE malicious documents
    # -----------------------------------------------------

    if scan_result["status"] == "QUARANTINED":

        QUARANTINE_FOLDER.mkdir(
            parents=True,
            exist_ok=True
        )

        quarantine_path = (
            QUARANTINE_FOLDER /
            stored_filename
        )

        try:
            stored_path.replace(
                quarantine_path
            )

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Document was detected as malicious "
                    f"but could not be quarantined: {error}"
                )
            )

        return {
            "document_id": document_id,
            "status": "QUARANTINED",
            "risk_score": scan_result[
                "risk_score"
            ],
            "ml_prediction": scan_result[
                "ml_prediction"
            ],
            "ml_malicious_probability":
                scan_result[
                    "ml_malicious_probability"
                ],
            "detected_signals":
                scan_result[
                    "detected_signals"
                ],
            "ragshield_enabled": True,
            "mode": "RAGSHIELD",
            "security_bypassed": False,
            "layer_trace": {
                "layer_1": "QUARANTINED",
                "layer_2": "BLOCKED",
                "layer_3": "BLOCKED",
            },
            "message": (
                "Document was quarantined and was not "
                "added to the vector database."
            )
        }

    # -----------------------------------------------------
    # STEP 9: APPROVED documents enter ChromaDB
    # -----------------------------------------------------

    vector_result = add_document(
        document_id=document_id,
        tenant_id=document["tenant_id"],
        filename=document["filename"],
        text=text
    )

    return {
        "document_id": document_id,
        "status": "APPROVED",
        "risk_score": scan_result[
            "risk_score"
        ],
        "ml_prediction": scan_result[
            "ml_prediction"
        ],
        "ml_malicious_probability":
            scan_result[
                "ml_malicious_probability"
            ],
        "detected_signals":
            scan_result[
                "detected_signals"
            ],
        "vector_store": vector_result,
        "ragshield_enabled": True,
        "mode": "RAGSHIELD",
        "security_bypassed": False,
        "layer_trace": {
            "layer_1": "APPROVED",
            "layer_2": "NOT_RUN",
            "layer_3": "NOT_RUN",
        },
        "message": (
            "Document passed ingestion security "
            "and was added to the vector database."
        )
    }


# ---------------------------------------------------------
# Stage 2 + Stage 3: Secure RAG
# ---------------------------------------------------------

@app.post("/search")
def secure_search(request: SearchRequest):
    """
    Complete secure RAG pipeline.

    User question
        ↓
    Input security / threat detection
        ↓
    Authorization
        ↓
    Tenant-scoped retrieval
        ↓
    Retrieved chunks
        ↓
    Gemini
        ↓
    Output security guard
        ↓
    Safe answer OR BLOCK
    """

    # -----------------------------------------------------
    # RAGShield OFF: direct baseline RAG comparison
    # -----------------------------------------------------

    if not request.ragshield_enabled:

        # No input guard, authorization, tenant filter, or output guard.
        # Retrieval uses only the separate baseline collection so unsafe
        # demo data never contaminates the protected RAGShield collection.
        results = baseline_search(
            query=request.query
        )

        documents = results.get(
            "documents",
            [[]]
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]]
        )[0]

        distances = results.get(
            "distances",
            [[]]
        )[0]

        retrieved_chunks = []

        for index, document in enumerate(documents):

            metadata = metadatas[index]
            distance = distances[index]

            similarity_score = 1 / (1 + distance)

            retrieved_chunks.append({
                "document_id": metadata["document_id"],
                "tenant_id": metadata["tenant_id"],
                "filename": metadata["filename"],
                "similarity_score": similarity_score,
                "text": document
            })

        if not retrieved_chunks:
            return {
                "safe": None,
                "blocked": False,
                "reason": (
                    "RAGShield is OFF. No baseline document "
                    "was found for this query."
                ),
                "answer": "No baseline document was found.",
                "sources": [],
                "ragshield_enabled": False,
                "mode": "BASELINE",
                "security_bypassed": True,
                "layer_trace": {
                    "layer_1": "BYPASSED",
                    "input_guard": "BYPASSED",
                    "authorization": "BYPASSED",
                    "layer_2": "BYPASSED",
                    "generation": "NOT_RUN",
                    "layer_3": "BYPASSED",
                }
            }

        try:
            generation_result = generate_baseline_answer(
                question=request.query,
                retrieved_chunks=retrieved_chunks
            )

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Baseline generation failed: {error}"
            )

        return {
            "safe": None,
            "blocked": False,
            "reason": (
                "RAGShield is OFF. Raw baseline output was "
                "returned without RAGShield security validation."
            ),
            "answer": generation_result["answer"],
            "sources": generation_result["sources"],
            "ragshield_enabled": False,
            "mode": "BASELINE",
            "security_bypassed": True,
            "layer_trace": {
                "layer_1": "BYPASSED",
                "input_guard": "BYPASSED",
                "authorization": "BYPASSED",
                "layer_2": "BYPASSED",
                "generation": "RAW_BASELINE",
                "layer_3": "BYPASSED",
            }
        }

    # -----------------------------------------------------
    # STEP 1: Input Security
    # -----------------------------------------------------

    detected_threats = detect_input_threats(request.query)

    if detected_threats:
        return {
            "safe": False,
            "blocked": True,
            "reason": "Malicious input detected.",
            "threats": detected_threats,
            "answer": "Request blocked by RAGShield.",
            "sources": [],
            "ragshield_enabled": True,
            "mode": "RAGSHIELD",
            "security_bypassed": False,
            "layer_trace": {
                "layer_1": "ENFORCED_AT_INGESTION",
                "input_guard": "BLOCKED",
                "authorization": "NOT_RUN",
                "layer_2": "NOT_RUN",
                "generation": "NOT_RUN",
                "layer_3": "NOT_RUN",
            }
        }

    # -----------------------------------------------------
    # STEP 2: Authorization
    # -----------------------------------------------------

    authorized_tenant = get_authorized_tenant(
        request.user_id
    )

    if authorized_tenant is None:
        raise HTTPException(
            status_code=403,
            detail="User is not authorized."
        )

    # -----------------------------------------------------
    # STEP 3: Tenant-scoped retrieval
    # -----------------------------------------------------

    # IMPORTANT SECURITY RULE:
    #
    # Authorization happens BEFORE vector search.
    #
    # The vector search is restricted to the tenant
    # that the user is authorized to access.

    results = tenant_scoped_search(
        query=request.query,
        authorized_tenant=authorized_tenant
    )

    # -----------------------------------------------------
    # STEP 4: Get ChromaDB results
    # -----------------------------------------------------

    documents = results.get(
        "documents",
        [[]]
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    distances = results.get(
        "distances",
        [[]]
    )[0]

    # -----------------------------------------------------
    # STEP 5: Build retrieved chunks
    # -----------------------------------------------------

    retrieved_chunks = []

    for index, document in enumerate(documents):

        metadata = metadatas[index]
        distance = distances[index]

        similarity_score = 1 / (1 + distance)

        retrieved_chunks.append({
            "document_id": metadata["document_id"],
            "tenant_id": metadata["tenant_id"],
            "filename": metadata["filename"],
            "similarity_score": similarity_score,
            "text": document
        })

    # -----------------------------------------------------
    # Retrieval trace metadata
    # -----------------------------------------------------
    # Keep a safe metadata-only copy of the retrieved evidence.
    # This is returned even if Layer 3 blocks the generated answer,
    # so the verification UI can still show what Layer 2 retrieved.
    # The retrieved text itself is intentionally not exposed here.

    retrieved_sources = [
        {
            "document_id": chunk["document_id"],
            "tenant_id": chunk["tenant_id"],
            "filename": chunk["filename"],
            "similarity_score": chunk["similarity_score"],
        }
        for chunk in retrieved_chunks
    ]

    # -----------------------------------------------------
    # STEP 6: STOP if no authorized evidence exists
    # -----------------------------------------------------

    # IMPORTANT SECURITY CONTROL:
    #
    # If there are no authorized documents, do NOT send
    # an empty evidence set to Gemini.
    #
    # The request stops here.
    #
    # This prevents the LLM from trying to answer using
    # information outside the authorized evidence.

    if not retrieved_chunks:

        return {
            "safe": True,
            "blocked": False,
            "reason": "No authorized document was found.",
            "answer": "No authorized document was found.",
            "sources": [],
            "ragshield_enabled": True,
            "mode": "RAGSHIELD",
            "security_bypassed": False,
            "layer_trace": {
                "layer_1": "ENFORCED_AT_INGESTION",
                "input_guard": "PASSED",
                "authorization": "PASSED",
                "layer_2": "PASSED_NO_MATCH",
                "generation": "NOT_RUN",
                "layer_3": "NOT_RUN",
            }
        }

    # -----------------------------------------------------
    # STEP 7: Generate answer with Gemini
    # -----------------------------------------------------

    try:

        generation_result = generate_answer(
            question=request.query,
            retrieved_chunks=retrieved_chunks
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {error}"
        )

    answer = generation_result["answer"]
    sources = generation_result["sources"]

    # -----------------------------------------------------
    # STEP 8: Stage 3 Output Security Guard
    # -----------------------------------------------------

    security_result = inspect_output(
        answer=answer,
        sources=sources,
        retrieved_chunks=retrieved_chunks,
        authorized_tenant=authorized_tenant
    )

    # -----------------------------------------------------
    # STEP 9: BLOCK UNSAFE OUTPUT
    # -----------------------------------------------------

    if not security_result["safe"]:

        return {
            "safe": False,
            "blocked": True,
            "reason": security_result["reason"],
            "answer": (
                "The generated answer was blocked because "
                "it failed the RAGShield security check."
            ),
            "sources": retrieved_sources,
            "ragshield_enabled": True,
            "mode": "RAGSHIELD",
            "security_bypassed": False,
            "layer_trace": {
                "layer_1": "ENFORCED_AT_INGESTION",
                "input_guard": "PASSED",
                "authorization": "PASSED",
                "layer_2": "PASSED",
                "generation": "COMPLETED",
                "layer_3": "BLOCKED",
            }
        }

    # -----------------------------------------------------
    # STEP 10: Return SAFE output
    # -----------------------------------------------------

    return {
        "safe": True,
        "blocked": False,
        "reason": security_result["reason"],
        "answer": answer,
        "sources": sources,
        "ragshield_enabled": True,
        "mode": "RAGSHIELD",
        "security_bypassed": False,
        "layer_trace": {
            "layer_1": "ENFORCED_AT_INGESTION",
            "input_guard": "PASSED",
            "authorization": "PASSED",
            "layer_2": "PASSED",
            "generation": "COMPLETED",
            "layer_3": "PASSED",
        }
    }