import argparse

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orkg-sparql-pipeline",
        description="CLI entry point for the ORKG pipeline."
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    subparsers.add_parser("query", help="Run a single query task.")
    subparsers.add_parser("train", help="Run a training task.")
    subparsers.add_parser("evaluate", help="Run an evaluation task.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    print(args)
    return 0



if __name__ == "__main__":
    raise SystemExit(main())