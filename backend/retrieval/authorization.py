# Simple user-to-tenant mapping for the hackathon MVP.

USER_TENANT_MAP = {
    "user_001": "tenant_a",
    "user_002": "tenant_b",
    "user_003": "tenant_c",
}


def get_authorized_tenant(user_id):
    """
    Return the tenant that this user is allowed to access.

    If the user does not exist, return None.
    """

    return USER_TENANT_MAP.get(user_id)