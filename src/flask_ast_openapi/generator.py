"""Core OpenAPI generator."""

import ast
from pathlib import Path
from dataclasses import dataclass, field
import re
from typing import Any
import json
@dataclass
class RouteDefinition:
    """Information extracted from a Flask route."""

    function_name: str
    path: str
    methods: list[str]
    query_parameter_names: list[str] = field(default_factory=list)
    uses_json_body: bool = False
    json_body_field_names: list[str] = field(default_factory=list)
    description: str | None = None
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
    def extract_routes(self,tree: ast.Module,) -> list[RouteDefinition]:
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
                        query_parameter_names=(
                            self.extract_query_parameter_names(function)
                        ),
                        uses_json_body=self.function_uses_json_body(
                            function
                        ),
                        json_body_field_names=(
                            self.extract_json_body_field_names(function)
                        ),
                        description=self.extract_function_description(
                            function
                        ),
                    )
                )

        return routes
    def convert_flask_path_to_openapi(self, path: str) -> str:
        """Convert Flask path parameters to OpenAPI format."""

        pattern = r"<(?:[^:<>]+:)?([^<>]+)>"

        return re.sub(pattern,r"{\1}",path,)
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

        parameters = self.build_openapi_path_parameters(route.path)

        parameters.extend(
            self.build_query_parameters_from_names(
                route.query_parameter_names
            )
        )

        operation: dict[str, Any] = {
            "operationId": route.function_name,
            "parameters": parameters,
            "responses": {
                "200": {
                    "description": "Successful response",
                }
            },
        }

        if route.uses_json_body:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": self.build_json_body_schema(
                            route.json_body_field_names
                        )
                    }
                },
            }

        if route.description:
            operation["description"] = route.description

        return operation
    def build_openapi_paths(self,routes: list[RouteDefinition],) -> dict[str, Any]:
        """Build the OpenAPI paths object."""

        paths: dict[str, Any] = {}

        for route in routes:
            openapi_path = self.convert_flask_path_to_openapi(
                route.path
            )

            path_item = paths.setdefault(openapi_path, {})

            for method in route.methods:
                operation = self.build_openapi_operation(route)

                if len(route.methods) > 1:
                    operation["operationId"] = (
                        f"{route.function_name}_{method.lower()}"
                    )

                path_item[method.lower()] = operation

        return paths
    def build_openapi_spec(self,routes: list[RouteDefinition],title: str = "Flask API",version: str = "1.0.0",) -> dict[str, Any]:
        """Build a complete OpenAPI specification."""

        return {
            "openapi": "3.0.3",
            "info": {
                "title": title,
                "version": version,
            },
            "paths": self.build_openapi_paths(routes),
        }
    def generate(self,title: str = "Flask API",version: str = "1.0.0",) -> dict[str, Any]:
        """Generate an OpenAPI specification from all Python source files."""

        routes: list[RouteDefinition] = []

        for file_path in self.discover_python_files():
            tree = self.parse_file(file_path)
            routes.extend(self.extract_routes(tree))

        return self.build_openapi_spec(
            routes,
            title=title,
            version=version,
        )
    def write_json(self,spec: dict[str, Any],output_path: str | Path,) -> Path:
        """Write an OpenAPI specification to a JSON file."""

        path = Path(output_path)

        path.write_text(
            json.dumps(
                spec,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return path
    def extract_query_parameter_names(self,function: ast.FunctionDef | ast.AsyncFunctionDef,) -> list[str]:
        """Extract query parameter names used with request.args.get."""

        parameter_names: list[str] = []

        for node in ast.walk(function):
            if not isinstance(node, ast.Call):
                continue

            if not isinstance(node.func, ast.Attribute):
                continue

            if node.func.attr != "get":
                continue

            args_attribute = node.func.value

            if not isinstance(args_attribute, ast.Attribute):
                continue

            if args_attribute.attr != "args":
                continue

            if not isinstance(args_attribute.value, ast.Name):
                continue

            if args_attribute.value.id != "request":
                continue

            if not node.args:
                continue

            first_argument = node.args[0]

            if not isinstance(first_argument, ast.Constant):
                continue

            if not isinstance(first_argument.value, str):
                continue

            parameter_names.append(first_argument.value)

        return parameter_names
    def build_openapi_query_parameters(self,function: ast.FunctionDef | ast.AsyncFunctionDef,) -> list[dict[str, Any]]:
        """Build OpenAPI query parameters from a route function."""

        parameters: list[dict[str, Any]] = []

        for name in self.extract_query_parameter_names(function):
            parameters.append(
                {
                    "name": name,
                    "in": "query",
                    "required": False,
                    "schema": {
                        "type": "string",
                    },
                }
            )

        return parameters
    def build_query_parameters_from_names(self,names: list[str],) -> list[dict[str, Any]]:
        """Build OpenAPI query parameters from their names."""

        return [
            {
                "name": name,
                "in": "query",
                "required": False,
                "schema": {
                    "type": "string",
                },
            }
            for name in names
        ]
    def function_uses_json_body(self,function: ast.FunctionDef | ast.AsyncFunctionDef,) -> bool:
        """Check whether a route function reads a JSON request body."""

        for node in ast.walk(function):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if (
                        isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "request"
                        and node.func.attr == "get_json"
                    ):
                        return True

            if isinstance(node, ast.Attribute):
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "request"
                    and node.attr == "json"
                ):
                    return True

        return False 
    def extract_json_body_field_names(self,function: ast.FunctionDef | ast.AsyncFunctionDef,) -> list[str]:
        """Extract JSON body field names used inside a route function."""

        json_variable_names: set[str] = set()
        field_names: list[str] = []

        for node in ast.walk(function):
            if not isinstance(node, ast.Assign):
                continue

            value = node.value

            uses_get_json = (
                isinstance(value, ast.Call)
                and isinstance(value.func, ast.Attribute)
                and isinstance(value.func.value, ast.Name)
                and value.func.value.id == "request"
                and value.func.attr == "get_json"
            )

            uses_request_json = (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and value.value.id == "request"
                and value.attr == "json"
            )

            if not uses_get_json and not uses_request_json:
                continue

            for target in node.targets:
                if isinstance(target, ast.Name):
                    json_variable_names.add(target.id)

        for node in ast.walk(function):
            if isinstance(node, ast.Call):
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "get"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in json_variable_names
                    and node.args
                ):
                    first_argument = node.args[0]

                    if (
                        isinstance(first_argument, ast.Constant)
                        and isinstance(first_argument.value, str)
                        and first_argument.value not in field_names
                    ):
                        field_names.append(first_argument.value)

            if isinstance(node, ast.Subscript):
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id in json_variable_names
                    and isinstance(node.slice, ast.Constant)
                    and isinstance(node.slice.value, str)
                    and node.slice.value not in field_names
                ):
                    field_names.append(node.slice.value)

        return field_names
    def build_json_body_schema(
        self,
        field_names: list[str],
    ) -> dict[str, Any]:
        """Build an OpenAPI schema for JSON body fields."""

        properties = {
            field_name: {
                "type": "string",
            }
            for field_name in field_names
        }

        return {
            "type": "object",
            "properties": properties,
        }
    def extract_function_description(self,function: ast.FunctionDef | ast.AsyncFunctionDef,) -> str | None:
        """Extract the docstring from a route function."""

        return ast.get_docstring(function)
    def is_http_method_decorator(self,decorator: ast.expr,) -> bool:
        """Check whether a decorator is a Flask HTTP method decorator."""

        if not isinstance(decorator, ast.Call):
            return False

        if not isinstance(decorator.func, ast.Attribute):
            return False

        supported_methods = {
            "get",
            "post",
            "put",
            "patch",
            "delete",
        }

        return decorator.func.attr in supported_methods
    def is_flask_route_decorator(self,decorator: ast.expr,) -> bool:
        """Check whether a decorator defines a Flask route."""

        return (
            self.is_route_decorator(decorator)
            or self.is_http_method_decorator(decorator)
        )