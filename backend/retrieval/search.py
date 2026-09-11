from database.vector_store import (
    search_documents,
    search_baseline_documents,
)


def tenant_scoped_search(query, authorized_tenant):
    """
    Search only documents belonging to the authorized tenant.
    """

    return search_documents(
        query=query,
        tenant_id=authorized_tenant,
        limit=5
    )


def baseline_search(query):
    """
    Baseline retrieval used only when RAGShield is OFF.

    No tenant filter is applied so the demo can show the difference
    made by the protected retrieval layer.
    """

    return search_baseline_documents(
        query=query,
        limit=5
    )
