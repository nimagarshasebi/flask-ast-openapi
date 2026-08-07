"""Command-line interface for flask-ast-openapi."""

import argparse
from pathlib import Path

from .generator import FlaskASTOpenAPI


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""

    parser = argparse.ArgumentParser(
        prog="flask-ast-openapi",
        description="Generate OpenAPI specifications from Flask source code.",
    )

    parser.add_argument(
        "source_dir",
        type=Path,
        help="Path to the Flask source directory.",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("openapi.json"),
        help="Output file path.",
    )

    return parser


def main() -> None:
    """Generate an OpenAPI specification from Flask source code."""

    parser = build_parser()
    args = parser.parse_args()

    generator = FlaskASTOpenAPI(
        args.source_dir
    )

    spec = generator.generate()

    generator.write_json(
        spec,
        args.output,
    )