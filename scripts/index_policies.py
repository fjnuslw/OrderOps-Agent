from argparse import ArgumentParser
from pathlib import Path

from orderops_api.core.config import get_settings
from orderops_api.rag.embedding import HashingEmbeddingProvider
from orderops_api.rag.policies import load_policy_chunks
from orderops_api.rag.qdrant import QdrantHttpClient


def index_policies(policy_dir: Path) -> int:
    settings = get_settings()
    embedding_provider = HashingEmbeddingProvider()
    chunks = load_policy_chunks(policy_dir)
    client = QdrantHttpClient(settings.qdrant_url, settings.qdrant_collection)
    client.recreate_collection(embedding_provider.dimension)
    client.upsert_chunks(chunks, embedding_provider)
    return len(chunks)


def main() -> None:
    parser = ArgumentParser(description="Index policy markdown files into Qdrant.")
    parser.add_argument("--policy-dir", type=Path, default=Path("data/policies"))
    args = parser.parse_args()

    count = index_policies(args.policy_dir)
    print(f"indexed_policy_chunks: {count}")


if __name__ == "__main__":
    main()
