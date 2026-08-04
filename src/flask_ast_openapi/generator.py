"""Core OpenAPI generator."""

import ast
from pathlib import Path


class FlaskASTOpenAPI:
    """Generate OpenAPI documentation by analyzing Flask source code."""

    def __init__(self, source_dir: str | Path) -> None:
        self.source_dir = Path(source_dir)

    def parse_file(self, file_path: str | Path) -> ast.Module:
        """Read a Python file and convert it into an AST tree."""

        path = Path(file_path)
        source_code = path.read_text(encoding="utf-8")

        return ast.parse(
            source_code,
            filename=str(path),
        )