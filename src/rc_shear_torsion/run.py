from __future__ import annotations

import argparse
import sys

from .domain.errors import DomainValidationError
from .engine import run_case


def ensure_python_312() -> None:
    if sys.version_info[:2] != (3, 12):
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        raise RuntimeError(
            "This project requires Python 3.12.x. "
            f"Current interpreter: {version}. "
            "Use python3.12 to create/activate the virtual environment."
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rc_shear_torsion.run")
    parser.add_argument("case_json", help="Path to case.json")
    parser.add_argument("--out", default="results/", help="Output root directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    ensure_python_312()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output_dir = run_case(args.case_json, args.out)
        print(output_dir)
        return 0
    except DomainValidationError as exc:
        print("Domain validation failed:", file=sys.stderr)
        for issue in exc.issues:
            print(f"- [{issue.code}] {issue.field}: {issue.message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
