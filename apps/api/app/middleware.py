"""
Mandate Gateway — Request Identity & Correlation Middleware
Section S00.4 — Application Runtime Foundation
"""

import re
import uuid
from typing import Dict, Tuple

# Validation pattern: alphanumeric, hyphen, underscore, length 1..128
VALID_ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-_]{1,128}$")


def sanitize_or_generate_id(header_val: str) -> str:
    """
    Validates caller-supplied request/correlation ID against safe formatting rules.
    If valid, returns the header value. Otherwise, generates a safe UUIDv4.
    """
    if header_val and isinstance(header_val, str):
        val = header_val.strip()
        if VALID_ID_PATTERN.match(val):
            return val
    return str(uuid.uuid4())


def extract_request_headers(headers_dict: Dict[str, str]) -> Tuple[str, str, str]:
    """
    Extracts and sanitizes request_id, correlation_id, and trace_id from HTTP headers.
    Headers are matched case-insensitively.
    """
    normalized_headers = {k.lower(): v for k, v in headers_dict.items()}

    req_id = sanitize_or_generate_id(normalized_headers.get("x-request-id", ""))
    corr_id = sanitize_or_generate_id(normalized_headers.get("x-correlation-id", req_id))
    trace_id = sanitize_or_generate_id(normalized_headers.get("x-trace-id", corr_id))

    return req_id, corr_id, trace_id
