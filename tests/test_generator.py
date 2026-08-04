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


    
def test_discover_python_files_finds_nested_python_files(tmp_path):
    controllers_dir = tmp_path / "controllers"
    controllers_dir.mkdir()

    app_file = tmp_path / "app.py"
    controller_file = controllers_dir / "user_controller.py"
    text_file = tmp_path / "README.txt"

    app_file.write_text("", encoding="utf-8")
    controller_file.write_text("", encoding="utf-8")
    text_file.write_text("", encoding="utf-8")

    generator = FlaskASTOpenAPI(tmp_path)
    discovered_files = generator.discover_python_files()

    assert set(discovered_files) == {
        app_file,
        controller_file,
    }