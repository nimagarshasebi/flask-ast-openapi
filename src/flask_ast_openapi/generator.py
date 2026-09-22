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
    required_json_body_field_names: list[str] = field(
        default_factory=list
    )
    json_body_field_schemas: dict[
        str,
        dict[str, Any],
    ] = field(default_factory=dict)
    response_status_codes: list[int] = field(default_factory=list)
    response_schemas: dict[
        int,
        dict[str, Any],
    ] = field(default_factory=dict)
    requires_auth: bool = False
    auth_schemes: list[str] = field(default_factory=list)
    auth_scheme_mode: str = "and"
    description: str | None = None
    request_schema: dict[str, Any] | None = None
    response_schema: dict[str, Any] | None = None
    request_content_type: str | None = "application/json"
    response_content_type: str = "application/json"
    tag: str | None = None
@dataclass
class PathParameter:
    """A parameter extracted from a Flask route path."""

    name: str
    converter: str
class FlaskASTOpenAPI:
    """Generate OpenAPI documentation by analyzing Flask source code."""
    DEFAULT_AUTH_DECORATORS = {
        "require_auth",
        "jwt_required",
        "login_required",
    }
    DEFAULT_EXCLUDED_DIRS = {
        ".git",
        ".pytest_cache",
        ".venv",
        "__pycache__",
        "test",
        "tests",
        "venv",
    }
    def __init__(
    self,
    source_dir: str | Path,
    auth_decorator_names: set[str] | None = None,
    auth_scheme_mapping: dict[str, list[str]] | None = None,
    security_schemes: dict[str, dict[str, Any]] | None = None,
    auth_scheme_modes: dict[str, str] | None = None,
    excluded_dir_names: set[str] | None = None,
) -> None:
        self.source_dir = Path(source_dir)

        self.auth_decorator_names = (
            auth_decorator_names
            if auth_decorator_names is not None
            else self.DEFAULT_AUTH_DECORATORS.copy()
        )

        self.auth_scheme_mapping = (
            auth_scheme_mapping
            if auth_scheme_mapping is not None
            else {
                "require_auth": ["BearerAuth"],
                "jwt_required": ["BearerAuth"],
                "login_required": ["BearerAuth"],
            }
        )

        self.security_schemes = (
            security_schemes
            if security_schemes is not None
            else {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            }
        )
        self.auth_scheme_modes = (
            auth_scheme_modes
            if auth_scheme_modes is not None
            else {}
        )
        self._schema_registry: dict[str, ast.ClassDef] = {}
        self._blueprint_prefixes: dict[str, str] = {}
        self._blueprint_tags: dict[str, str] = {}
        self.excluded_dir_names = (
            excluded_dir_names
            if excluded_dir_names is not None
            else self.DEFAULT_EXCLUDED_DIRS.copy()
        )
    def discover_python_files(self) -> list[Path]:
        """Find all Python files inside the source directory."""

        return sorted(
            path
            for path in self.source_dir.rglob("*.py")
            if not any(
                part in self.excluded_dir_names
                for part in path.relative_to(self.source_dir).parts[:-1]
            )
        )

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
    def extract_route_path(
    self,
    decorator: ast.expr,
) -> str | None:
        """Extract the path from a Flask route decorator."""

        if not self.is_flask_route_decorator(decorator):
            return None

        if not isinstance(decorator, ast.Call):
            return None

        if not decorator.args:
            return None

        route_argument = decorator.args[0]

        if not isinstance(route_argument, ast.Constant):
            return None

        if not isinstance(route_argument.value, str):
            return None

        return route_argument.value
    def extract_http_methods(
        self,
        decorator: ast.expr,
    ) -> list[str]:
        """Extract HTTP methods from a Flask route decorator."""

        if not self.is_flask_route_decorator(decorator):
            return []

        if not isinstance(decorator, ast.Call):
            return []

        if self.is_http_method_decorator(decorator):
            method_name = decorator.func.attr
            return [method_name.upper()]

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
    def find_route_functions(self,tree: ast.Module,) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        """Find functions decorated as Flask routes."""

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
                self.is_flask_route_decorator(decorator)
                for decorator in node.decorator_list
            )

            if has_route_decorator:
                route_functions.append(node)

        return route_functions
    def extract_routes(
        self,
        tree: ast.Module,
    ) -> list[RouteDefinition]:
        """Extract route definitions from an AST module."""

        routes: list[RouteDefinition] = []

        blueprint_prefixes = {
            **self.extract_blueprint_prefixes(tree),
            **self._blueprint_prefixes,
        }

        for function in self.find_route_functions(tree):
            auth_decorator_name = self.extract_auth_decorator_name(
                function
            )

            auth_scheme_mode = "and"

            if auth_decorator_name is not None:
                auth_scheme_mode = self.get_auth_scheme_mode(
                    auth_decorator_name
                )

            for decorator in function.decorator_list:
                if not self.is_flask_route_decorator(decorator):
                    continue

                path = self.extract_route_path(decorator)

                if path is None:
                    continue

                owner = self.extract_decorator_owner(decorator)

                if owner in blueprint_prefixes:
                    path = self.combine_url_prefix_and_path(
                        blueprint_prefixes[owner],
                        path,
                    )

                routes.append(
                    RouteDefinition(
                        function_name=function.name,
                        path=path,
                        methods=self.extract_http_methods(
                            decorator
                        ),
                        query_parameter_names=(
                            self.extract_query_parameter_names(
                                function
                            )
                        ),
                        request_schema=self.build_request_schema_from_docstring(
                            tree,
                            function,
                        ),
                        request_content_type=(
                            self.extract_request_content_type(function)
                        ),
                        response_content_type=(
                            self.extract_response_content_type(function)
                        ),
                        uses_json_body=(
                            self.function_uses_json_body(
                                function
                            )
                        ),
                        json_body_field_names=(
                            self.extract_json_body_field_names(
                                function
                            )
                        ),
                        required_json_body_field_names=(
                            self.extract_required_json_body_field_names(
                                function
                            )
                        ),
                        json_body_field_schemas=(
                            self.extract_json_body_field_schemas(
                                function
                            )
                        ),
                        response_status_codes=(
                            self.extract_response_status_codes(
                                function
                            )
                        ),
                        response_schemas=(
                            self.extract_response_schemas(
                                function
                            )
                        ),
                        requires_auth=(
                            self.function_has_auth_decorator(
                                function,
                                self.auth_decorator_names,
                            )
                        ),
                        auth_schemes=(
                            self.extract_auth_schemes(
                                function
                            )
                        ),
                        auth_scheme_mode=auth_scheme_mode,
                        description=(
                            self.extract_function_description(
                                function
                            )
                        ),
                        response_schema=(
                            self.build_response_schema_from_docstring(
                                tree,
                                function,
                            )
                        ),
                        tag=self._blueprint_tags.get(owner),
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

        parameters = self.build_openapi_path_parameters(
            route.path
        )

        parameters.extend(
            self.build_query_parameters_from_names(
                route.query_parameter_names,
                route.request_schema,
            )
        )
        response_status_codes = list(
            route.response_status_codes
        )

        response_schemas = dict(
            route.response_schemas
        )

        if route.response_schema is not None:
            success_status_code = self.find_success_status_code(
                response_status_codes
            )

            response_schemas[
                success_status_code
            ] = route.response_schema

            if success_status_code not in response_status_codes:
                response_status_codes.append(
                    success_status_code
                )
        operation: dict[str, Any] = {
            "operationId": route.function_name,
            "parameters": parameters,
            "responses": self.build_openapi_responses(
                response_status_codes,
                response_schemas,
                route.response_content_type,
            ),
        }

        if route.tag:
            operation["tags"] = [route.tag]

        if (
            route.request_content_type is not None
            and (route.uses_json_body or route.request_schema is not None)
        ):
            request_schema = route.request_schema

            if request_schema is None:
                request_schema = self.build_json_body_schema(
                    route.json_body_field_names,
                    route.required_json_body_field_names,
                    route.json_body_field_schemas,
                )

            operation["requestBody"] = {
                "required": True,
                "content": {
                    route.request_content_type: {
                        "schema": request_schema,
                    }
                },
        }

        if route.description:
            operation["description"] = route.description

        if route.requires_auth and route.auth_schemes:
            if route.auth_scheme_mode == "or":
                operation["security"] = [
                    {
                        scheme_name: [],
                    }
                    for scheme_name in route.auth_schemes
                ]
            else:
                operation["security"] = [
                    {
                        scheme_name: []
                        for scheme_name in route.auth_schemes
                    }
                ]

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
    def build_openapi_spec(
    self,
    routes: list[RouteDefinition],
    title: str = "Flask API",
    version: str = "1.0.0",
    schemas: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
        """Build the complete OpenAPI specification."""

        components: dict[str, Any] = {
            "securitySchemes": self.build_security_schemes(),
        }

        if schemas:
            components["schemas"] = schemas

        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": title,
                "version": version,
            },
            "components": components,
            "paths": self.build_openapi_paths(routes),
        }

        tags = sorted({route.tag for route in routes if route.tag})
        if tags:
            spec["tags"] = [{"name": tag} for tag in tags]

        return spec

    def expression_name(self, node: ast.expr) -> str | None:
        """Return the final name from a Name or Attribute expression."""

        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            return node.attr

        return None

    def index_project(self, trees: list[ast.Module]) -> None:
        """Index schemas and resolve Blueprint registration chains."""

        blueprint_defaults: dict[str, str] = {}
        registrations: list[tuple[str, str, str | None]] = []

        self._schema_registry = {}
        self._blueprint_prefixes = {}
        self._blueprint_tags = {}

        for tree in trees:
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    self._schema_registry[node.name] = node

                if not isinstance(node, ast.Assign):
                    continue

                if not isinstance(node.value, ast.Call):
                    continue

                call = node.value
                if not isinstance(call.func, ast.Name):
                    continue

                if call.func.id != "Blueprint":
                    continue

                prefix = ""
                for keyword in call.keywords:
                    if (
                        keyword.arg == "url_prefix"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, str)
                    ):
                        prefix = keyword.value.value

                blueprint_name: str | None = None
                if (
                    call.args
                    and isinstance(call.args[0], ast.Constant)
                    and isinstance(call.args[0].value, str)
                ):
                    blueprint_name = call.args[0].value

                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    blueprint_defaults[target.id] = prefix
                    tag_name = blueprint_name or target.id.removesuffix("_bp")
                    self._blueprint_tags[target.id] = (
                        tag_name.replace("_", " ").title()
                    )

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr != "register_blueprint" or not node.args:
                    continue

                parent = self.expression_name(node.func.value)
                child = self.expression_name(node.args[0])
                if parent is None or child is None:
                    continue

                registration_prefix: str | None = None
                for keyword in node.keywords:
                    if (
                        keyword.arg == "url_prefix"
                        and isinstance(keyword.value, ast.Constant)
                        and isinstance(keyword.value.value, str)
                    ):
                        registration_prefix = keyword.value.value

                registrations.append((parent, child, registration_prefix))

        unresolved = list(registrations)
        for _ in range(len(unresolved) + 1):
            next_unresolved: list[tuple[str, str, str | None]] = []
            changed = False

            for parent, child, registration_prefix in unresolved:
                if parent in blueprint_defaults and parent not in self._blueprint_prefixes:
                    next_unresolved.append((parent, child, registration_prefix))
                    continue

                parent_prefix = self._blueprint_prefixes.get(parent, "")
                child_prefix = (
                    registration_prefix
                    if registration_prefix is not None
                    else blueprint_defaults.get(child, "")
                )
                self._blueprint_prefixes[child] = self.combine_url_prefix_and_path(
                    parent_prefix,
                    child_prefix,
                )
                changed = True

            unresolved = next_unresolved
            if not unresolved or not changed:
                break

        for blueprint, prefix in blueprint_defaults.items():
            self._blueprint_prefixes.setdefault(blueprint, prefix)
    def generate(
        self,
        title: str = "Flask API",
        version: str = "1.0.0",
    ) -> dict[str, Any]:
            """Generate an OpenAPI specification."""

            routes: list[RouteDefinition] = []
            schemas: dict[str, dict[str, Any]] = {}
            trees = [
                self.parse_file(file_path)
                for file_path in self.discover_python_files()
            ]

            self.index_project(trees)

            for tree in trees:

                routes.extend(
                    self.extract_routes(tree)
                )

                schemas.update(
                    self.extract_marshmallow_schema_components(
                        tree
                    )
                )

            return self.build_openapi_spec(
                routes,
                title=title,
                version=version,
                schemas=schemas,
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
    def build_query_parameters_from_names(
        self,
        names: list[str],
        request_schema: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Build OpenAPI query parameters from their names."""

        schema_properties = (
            request_schema.get("properties", {})
            if request_schema
            else {}
        )
        required_names = set(
            request_schema.get("required", [])
            if request_schema
            else []
        )

        return [
            {
                "name": name,
                "in": "query",
                "required": name in required_names,
                "schema": schema_properties.get(name, {"type": "string"}),
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

    def function_uses_multipart_body(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> bool:
        """Check whether a route reads form fields or uploaded files."""

        for node in ast.walk(function):
            if not isinstance(node, ast.Attribute):
                continue

            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "request"
                and node.attr in {"form", "files"}
            ):
                return True

        return False

    def extract_docstring_directive(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
        directive: str,
    ) -> str | None:
        """Extract a named ``:directive: value`` from a docstring."""

        docstring = ast.get_docstring(function)
        if not docstring:
            return None

        match = re.search(
            rf"^\s*:{re.escape(directive)}:\s*([^\s]+)",
            docstring,
            re.MULTILINE,
        )
        return match.group(1) if match else None

    def extract_request_content_type(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> str | None:
        """Infer request body media type, allowing a docstring override."""

        explicit = self.extract_docstring_directive(
            function,
            "request-content-type",
        )
        if explicit:
            return explicit

        if self.function_uses_multipart_body(function):
            return "multipart/form-data"

        if self.function_uses_json_body(function):
            return "application/json"

        return None

    def extract_response_content_type(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> str:
        """Return the declared response media type or JSON by default."""

        return (
            self.extract_docstring_directive(
                function,
                "response-content-type",
            )
            or "application/json"
        )
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
    def build_json_body_schema(self,field_names: list[str],required_field_names: list[str] | None = None,field_schemas: dict[str, dict[str, Any]] | None = None,) -> dict[str, Any]:
        """Build an OpenAPI schema for JSON body fields."""

        properties: dict[str, Any] = {}

        for field_name in field_names:
            if field_schemas and field_name in field_schemas:
                properties[field_name] = field_schemas[field_name]
            else:
                properties[field_name] = {
                    "type": "string",
                }

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }

        if required_field_names:
            schema["required"] = required_field_names

        return schema
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
    def extract_required_json_body_field_names(
    self,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
        """Extract required JSON fields accessed with dictionary subscripts."""

        json_variable_names: set[str] = set()
        required_field_names: list[str] = []

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
            if not isinstance(node, ast.Subscript):
                continue

            if not isinstance(node.value, ast.Name):
                continue

            if node.value.id not in json_variable_names:
                continue

            if not isinstance(node.slice, ast.Constant):
                continue

            if not isinstance(node.slice.value, str):
                continue

            field_name = node.slice.value

            if field_name not in required_field_names:
                required_field_names.append(field_name)

        return required_field_names
    def infer_openapi_schema_from_value(self,value: ast.expr,) -> dict[str, Any]:
        """Infer an OpenAPI schema from an AST value."""

        if isinstance(value, ast.Constant):
            if isinstance(value.value, bool):
                return {"type": "boolean"}

            if isinstance(value.value, int):
                return {"type": "integer"}

            if isinstance(value.value, float):
                return {
                    "type": "number",
                    "format": "float",
                }

            if isinstance(value.value, str):
                return {"type": "string"}

        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            return {
                "type": "array",
                "items": {},
            }

        if isinstance(value, ast.Dict):
            return {"type": "object"}

        return {"type": "string"}
    def extract_json_body_field_schemas(self,function: ast.FunctionDef | ast.AsyncFunctionDef,) -> dict[str, dict[str, Any]]:
        """Extract JSON body field schemas from default values."""

        json_variable_names: set[str] = set()
        field_schemas: dict[str, dict[str, Any]] = {}

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
            if not isinstance(node, ast.Call):
                continue

            if not isinstance(node.func, ast.Attribute):
                continue

            if node.func.attr != "get":
                continue

            if not isinstance(node.func.value, ast.Name):
                continue

            if node.func.value.id not in json_variable_names:
                continue

            if not node.args:
                continue

            field_node = node.args[0]

            if not (
                isinstance(field_node, ast.Constant)
                and isinstance(field_node.value, str)
            ):
                continue

            field_name = field_node.value

            if len(node.args) >= 2:
                field_schemas[field_name] = (
                    self.infer_openapi_schema_from_value(
                        node.args[1]
                    )
                )
            else:
                field_schemas[field_name] = {
                    "type": "string",
                }

        for node in ast.walk(function):
            if not isinstance(node, ast.Subscript):
                continue

            if not isinstance(node.value, ast.Name):
                continue

            if node.value.id not in json_variable_names:
                continue

            if not isinstance(node.slice, ast.Constant):
                continue

            if not isinstance(node.slice.value, str):
                continue

            field_name = node.slice.value

            field_schemas.setdefault(
                field_name,
                {
                    "type": "string",
                },
            )

        return field_schemas
    def extract_response_status_codes(
    self,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[int]:
        """Extract HTTP status codes from route return statements."""

        status_codes: list[int] = []

        for node in ast.walk(function):
            if not isinstance(node, ast.Return):
                continue

            if not isinstance(node.value, ast.Tuple):
                continue

            if len(node.value.elts) < 2:
                continue

            status_node = node.value.elts[1]

            if not isinstance(status_node, ast.Constant):
                continue

            if not isinstance(status_node.value, int):
                continue

            status_code = status_node.value

            if status_code not in status_codes:
                status_codes.append(status_code)

        return status_codes
    def build_openapi_responses(
        self,
        status_codes: list[int],
        response_schemas: dict[int, dict[str, Any]] | None = None,
        content_type: str = "application/json",
) -> dict[str, Any]:
        """Build OpenAPI responses from status codes and schemas."""

        response_schemas = response_schemas or {}

        effective_status_codes = (
            status_codes
            or list(response_schemas.keys())
            or [200]
        )

        responses: dict[str, Any] = {}

        for status_code in effective_status_codes:
            response: dict[str, Any] = {
                "description": f"HTTP {status_code} response",
            }

            schema = response_schemas.get(status_code)

            if schema:
                response["content"] = {
                    content_type: {
                        "schema": schema,
                    }
                }

            responses[str(status_code)] = response

        return responses
    def infer_openapi_schema_from_expression(
    self,
    value: ast.expr,
) -> dict[str, Any]:
        """Infer an OpenAPI schema from an AST expression."""

        if isinstance(value, ast.Constant):
            if isinstance(value.value, bool):
                return {"type": "boolean"}

            if isinstance(value.value, int):
                return {"type": "integer"}

            if isinstance(value.value, float):
                return {
                    "type": "number",
                    "format": "float",
                }

            if isinstance(value.value, str):
                return {"type": "string"}

            if value.value is None:
                return {"nullable": True}

        if isinstance(value, ast.List):
            item_schema: dict[str, Any] = {}

            if value.elts:
                item_schema = self.infer_openapi_schema_from_expression(
                    value.elts[0]
                )

            return {
                "type": "array",
                "items": item_schema,
            }

        if isinstance(value, ast.Tuple):
            return {
                "type": "array",
                "items": {},
            }

        if isinstance(value, ast.Dict):
            properties: dict[str, Any] = {}

            for key, item_value in zip(
                value.keys,
                value.values,
            ):
                if not isinstance(key, ast.Constant):
                    continue

                if not isinstance(key.value, str):
                    continue

                properties[key.value] = (
                    self.infer_openapi_schema_from_expression(
                        item_value
                    )
                )

            return {
                "type": "object",
                "properties": properties,
            }

        return {}
    def extract_response_schemas(
    self,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[int, dict[str, Any]]:
        """Extract response schemas grouped by HTTP status code."""

        response_schemas: dict[int, dict[str, Any]] = {}

        for node in ast.walk(function):
            if not isinstance(node, ast.Return):
                continue

            if node.value is None:
                continue

            response_value = node.value
            status_code = 200

            if isinstance(node.value, ast.Tuple):
                if not node.value.elts:
                    continue

                response_value = node.value.elts[0]

                if len(node.value.elts) >= 2:
                    status_node = node.value.elts[1]

                    if (
                        isinstance(status_node, ast.Constant)
                        and isinstance(status_node.value, int)
                    ):
                        status_code = status_node.value

            if (
                isinstance(response_value, ast.Call)
                and isinstance(response_value.func, ast.Name)
                and response_value.func.id == "jsonify"
            ):
                if not response_value.args:
                    continue

                response_value = response_value.args[0]

            schema = self.infer_openapi_schema_from_expression(
                response_value
            )

            if not schema:
                continue

            response_schemas.setdefault(
                status_code,
                schema,
            )

        return response_schemas
    def extract_blueprint_prefixes(
    self,
    tree: ast.Module,
) -> dict[str, str]:
        """Extract Blueprint variable names and URL prefixes."""

        prefixes: dict[str, str] = {}

        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue

            if not isinstance(node.value, ast.Call):
                continue

            call = node.value

            if not isinstance(call.func, ast.Name):
                continue

            if call.func.id != "Blueprint":
                continue

            prefix = ""

            for keyword in call.keywords:
                if keyword.arg != "url_prefix":
                    continue

                if (
                    isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, str)
                ):
                    prefix = keyword.value.value

            for target in node.targets:
                if isinstance(target, ast.Name):
                    prefixes[target.id] = prefix

        return prefixes
    def extract_decorator_owner(
    self,
    decorator: ast.expr,
) -> str | None:
        """Extract the object name used by a Flask route decorator."""

        if not isinstance(decorator, ast.Call):
            return None

        if not isinstance(decorator.func, ast.Attribute):
            return None

        owner = decorator.func.value

        if not isinstance(owner, ast.Name):
            return None

        return owner.id
    def combine_url_prefix_and_path(
    self,
    prefix: str,
    path: str,
) -> str:
        """Combine a Blueprint URL prefix with a route path."""

        normalized_prefix = prefix.rstrip("/")
        normalized_path = path.lstrip("/")

        if not normalized_prefix:
            return f"/{normalized_path}"

        if not normalized_path:
            return normalized_prefix or "/"

        return f"{normalized_prefix}/{normalized_path}"

    def function_has_auth_decorator(
    self,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    auth_decorator_names: set[str],
) -> bool:
        """Check whether a route function uses an authentication decorator."""

        for decorator in function.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id in auth_decorator_names:
                    return True

            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    if decorator.func.id in auth_decorator_names:
                        return True

        return False
    def build_security_schemes(
        self,
    ) -> dict[str, dict[str, Any]]:
        """Build configured OpenAPI security schemes."""

        return self.security_schemes
    def extract_auth_schemes(
    self,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
        """Extract security scheme names from authentication decorators."""

        schemes: list[str] = []

        for decorator in function.decorator_list:
            decorator_name: str | None = None

            if isinstance(decorator, ast.Name):
                decorator_name = decorator.id

            elif (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Name)
            ):
                decorator_name = decorator.func.id

            if decorator_name is None:
                continue

            mapped_schemes = self.auth_scheme_mapping.get(
                decorator_name,
                [],
            )

            for scheme in mapped_schemes:
                if scheme not in schemes:
                    schemes.append(scheme)

        return schemes
    def get_auth_scheme_mode(
    self,
    decorator_name: str,
) -> str:
        """Return the configured security mode for an auth decorator."""

        mode = self.auth_scheme_modes.get(
            decorator_name,
            "and",
        ).lower()

        if mode not in {"and", "or"}:
            raise ValueError(
                f"Invalid auth scheme mode: {mode}"
            )

        return mode
    def extract_auth_decorator_name(
    self,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str | None:
        """Extract the first configured authentication decorator name."""

        for decorator in function.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id in self.auth_decorator_names:
                    return decorator.id

            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Name)
            ):
                if decorator.func.id in self.auth_decorator_names:
                    return decorator.func.id

        return None
    def extract_request_schema_name(
    self,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str | None:
        """Extract a request schema name from the function docstring."""

        docstring = ast.get_docstring(function)

        if not docstring:
            return None

        match = re.search(
            r"^\s*:request:\s*(\w+)",
            docstring,
            re.MULTILINE,
        )

        if match is None:
            return None

        return match.group(1)
    def extract_response_schema_name(
    self,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> str | None:
        """Extract a response schema name from the function docstring."""

        docstring = ast.get_docstring(function)

        if not docstring:
            return None

        match = re.search(
            r"^\s*:response:\s*(\w+)",
            docstring,
            re.MULTILINE,
        )

        if match is None:
            return None

        return match.group(1)
    def find_schema_class(
    self,
    tree: ast.Module,
    schema_name: str,
) -> ast.ClassDef | None:
        """Find a schema class by name in an AST module."""

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue

            if node.name == schema_name:
                return node

        return self._schema_registry.get(schema_name)
    def extract_marshmallow_fields(
        self,
        schema_class: ast.ClassDef,
    ) -> dict[str, dict[str, Any]]:
        """Extract Marshmallow field definitions from a schema class."""

        extracted_fields: dict[str, dict[str, Any]] = {}

        for node in schema_class.body:
            if not isinstance(node, ast.Assign):
                continue

            if len(node.targets) != 1:
                continue

            target = node.targets[0]

            if not isinstance(target, ast.Name):
                continue

            if not isinstance(node.value, ast.Call):
                continue

            if not isinstance(node.value.func, ast.Attribute):
                continue

            field_type = node.value.func.attr

            required = False
            item_type: str | None = None
            nested_schema: str | None = None
            item_nested_schema: str | None = None

            for keyword in node.value.keywords:
                if keyword.arg != "required":
                    continue

                if (
                    isinstance(keyword.value, ast.Constant)
                    and isinstance(keyword.value.value, bool)
                ):
                    required = keyword.value.value

            if field_type == "List" and node.value.args:
                inner_field = node.value.args[0]

                if (
                    isinstance(inner_field, ast.Call)
                    and isinstance(inner_field.func, ast.Attribute)
                ):
                    item_type = inner_field.func.attr

                    if item_type == "Nested" and inner_field.args:
                        nested_argument = inner_field.args[0]

                        if isinstance(nested_argument, ast.Name):
                            item_nested_schema = nested_argument.id
            if field_type == "Nested" and node.value.args:
                nested_argument = node.value.args[0]

                if isinstance(nested_argument, ast.Name):
                    nested_schema = nested_argument.id

            field_info: dict[str, Any] = {
                "field_type": field_type,
                "required": required,
            }

            if item_type is not None:
                field_info["item_type"] = item_type
            if item_nested_schema is not None:
                field_info["item_nested_schema"] = item_nested_schema

            if nested_schema is not None:
                field_info["nested_schema"] = nested_schema

            extracted_fields[target.id] = field_info

        return extracted_fields
    def marshmallow_field_type_to_openapi_schema(
    self,
    field_type: str,
) -> dict[str, Any]:
        """Convert a Marshmallow field type to an OpenAPI schema."""

        schemas: dict[str, dict[str, Any]] = {
            "String": {
                "type": "string",
            },
            "Integer": {
                "type": "integer",
            },
            "Float": {
                "type": "number",
                "format": "float",
            },
            "Boolean": {
                "type": "boolean",
            },
            "DateTime": {
                "type": "string",
                "format": "date-time",
            },
            "Date": {
                "type": "string",
                "format": "date",
            },
            "UUID": {
                "type": "string",
                "format": "uuid",
            },
            "Dict": {
                "type": "object",
            },
            "List": {
                "type": "array",
                "items": {},
            },
            "Raw": {},
        }

        return schemas.get(
            field_type,
            {
                "type": "string",
            },
        )
    def build_openapi_schema_from_marshmallow_fields(
    self,
    extracted_fields: dict[str, dict[str, Any]],
) -> dict[str, Any]:
        """Build an OpenAPI object schema from Marshmallow fields."""

        properties: dict[str, Any] = {}
        required_fields: list[str] = []

        for field_name, field_info in extracted_fields.items():
            field_type = field_info["field_type"]

            if field_type == "Nested":
                nested_schema = field_info.get("nested_schema")

                if nested_schema is not None:
                    field_schema = {
                        "$ref": f"#/components/schemas/{nested_schema}",
                    }
                else:
                    field_schema = {
                        "type": "object",
                    }

            elif field_type == "List":
                item_type = field_info.get("item_type")

                field_schema = {
                    "type": "array",
                    "items": {},
                }

                if item_type == "Nested":
                    nested_schema = field_info.get(
                        "item_nested_schema"
                    )

                    if nested_schema is not None:
                        field_schema["items"] = {
                            "$ref": (
                                "#/components/schemas/"
                                f"{nested_schema}"
                            ),
                        }

                elif item_type is not None:
                    field_schema["items"] = (
                        self.marshmallow_field_type_to_openapi_schema(
                            item_type
                        )
                    )

            else:
                field_schema = (
                    self.marshmallow_field_type_to_openapi_schema(
                        field_type
                    )
                )

            properties[field_name] = field_schema

            if field_info.get("required"):
                required_fields.append(field_name)

        schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }

        if required_fields:
            schema["required"] = required_fields

        return schema
    def build_request_schema_from_docstring(
    self,
    tree: ast.Module,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, Any] | None:
        """Build a request schema from a docstring-referenced Marshmallow schema."""

        schema_name = self.extract_request_schema_name(
            function
        )

        if schema_name is None:
            return None

        schema_class = self.find_schema_class(
            tree,
            schema_name,
        )

        if schema_class is None:
            return None

        extracted_fields = self.extract_marshmallow_fields(
            schema_class
        )

        return self.build_openapi_schema_from_marshmallow_fields(
            extracted_fields
        )

        return None
    def build_response_schema_from_docstring(
    self,
    tree: ast.Module,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, Any] | None:
        """Build a response schema from a docstring-referenced Marshmallow schema."""

        schema_name = self.extract_response_schema_name(
            function
        )

        if schema_name is None:
            return None

        schema_class = self.find_schema_class(
            tree,
            schema_name,
        )

        if schema_class is None:
            return None

        extracted_fields = self.extract_marshmallow_fields(
            schema_class
        )

        return self.build_openapi_schema_from_marshmallow_fields(
            extracted_fields
        )
    def find_success_status_code(
    self,
    status_codes: list[int],
) -> int:
        """Find the primary successful HTTP status code."""

        for status_code in status_codes:
            if 200 <= status_code < 300:
                return status_code

        return 200
    def extract_marshmallow_schema_components(
    self,
    tree: ast.Module,
) -> dict[str, dict[str, Any]]:
        """Extract Marshmallow schemas as OpenAPI components."""

        schemas: dict[str, dict[str, Any]] = {}

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue

            is_schema = False

            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Schema":
                    is_schema = True

                elif (
                    isinstance(base, ast.Attribute)
                    and base.attr == "Schema"
                ):
                    is_schema = True

            if not is_schema:
                continue

            extracted_fields = self.extract_marshmallow_fields(
                node
            )

            schemas[node.name] = (
                self.build_openapi_schema_from_marshmallow_fields(
                    extracted_fields
                )
            )

        return schemas
