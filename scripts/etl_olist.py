from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from orderops_api.core.config import get_settings


RAW_DIR = Path("data/raw")


@dataclass(frozen=True)
class CsvTableSpec:
    table_name: str
    file_name: str
    columns: tuple[str, ...]


CSV_TABLES: tuple[CsvTableSpec, ...] = (
    CsvTableSpec(
        table_name="orders",
        file_name="olist_orders_dataset.csv",
        columns=(
            "order_id",
            "customer_id",
            "order_status",
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ),
    ),
    CsvTableSpec(
        table_name="order_items",
        file_name="olist_order_items_dataset.csv",
        columns=(
            "order_id",
            "order_item_id",
            "product_id",
            "seller_id",
            "shipping_limit_date",
            "price",
            "freight_value",
        ),
    ),
    CsvTableSpec(
        table_name="payments",
        file_name="olist_order_payments_dataset.csv",
        columns=(
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ),
    ),
    CsvTableSpec(
        table_name="reviews",
        file_name="olist_order_reviews_dataset.csv",
        columns=(
            "review_id",
            "order_id",
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_answer_timestamp",
        ),
    ),
    CsvTableSpec(
        table_name="products",
        file_name="olist_products_dataset.csv",
        columns=(
            "product_id",
            "product_category_name",
            "product_name_lenght",
            "product_description_lenght",
            "product_photos_qty",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ),
    ),
    CsvTableSpec(
        table_name="sellers",
        file_name="olist_sellers_dataset.csv",
        columns=("seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"),
    ),
    CsvTableSpec(
        table_name="customers",
        file_name="olist_customers_dataset.csv",
        columns=(
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ),
    ),
)


def missing_csv_files(raw_dir: Path, specs: Iterable[CsvTableSpec] = CSV_TABLES) -> list[Path]:
    return [raw_dir / spec.file_name for spec in specs if not (raw_dir / spec.file_name).exists()]


def require_csv_files(raw_dir: Path) -> None:
    missing = missing_csv_files(raw_dir)
    if missing:
        formatted = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(
            "Missing Olist CSV files. Download the dataset and place these files under "
            f"{raw_dir}:\n{formatted}"
        )


def copy_csv_table(cursor, raw_dir: Path, spec: CsvTableSpec) -> None:
    columns_sql = ", ".join(spec.columns)
    copy_sql = (
        f"COPY {spec.table_name} ({columns_sql}) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')"
    )
    file_path = raw_dir / spec.file_name

    with cursor.copy(copy_sql) as copy:
        with file_path.open("r", encoding="utf-8", newline="") as csv_file:
            for line in csv_file:
                copy.write(line)


def truncate_tables(cursor, specs: Iterable[CsvTableSpec] = CSV_TABLES) -> None:
    table_names = ", ".join(spec.table_name for spec in specs)
    cursor.execute(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")


def table_counts(cursor, specs: Iterable[CsvTableSpec] = CSV_TABLES) -> dict[str, int]:
    counts: dict[str, int] = {}
    for spec in specs:
        cursor.execute(f"SELECT COUNT(*) FROM {spec.table_name}")
        counts[spec.table_name] = cursor.fetchone()[0]
    return counts


def import_olist_csvs(database_url: str, raw_dir: Path = RAW_DIR, replace: bool = False) -> dict[str, int]:
    import psycopg

    require_csv_files(raw_dir)

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            if replace:
                truncate_tables(cursor)
            for spec in CSV_TABLES:
                copy_csv_table(cursor, raw_dir, spec)
            counts = table_counts(cursor)
        conn.commit()
    return counts


def main() -> None:
    parser = ArgumentParser(description="Import Olist CSV files into PostgreSQL.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Truncate target tables before importing.",
    )
    args = parser.parse_args()

    settings = get_settings()
    counts = import_olist_csvs(settings.database_url, args.raw_dir, args.replace)

    for table_name, count in counts.items():
        print(f"{table_name}: {count}")


if __name__ == "__main__":
    main()
