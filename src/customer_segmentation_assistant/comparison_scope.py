"""Detect known unsupported requirements in comparison requests."""

import re

TENURE_PATTERNS = (
    r"\btenure\b",
    r"\bcustomer\s+seniority\b",
    r"\bcustomer\s+lifetime\b",
    (
        r"\b(?:customers?|subscribers?)\s+"
        r"(?:who\s+)?(?:have\s+)?(?:been\s+)?"
        r"(?:with\s+(?:us|the company)|subscribed|active)\s+for\b"
    ),
    (
        r"\b(?:customers?|subscribers?)\s+for\s+"
        r"(?:at least|more than|less than|over|under)\b"
    ),
)

CHARGE_FILTER_PATTERNS = (
    (
        r"\bmonthly\s+(?:charges?|costs?|payments?)\s+"
        r"(?:of\s+)?"
        r"(?:at least|at most|above|below|over|under|"
        r"greater than|less than|more than|between)\b"
    ),
    r"\bmonthly\s+(?:charges?|costs?|payments?)\s*[<>=]",
    (
        r"\b(?:paying|spending|charged)\s+"
        r"(?:at least|at most|above|below|over|under|"
        r"more than|less than|between)\b"
    ),
)

ATTRIBUTE_FILTER_PATTERNS = (
    r"\b(?:customer\s+)?age\b",
    r"\bgender\b",
    r"\bsenior\s+citizens?\b",
    r"\btotal\s+charges\b",
    r"\bpayment\s+method\b",
    r"\binternet\s+service\b",
)


def detect_unsupported_requirements(question: str) -> list[str]:
    """Detect known unsupported requirements without calling a model."""
    requirements = []

    if any(re.search(pattern, question, re.IGNORECASE) for pattern in TENURE_PATTERNS):
        requirements.append("Customer tenure conditions and metrics are not supported.")

    if any(
        re.search(pattern, question, re.IGNORECASE)
        for pattern in CHARGE_FILTER_PATTERNS
    ):
        requirements.append("Monthly charge filters are not supported.")

    if any(
        re.search(pattern, question, re.IGNORECASE)
        for pattern in ATTRIBUTE_FILTER_PATTERNS
    ):
        requirements.append("Additional customer attributes are not supported.")

    return requirements


def check_comparison_scope(question: str) -> dict[str, object] | None:
    """Return an unsupported decision for known out-of-scope requests."""
    requirements = detect_unsupported_requirements(question)

    if not requirements:
        return None

    return {
        "kind": "unsupported",
        "message": "Unsupported requirements: " + "; ".join(requirements),
    }
