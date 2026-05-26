from argparse import ArgumentParser
from fnmatch import fnmatch
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


def repo_api_url(repo_id: str, endpoint: str) -> str:
    return f"{endpoint.rstrip('/')}/api/models/{repo_id}"


def resolve_url(repo_id: str, file_name: str, endpoint: str) -> str:
    quoted_file_name = quote(file_name, safe="/")
    return f"{endpoint.rstrip('/')}/{repo_id}/resolve/main/{quoted_file_name}?download=1"


def load_sibling_files(repo_id: str, endpoint: str) -> list[str]:
    with urlopen(repo_api_url(repo_id, endpoint), timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return [item["rfilename"] for item in payload["siblings"]]


def should_skip(file_name: str, ignore: list[str]) -> bool:
    return any(fnmatch(file_name, pattern) for pattern in ignore)


def remote_size(url: str) -> int | None:
    req = Request(url, method="HEAD")
    with urlopen(req, timeout=60) as response:
        content_length = response.headers.get("Content-Length")
    return None if content_length is None else int(content_length)


def download_file(url: str, target: Path) -> None:
    expected_size = remote_size(url)
    for _ in range(5):
        current_size = target.stat().st_size if target.exists() else 0
        if expected_size is not None and current_size >= expected_size:
            return

        headers = {}
        mode = "wb"
        if current_size > 0:
            headers["Range"] = f"bytes={current_size}-"
            mode = "ab"

        req = Request(url, headers=headers)
        with urlopen(req, timeout=60) as response:
            if current_size > 0 and getattr(response, "status", None) != 206:
                mode = "wb"
            with target.open(mode) as file:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    file.write(chunk)

    final_size = target.stat().st_size if target.exists() else 0
    if expected_size is not None and final_size < expected_size:
        raise RuntimeError(
            f"Download incomplete for {target}: got {final_size}, expected {expected_size}"
        )


def download_snapshot(
    repo_id: str,
    local_dir: Path,
    endpoint: str,
    ignore: list[str],
) -> list[Path]:
    local_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []

    for file_name in load_sibling_files(repo_id, endpoint):
        if should_skip(file_name, ignore):
            continue

        target = local_dir / file_name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size > 0:
            size = remote_size(resolve_url(repo_id, file_name, endpoint))
            if size is not None and target.stat().st_size >= size:
                print(f"skip_existing: {target}")
                continue
            print(f"resume: {file_name}")
        else:
            print(f"download: {file_name}")

        download_file(resolve_url(repo_id, file_name, endpoint), target)
        downloaded.append(target)

    return downloaded


def main() -> None:
    parser = ArgumentParser(description="Download selected files from a HuggingFace model repo.")
    parser.add_argument("repo_id")
    parser.add_argument("local_dir", type=Path)
    parser.add_argument("--endpoint", default="https://huggingface.co")
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Glob pattern to skip. Can be provided multiple times.",
    )
    args = parser.parse_args()

    downloaded = download_snapshot(
        repo_id=args.repo_id,
        local_dir=args.local_dir,
        endpoint=args.endpoint,
        ignore=args.ignore,
    )
    print(f"downloaded_files: {len(downloaded)}")


if __name__ == "__main__":
    main()
