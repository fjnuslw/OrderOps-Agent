from argparse import ArgumentParser
from pathlib import Path

from orderops_api.core.config import get_settings


DEFAULT_SCHEMA_PATH = Path("data/sql/target_schema.sql")


def load_schema(schema_path: Path = DEFAULT_SCHEMA_PATH) -> str:
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    return schema_path.read_text(encoding="utf-8")


def apply_schema(database_url: str, schema_sql: str) -> None:
    import psycopg

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(schema_sql)
        conn.commit()


def main() -> None:
    parser = ArgumentParser(description="Apply the OrderOps target schema.")
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Path to the SQL schema file.",
    )
    args = parser.parse_args()

    settings = get_settings()
    schema_sql = load_schema(args.schema)
    apply_schema(settings.database_url, schema_sql)
    print(f"Applied schema from {args.schema} to {settings.database_url}")


if __name__ == "__main__":
    main()
