from datetime import datetime
from decimal import Decimal

from orderops_api.tools.sql_tools import jsonable_row


def test_jsonable_row_converts_database_values() -> None:
    row = jsonable_row(
        {
            "amount": Decimal("12.34"),
            "created_at": datetime(2018, 1, 1, 12, 30),
            "name": "order",
        }
    )

    assert row == {
        "amount": 12.34,
        "created_at": "2018-01-01T12:30:00",
        "name": "order",
    }
