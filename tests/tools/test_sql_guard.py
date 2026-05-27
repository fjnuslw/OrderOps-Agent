import pytest

from orderops_api.tools.sql_guard import SqlGuardError, add_limit_if_missing, ensure_select_only


def test_sql_guard_allows_select_and_adds_limit() -> None:
    assert add_limit_if_missing("SELECT order_id FROM orders", limit=50).endswith("LIMIT 50")
    assert add_limit_if_missing("SELECT order_id FROM orders LIMIT 10") == (
        "SELECT order_id FROM orders LIMIT 10"
    )
    assert add_limit_if_missing("SELECT order_id FROM orders LIMIT 1000", limit=50) == (
        "SELECT order_id FROM orders LIMIT 50"
    )


def test_sql_guard_rejects_write_statements() -> None:
    with pytest.raises(SqlGuardError, match="Only SELECT"):
        ensure_select_only("DELETE FROM orders")

    with pytest.raises(SqlGuardError, match="Multiple SQL statements"):
        ensure_select_only("SELECT * FROM orders; DROP TABLE orders")


def test_sql_guard_rejects_private_fields() -> None:
    with pytest.raises(SqlGuardError, match="Forbidden private field"):
        ensure_select_only("SELECT customer_unique_id FROM customers")
