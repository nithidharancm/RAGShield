from retrieval.authorization import get_authorized_tenant
from retrieval.search import tenant_scoped_search


def test_user_001_is_only_allowed_tenant_a():
    tenant = get_authorized_tenant("user_001")

    assert tenant == "tenant_a"


def test_user_002_is_only_allowed_tenant_b():
    tenant = get_authorized_tenant("user_002")

    assert tenant == "tenant_b"


def test_user_003_is_only_allowed_tenant_c():
    tenant = get_authorized_tenant("user_003")

    assert tenant == "tenant_c"


def test_unknown_user_has_no_tenant():
    tenant = get_authorized_tenant("unknown_user")

    assert tenant is None


def test_search_cannot_return_tenant_b_for_tenant_a():
    results = tenant_scoped_search(
        query="secret project",
        authorized_tenant="tenant_a"
    )

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    for metadata in metadatas:
        assert metadata["tenant_id"] == "tenant_a"


def test_search_cannot_return_tenant_a_for_tenant_b():
    results = tenant_scoped_search(
        query="secret project",
        authorized_tenant="tenant_b"
    )

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    for metadata in metadatas:
        assert metadata["tenant_id"] == "tenant_b"


def test_search_cannot_return_tenant_c_for_tenant_a():
    results = tenant_scoped_search(
        query="project",
        authorized_tenant="tenant_a"
    )

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    for metadata in metadatas:
        assert metadata["tenant_id"] == "tenant_a"