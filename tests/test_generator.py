import ast

from flask_ast_openapi.generator import FlaskASTOpenAPI


def test_parse_file_returns_ast_module(tmp_path):
    source_file = tmp_path / "sample.py"

    source_file.write_text(
        'def hello():\n    return "Hello"\n',
        encoding="utf-8",
    )

    generator = FlaskASTOpenAPI(tmp_path)
    tree = generator.parse_file(source_file)

    assert isinstance(tree, ast.Module)