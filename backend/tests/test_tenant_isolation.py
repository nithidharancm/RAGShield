from retrieval.authorization import get_authorized_tenant


def test_user_001_belongs_to_tenant_a():
    assert get_authorized_tenant("user_001") == "tenant_a"


def test_user_002_belongs_to_tenant_b():
    assert get_authorized_tenant("user_002") == "tenant_b"


def test_user_003_belongs_to_tenant_c():
    assert get_authorized_tenant("user_003") == "tenant_c"


def test_unknown_user_is_rejected():
    assert get_authorized_tenant("unknown_user") is None