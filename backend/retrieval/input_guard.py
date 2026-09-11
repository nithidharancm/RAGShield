import re


THREAT_PATTERNS = {
    "ignore previous instructions": [
        r"\bignore\s+(all\s+)?previous\s+instructions\b",
        r"\bignore\s+(all\s+)?prior\s+instructions\b",
    ],

    "reveal system prompt": [
        r"\breveal\s+(your\s+)?system\s+prompt\b",
        r"\bshow\s+(me\s+)?(your\s+)?system\s+prompt\b",
        r"\bprint\s+(your\s+)?system\s+prompt\b",
    ],

    "reveal instructions": [
        r"\breveal\s+your\s+instructions\b",
        r"\bshow\s+your\s+instructions\b",
    ],

    "act as system/developer": [
        r"\bact\s+as\s+(the\s+)?system\b",
        r"\bact\s+as\s+(the\s+)?developer\b",
    ],

    "prompt injection": [
        r"\bwhen\s+an\s+ai\s+reads\s+this\b",
        r"\bwhen\s+retrieved\b",
        r"\bllm\s+should\b",
        r"\bai\s+must\b",
    ],

    "suspicious external action": [
        r"\bsend\s+confidential\s+information\b",
        r"\bsend\s+confidential\s+data\b",
        r"\bupload\s+data\s+to\b",
        r"\bsend\s+data\s+to\s+(a\s+)?url\b",
        r"\bdownload\s+and\s+execute\b",
    ],
}


def detect_input_threats(text: str) -> list[str]:
    """
    Detect known prompt-injection and suspicious-action patterns.

    Returns a short list of threat descriptions.
    """

    if not text:
        return []

    threats = []

    for threat_name, patterns in THREAT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                threats.append(threat_name)
                break

    return threats