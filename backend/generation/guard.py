import re


# ---------------------------------------------------------
# Malicious instruction patterns
# ---------------------------------------------------------

MALICIOUS_INSTRUCTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "ignore the system prompt",
    "ignore system instructions",
    "reveal your instructions",
    "reveal the system prompt",
    "reveal your prompt",
    "developer message",
    "system message",
]


# ---------------------------------------------------------
# Suspicious external action patterns
# ---------------------------------------------------------

# These patterns are intentionally more specific.
#
# Normal policy language such as:
#
# "Send incident reports to the IT team."
#
# should NOT be blocked.
#
# We only block actions that involve:
# - suspicious external destinations
# - sensitive information
# - command/script execution
# - obvious data exfiltration


EXTERNAL_ACTION_PATTERNS = [

    # -----------------------------------------------------
    # Sending/uploading data to suspicious external targets
    # -----------------------------------------------------

    r"\b(?:send|upload|submit|post)\b.*"
    r"\b(?:https?://|www\.|webhook|pastebin|remote server|"
    r"external site|third[- ]party site|unknown site)\b",

    # -----------------------------------------------------
    # Sensitive information disclosure
    # -----------------------------------------------------

    r"\b(?:send|upload|share|disclose|submit)\b.*"
    r"\b(?:password|api key|secret key|access token|"
    r"authentication token|credential|credentials)\b",

    # -----------------------------------------------------
    # Explicit code / command execution
    # -----------------------------------------------------

    r"\bexecute\b.*\b(?:command|script|program|executable)\b",

    r"\brun\b.*\b(?:shell command|terminal command|"
    r"powershell command|script|executable)\b",

    # -----------------------------------------------------
    # Explicit exfiltration / leakage
    # -----------------------------------------------------

    r"\b(?:exfiltrate|steal|leak)\b.*"
    r"\b(?:data|information|credentials|files|secrets)\b",
]


# ---------------------------------------------------------
# Text helpers
# ---------------------------------------------------------

def normalize_text(text):
    """
    Convert text into a simple normalized form.
    """

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def get_sentences(text):
    """
    Split text into simple sentences.
    """

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text.strip()
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


# ---------------------------------------------------------
# Helper: detect safe negated instructions
# ---------------------------------------------------------

def is_negated_action(sentence):
    """
    Detect statements that WARN against an action.

    Examples:

    "Do not share passwords."
    "Never upload credentials to external websites."

    These are security recommendations, not malicious actions.
    """

    normalized = normalize_text(sentence)

    negation_patterns = [
        r"\bdo not\b",
        r"\bdon't\b",
        r"\bmust not\b",
        r"\bshould not\b",
        r"\bnever\b",
        r"\bavoid\b",
        r"\bprohibited\b",
        r"\bnot allowed\b",
    ]

    return any(
        re.search(pattern, normalized)
        for pattern in negation_patterns
    )


# ---------------------------------------------------------
# Check 1: Instruction Echo
# ---------------------------------------------------------

def check_instruction_echo(answer, retrieved_chunks):
    """
    Detect whether the generated answer repeats
    malicious instructions found in retrieved documents.
    """

    answer_normalized = normalize_text(answer)

    for chunk in retrieved_chunks:

        chunk_text = normalize_text(
            chunk["text"]
        )

        for pattern in MALICIOUS_INSTRUCTION_PATTERNS:

            if (
                pattern in chunk_text
                and pattern in answer_normalized
            ):

                return {
                    "safe": False,
                    "reason": (
                        "The generated answer echoed a "
                        "malicious instruction found in "
                        "retrieved document evidence."
                    )
                }

    return {
        "safe": True,
        "reason": ""
    }


# ---------------------------------------------------------
# Check 2: Unsolicited External Actions
# ---------------------------------------------------------

def check_external_actions(answer):
    """
    Detect genuinely suspicious external actions.

    Normal organizational instructions such as:

    "Send incident reports to the IT team."

    are allowed.

    Suspicious actions such as:

    "Send your API key to https://unknown-site.example"

    are blocked.
    """

    sentences = get_sentences(answer)

    for sentence in sentences:

        sentence_normalized = normalize_text(
            sentence
        )

        # A warning telling the user NOT to perform
        # an unsafe action should not itself be blocked.
        if is_negated_action(sentence_normalized):
            continue

        for pattern in EXTERNAL_ACTION_PATTERNS:

            if re.search(
                pattern,
                sentence_normalized
            ):

                return {
                    "safe": False,
                    "reason": (
                        "The generated answer contains a "
                        "suspicious external action."
                    )
                }

    return {
        "safe": True,
        "reason": ""
    }


# ---------------------------------------------------------
# Check 3: Unsupported Claims
# ---------------------------------------------------------

def check_supported_claims(answer, retrieved_chunks):
    """
    Perform a simple evidence-grounding check.

    Each answer sentence must share meaningful words
    with at least one retrieved chunk.

    This is a lightweight MVP check.
    A future version can use an LLM or embedding-based
    entailment model for stronger claim verification.
    """

    if not retrieved_chunks:

        return {
            "safe": False,
            "reason": (
                "The answer has no retrieved evidence "
                "to support it."
            )
        }

    evidence_text = " ".join(
        chunk["text"]
        for chunk in retrieved_chunks
    )

    evidence_words = set(
        re.findall(
            r"\b[a-zA-Z0-9]{4,}\b",
            normalize_text(evidence_text)
        )
    )

    answer_sentences = get_sentences(answer)

    for sentence in answer_sentences:

        sentence_words = set(
            re.findall(
                r"\b[a-zA-Z0-9]{4,}\b",
                normalize_text(sentence)
            )
        )

        if not sentence_words:
            continue

        overlap = sentence_words.intersection(
            evidence_words
        )

        # Require at least one meaningful evidence word.
        #
        # This is intentionally simple for the hackathon MVP.
        if len(overlap) == 0:

            return {
                "safe": False,
                "reason": (
                    "The generated answer contains a "
                    "claim that could not be matched "
                    "to the retrieved evidence."
                )
            }

    return {
        "safe": True,
        "reason": ""
    }


# ---------------------------------------------------------
# Check 4: Source Validity
# ---------------------------------------------------------

def check_source_validity(
    sources,
    retrieved_chunks,
    authorized_tenant
):
    """
    Make sure every cited source:

    1. Belongs to the authorized tenant.
    2. Was actually retrieved.
    """

    retrieved_document_ids = {
        chunk["document_id"]
        for chunk in retrieved_chunks
    }

    for source in sources:

        source_document_id = source.get(
            "document_id"
        )

        source_tenant_id = source.get(
            "tenant_id"
        )

        # -------------------------------------------------
        # Check tenant
        # -------------------------------------------------

        if source_tenant_id != authorized_tenant:

            return {
                "safe": False,
                "reason": (
                    "A cited source belongs to an "
                    "unauthorized tenant."
                )
            }

        # -------------------------------------------------
        # Check retrieval
        # -------------------------------------------------

        if (
            source_document_id
            not in retrieved_document_ids
        ):

            return {
                "safe": False,
                "reason": (
                    "A cited source was not actually "
                    "retrieved for this query."
                )
            }

    return {
        "safe": True,
        "reason": ""
    }


# ---------------------------------------------------------
# Main Output Security Guard
# ---------------------------------------------------------

def inspect_output(
    answer,
    sources,
    retrieved_chunks,
    authorized_tenant
):
    """
    Run all Stage 3 output security checks.
    """

    # -----------------------------------------------------
    # Check 1: Instruction echo
    # -----------------------------------------------------

    result = check_instruction_echo(
        answer,
        retrieved_chunks
    )

    if not result["safe"]:
        return result

    # -----------------------------------------------------
    # Check 2: External actions
    # -----------------------------------------------------

    result = check_external_actions(
        answer
    )

    if not result["safe"]:
        return result

    # -----------------------------------------------------
    # Check 3: Unsupported claims
    # -----------------------------------------------------

    result = check_supported_claims(
        answer,
        retrieved_chunks
    )

    if not result["safe"]:
        return result

    # -----------------------------------------------------
    # Check 4: Source validity
    # -----------------------------------------------------

    result = check_source_validity(
        sources,
        retrieved_chunks,
        authorized_tenant
    )

    if not result["safe"]:
        return result

    # -----------------------------------------------------
    # Everything passed
    # -----------------------------------------------------

    return {
        "safe": True,
        "reason": "Output passed all security checks."
    }