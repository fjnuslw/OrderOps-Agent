from __future__ import annotations

import re


FORBIDDEN_SQL_KEYWORDS = (
    "alter",
    "copy",
    "create",
    "delete",
    "drop",
    "grant",
    "insert",
    "merge",
    "revoke",
    "truncate",
    "update",
)

PRIVATE_FIELDS = (
    "customer_unique_id",
    "customer_zip_code_prefix",
    "seller_zip_code_prefix",
    "review_comment_message",
)


class SqlGuardError(ValueError):
    pass


def strip_sql_comments(sql: str) -> str:
    without_line_comments = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    return re.sub(r"/\*.*?\*/", "", without_line_comments, flags=re.DOTALL)


def ensure_select_only(sql: str) -> str:
    cleaned = strip_sql_comments(sql).strip()
    normalized = cleaned.lower()
    if not normalized:
        raise SqlGuardError("SQL is empty.")
    if not (normalized.startswith("select") or normalized.startswith("with")):
        raise SqlGuardError("Only SELECT or WITH queries are allowed.")
    if ";" in cleaned.rstrip(";"):
        raise SqlGuardError("Multiple SQL statements are not allowed.")
    for keyword in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", normalized):
            raise SqlGuardError(f"Forbidden SQL keyword: {keyword}.")
    for field in PRIVATE_FIELDS:
        if re.search(rf"\b{field}\b", normalized):
            raise SqlGuardError(f"Forbidden private field: {field}.")
    return cleaned.rstrip(";").strip()


def add_limit_if_missing(sql: str, limit: int = 100) -> str:
    cleaned = ensure_select_only(sql)
    match = re.search(r"\blimit\s+(\d+)\b", cleaned, flags=re.IGNORECASE)
    if match is not None:
        current_limit = int(match.group(1))
        if current_limit <= limit:
            return cleaned
        return re.sub(
            r"\blimit\s+\d+\b",
            f"LIMIT {limit}",
            cleaned,
            count=1,
            flags=re.IGNORECASE,
        )
    return f"{cleaned} LIMIT {limit}"
