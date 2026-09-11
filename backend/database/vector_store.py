import chromadb


client = chromadb.PersistentClient(
    path="data/chroma"
)

# Existing protected RAGShield collection.
collection = client.get_or_create_collection(
    name="ragshield_documents"
)

# Separate baseline collection used only when RAGShield is OFF.
# Keeping this separate prevents intentionally unsafe demo documents
# from contaminating the protected collection above.
baseline_collection = client.get_or_create_collection(
    name="ragshield_baseline_documents"
)


def add_document(
    document_id,
    tenant_id,
    filename,
    text
):
    """
    Add an APPROVED document to the protected ChromaDB collection.

    The document is split into chunks.
    Each chunk gets its own embedding and metadata.
    """

    # Import here to keep chunking logic separate
    from ingestion.chunker import chunk_text

    chunks = chunk_text(text)

    if not chunks:
        return {
            "chunks_added": 0
        }

    ids = []
    metadatas = []

    for index, chunk in enumerate(chunks):

        chunk_id = f"{document_id}_chunk_{index}"

        ids.append(chunk_id)

        metadatas.append({
            "document_id": document_id,
            "tenant_id": tenant_id,
            "filename": filename,
        })

    collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    return {
        "chunks_added": len(chunks)
    }


def search_documents(query, tenant_id, limit=5):
    """
    Search ONLY inside the authorized tenant.

    The tenant filter is applied by ChromaDB
    before similarity results are returned.
    """

    results = collection.query(
        query_texts=[query],
        n_results=limit,
        where={
            "tenant_id": tenant_id
        },
    )

    return results


# ---------------------------------------------------------
# Baseline RAG store used only when RAGShield is OFF
# ---------------------------------------------------------


def add_baseline_document(
    document_id,
    tenant_id,
    filename,
    text
):
    """
    Add a document directly to the baseline collection.

    No RAGShield ingestion scan is performed before this function
    is called. This is intentionally separate from the protected
    collection so the demo can compare baseline RAG vs RAGShield.
    """

    from ingestion.chunker import chunk_text

    chunks = chunk_text(text)

    if not chunks:
        return {
            "chunks_added": 0
        }

    ids = []
    metadatas = []

    for index, chunk in enumerate(chunks):

        chunk_id = f"baseline_{document_id}_chunk_{index}"

        ids.append(chunk_id)

        metadatas.append({
            "document_id": document_id,
            "tenant_id": tenant_id,
            "filename": filename,
            "ragshield_enabled": False,
        })

    baseline_collection.add(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    return {
        "chunks_added": len(chunks)
    }


def search_baseline_documents(query, limit=5):
    """
    Search the baseline collection with NO tenant filter.

    This intentionally demonstrates how a naive RAG pipeline can
    retrieve across tenants when RAGShield Layer 2 is disabled.
    """

    return baseline_collection.query(
        query_texts=[query],
        n_results=limit,
    )
