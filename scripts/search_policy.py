from argparse import ArgumentParser

from orderops_api.rag.search import search_policy


def main() -> None:
    parser = ArgumentParser(description="Search indexed policy chunks.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--no-rerank", action="store_true")
    args = parser.parse_args()

    results = search_policy(args.query, top_k=args.top_k, rerank=not args.no_rerank)
    for result in results:
        print(f"{result.score:.4f} {result.doc_id} {result.section_id} {result.title}")
        print(result.text.replace("\n", " ")[:300])
        print()


if __name__ == "__main__":
    main()
