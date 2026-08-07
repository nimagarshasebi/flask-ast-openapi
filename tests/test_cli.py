from pathlib import Path

from flask_ast_openapi.cli import build_parser

import json
import sys

from flask_ast_openapi.cli import main
def test_build_parser_parses_source_directory():
    parser = build_parser()

    args = parser.parse_args(
        [
            "./app",
        ]
    )

    assert args.source_dir == Path("./app")
def test_build_parser_parses_output_path():
    parser = build_parser()

    args = parser.parse_args(
        [
            "./app",
            "--output",
            "schema.json",
        ]
    )

    assert args.output == Path("schema.json")

def test_build_parser_uses_default_output_path():
    parser = build_parser()

    args = parser.parse_args(
        [
            "./app",
        ]
    )

    assert args.output == Path("openapi.json")
def test_main_generates_openapi_json(
    tmp_path,
    monkeypatch,
):
    source_dir = tmp_path / "app"
    source_dir.mkdir()

    controller_file = source_dir / "user_controller.py"

    controller_file.write_text(
        """
from flask import Flask

app = Flask(__name__)


@app.get("/users")
def get_users():
    return [], 200
""",
        encoding="utf-8",
    )

    output_file = tmp_path / "openapi.json"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "flask-ast-openapi",
            str(source_dir),
            "--output",
            str(output_file),
        ],
    )

    main()

    assert output_file.exists()

    spec = json.loads(
        output_file.read_text(
            encoding="utf-8"
        )
    )

    assert spec["openapi"] == "3.0.3"
    assert "/users" in spec["paths"]
    assert "get" in spec["paths"]["/users"]