"""Core OpenAPI generator."""

import ast
from pathlib import Path
from dataclasses import dataclass
import re
from typing import Any
@dataclass
class RouteDefinition:
    """Information extracted from a Flask route."""

    function_name: str
    path: str
    methods: list[str]
@dataclass
class PathParameter:
    """A parameter extracted from a Flask route path."""

    name: str
    converter: str
class FlaskASTOpenAPI:
    """Generate OpenAPI documentation by analyzing Flask source code."""

    def __init__(self, source_dir: str | Path) -> None:
        self.source_dir = Path(source_dir)

    def discover_python_files(self) -> list[Path]:
        """Find all Python files inside the source directory."""

        return sorted(self.source_dir.rglob("*.py"))

    def parse_file(self, file_path: str | Path) -> ast.Module:
        """Read a Python file and convert it into an AST tree."""

        path = Path(file_path)
        source_code = path.read_text(encoding="utf-8")

        return ast.parse(
            source_code,
            filename=str(path),
        )

    def is_route_decorator(self, decorator: ast.expr) -> bool:
        """Check whether an AST decorator represents a Flask route."""

        if not isinstance(decorator, ast.Call):
            return False

        function = decorator.func

        if not isinstance(function, ast.Attribute):
            return False

        return function.attr == "route"
    def extract_route_path(self, decorator: ast.expr) -> str | None:
        """Extract the URL path from a Flask route decorator."""

        if not self.is_route_decorator(decorator):
            return None

        if not decorator.args:
            return None

        route_argument = decorator.args[0]

        if not isinstance(route_argument, ast.Constant):
            return None

        if not isinstance(route_argument.value, str):
            return None

        return route_argument.value
    def extract_http_methods(self, decorator: ast.expr) -> list[str]:
        """Extract HTTP methods from a Flask route decorator."""

        if not self.is_route_decorator(decorator):
            return []

        for keyword in decorator.keywords:
            if keyword.arg != "methods":
                continue

            methods_value = keyword.value

            if not isinstance(methods_value, (ast.List, ast.Tuple)):
                return ["GET"]

            methods: list[str] = []

            for element in methods_value.elts:
                if not isinstance(element, ast.Constant):
                    continue

                if not isinstance(element.value, str):
                    continue

                methods.append(element.value.upper())

            return methods or ["GET"]

        return ["GET"]
    
    def find_route_functions(
        self,
        tree: ast.Module,
    ) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        """Find Flask route functions in an AST module."""

        route_functions: list[
            ast.FunctionDef | ast.AsyncFunctionDef
        ] = []

        for node in tree.body:
            if not isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef),
            ):
                continue

            has_route_decorator = any(
                self.is_route_decorator(decorator)
                for decorator in node.decorator_list
            )

            if has_route_decorator:
                route_functions.append(node)

        return route_functions
    def extract_routes(self, tree: ast.Module) -> list[RouteDefinition]:
        """Extract route definitions from an AST module."""

        routes: list[RouteDefinition] = []

        for function in self.find_route_functions(tree):
            for decorator in function.decorator_list:
                if not self.is_route_decorator(decorator):
                    continue

                path = self.extract_route_path(decorator)

                if path is None:
                    continue

                routes.append(
                    RouteDefinition(
                        function_name=function.name,
                        path=path,
                        methods=self.extract_http_methods(decorator),
                    )
                )

        return routes
    def convert_flask_path_to_openapi(self, path: str) -> str:
        """Convert Flask path parameters to OpenAPI format."""

        pattern = r"<(?:[^:<>]+:)?([^<>]+)>"

        return re.sub(
            pattern,
            r"{\1}",
            path,
        )
    def extract_path_parameters(self, path: str) -> list[PathParameter]:
        """Extract path parameters from a Flask route."""

        pattern = r"<(?:(?P<converter>[^:<>]+):)?(?P<name>[^<>]+)>"

        parameters: list[PathParameter] = []

        for match in re.finditer(pattern, path):
            parameters.append(
                PathParameter(
                    name=match.group("name"),
                    converter=match.group("converter") or "string",
                )
            )

        return parameters
    def converter_to_openapi_schema(self,converter: str,) -> dict[str, str]:
        """Convert a Flask path converter to an OpenAPI schema."""

        schemas = {
            "int": {
                "type": "integer",
            },
            "float": {
                "type": "number",
                "format": "float",
            },
            "uuid": {
                "type": "string",
                "format": "uuid",
            },
            "path": {
                "type": "string",
            },
            "string": {
                "type": "string",
            },
        }

        return schemas.get(
            converter,
            {"type": "string"},
        )
    def build_openapi_path_parameters(self,path: str,) -> list[dict[str, Any]]:
        """Build OpenAPI parameter objects from a Flask route path."""

        openapi_parameters: list[dict[str, Any]] = []

        for parameter in self.extract_path_parameters(path):
            openapi_parameters.append(
                {
                    "name": parameter.name,
                    "in": "path",
                    "required": True,
                    "schema": self.converter_to_openapi_schema(
                        parameter.converter
                    ),
                }
            )

        return openapi_parameters
    def build_openapi_operation(
    self,
    route: RouteDefinition,
) -> dict[str, Any]:
        """Build an OpenAPI operation for a Flask route."""

        return {
            "operationId": route.function_name,
            "parameters": self.build_openapi_path_parameters(
                route.path
            ),
            "responses": {
                "200": {
                    "description": "Successful response",
                }
            },
        }