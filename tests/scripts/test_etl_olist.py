from pathlib import Path

import pytest

from scripts.etl_olist import CSV_TABLES, missing_csv_files, require_csv_files


def test_missing_csv_files_reports_every_required_file(tmp_path: Path) -> None:
    missing = missing_csv_files(tmp_path)

    assert len(missing) == len(CSV_TABLES)
    assert tmp_path / "olist_orders_dataset.csv" in missing
    assert tmp_path / "olist_customers_dataset.csv" in missing


def test_require_csv_files_passes_when_all_required_files_exist(tmp_path: Path) -> None:
    for spec in CSV_TABLES:
        (tmp_path / spec.file_name).write_text(",".join(spec.columns), encoding="utf-8")

    require_csv_files(tmp_path)


def test_require_csv_files_raises_clear_error_for_missing_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Missing Olist CSV files"):
        require_csv_files(tmp_path)
