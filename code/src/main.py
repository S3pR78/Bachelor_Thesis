import argparse

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orkg-sparql-pipeline",
        description="CLI entry point for the ORKG pipeline."
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    print(args)
    return 0



if __name__ == "__main__":
    raise SystemExit(main())