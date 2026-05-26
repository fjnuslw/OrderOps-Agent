from scripts.download_hf_snapshot import repo_api_url, resolve_url, should_skip


def test_huggingface_urls_are_built_from_endpoint() -> None:
    assert (
        repo_api_url("BAAI/bge-m3", "https://huggingface.co")
        == "https://huggingface.co/api/models/BAAI/bge-m3"
    )
    assert (
        resolve_url("BAAI/bge-m3", "onnx/model.onnx", "https://hf-mirror.com")
        == "https://hf-mirror.com/BAAI/bge-m3/resolve/main/onnx/model.onnx?download=1"
    )


def test_should_skip_uses_glob_patterns() -> None:
    ignore = ["imgs/*", "onnx/*", "*.jpg"]

    assert should_skip("imgs/logo.png", ignore)
    assert should_skip("onnx/model.onnx", ignore)
    assert should_skip("example.jpg", ignore)
    assert not should_skip("config.json", ignore)
