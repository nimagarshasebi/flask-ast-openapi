import ast

from flask_ast_openapi.generator import FlaskASTOpenAPI, RouteDefinition
from flask_ast_openapi import FlaskASTOpenAPI as PublicFlaskASTOpenAPI
import json

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


def test_is_route_decorator_returns_true_for_flask_route(tmp_path):
    source_code = """
@app.route("/users")
def get_users():
    pass
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.is_route_decorator(decorator) is True



def test_is_route_decorator_returns_false_for_other_decorator(tmp_path):
    source_code = """
@require_auth
def get_users():
    pass
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.is_route_decorator(decorator) is False



def test_extract_route_path_returns_route_url(tmp_path):
    source_code = """
@app.route("/users")
def get_users():
    pass
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)
    route_path = generator.extract_route_path(decorator)

    assert route_path == "/users"



def test_extract_route_path_returns_none_for_non_route_decorator(tmp_path):
    source_code = """
@require_auth
def get_users():
    pass
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)
    route_path = generator.extract_route_path(decorator)

    assert route_path is None



def test_extract_route_path_returns_none_when_path_is_missing(tmp_path):
    source_code = """
@app.route()
def get_users():
    pass
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)
    route_path = generator.extract_route_path(decorator)

    assert route_path is None


def test_extract_http_methods_returns_multiple_methods(tmp_path):
    source_code = """
@app.route("/users", methods=["GET", "POST"])
def users():
    pass
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)
    methods = generator.extract_http_methods(decorator)

    assert methods == ["GET", "POST"]



def test_extract_http_methods_converts_methods_to_uppercase(tmp_path):
    source_code = """
@app.route("/users", methods=["get", "post"])
def users():
    pass
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)
    methods = generator.extract_http_methods(decorator)

    assert methods == ["GET", "POST"]



def test_extract_http_methods_returns_get_by_default(tmp_path):
    source_code = """
@app.route("/users")
def users():
    pass
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)
    methods = generator.extract_http_methods(decorator)

    assert methods == ["GET"]



def test_extract_http_methods_returns_empty_list_for_non_route(tmp_path):
    source_code = """
@require_auth
def users():
    pass
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)
    methods = generator.extract_http_methods(decorator)

    assert methods == []
def test_find_route_functions_returns_only_route_functions(tmp_path):
    source_code = """
@app.route("/users")
def get_users():
    pass


def helper():
    pass
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    route_functions = generator.find_route_functions(tree)

    assert len(route_functions) == 1
    assert route_functions[0].name == "get_users"


def test_find_route_functions_supports_async_routes(tmp_path):
    source_code = """
@app.route("/users")
async def get_users():
    pass
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    route_functions = generator.find_route_functions(tree)

    assert len(route_functions) == 1
    assert route_functions[0].name == "get_users"
    assert isinstance(route_functions[0], ast.AsyncFunctionDef)


def test_find_route_functions_returns_empty_list_when_no_routes(tmp_path):
    source_code = """
def helper():
    pass
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    route_functions = generator.find_route_functions(tree)

    assert route_functions == []
def test_extract_routes_returns_route_information(tmp_path):
    source_code = """
@app.route("/users", methods=["GET", "POST"])
def users():
    pass
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 1
    assert routes[0].function_name == "users"
    assert routes[0].path == "/users"
    assert routes[0].methods == ["GET", "POST"]


def test_extract_routes_returns_multiple_routes(tmp_path):
    source_code = """
@app.route("/users")
def get_users():
    pass


@app.route("/products", methods=["POST"])
def create_product():
    pass
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 2
    assert routes[0].path == "/users"
    assert routes[0].methods == ["GET"]

    assert routes[1].path == "/products"
    assert routes[1].methods == ["POST"]


def test_extract_routes_ignores_route_without_path(tmp_path):
    source_code = """
@app.route()
def users():
    pass
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert routes == []
def test_convert_flask_path_with_type_converter(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    result = generator.convert_flask_path_to_openapi(
        "/users/<int:user_id>"
    )

    assert result == "/users/{user_id}"


def test_convert_flask_path_without_type_converter(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    result = generator.convert_flask_path_to_openapi(
        "/products/<product_id>"
    )

    assert result == "/products/{product_id}"


def test_convert_flask_path_with_multiple_parameters(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    result = generator.convert_flask_path_to_openapi(
        "/users/<int:user_id>/posts/<string:post_id>"
    )

    assert result == "/users/{user_id}/posts/{post_id}"


def test_convert_flask_path_without_parameters(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    result = generator.convert_flask_path_to_openapi("/users")

    assert result == "/users"
def test_extract_path_parameters_with_converter(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    parameters = generator.extract_path_parameters(
        "/users/<int:user_id>"
    )

    assert len(parameters) == 1
    assert parameters[0].name == "user_id"
    assert parameters[0].converter == "int"


def test_extract_path_parameters_uses_string_by_default(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    parameters = generator.extract_path_parameters(
        "/products/<product_id>"
    )

    assert len(parameters) == 1
    assert parameters[0].name == "product_id"
    assert parameters[0].converter == "string"


def test_extract_path_parameters_returns_multiple_parameters(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    parameters = generator.extract_path_parameters(
        "/users/<int:user_id>/posts/<string:post_id>"
    )

    assert len(parameters) == 2

    assert parameters[0].name == "user_id"
    assert parameters[0].converter == "int"

    assert parameters[1].name == "post_id"
    assert parameters[1].converter == "string"


def test_extract_path_parameters_returns_empty_list(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    parameters = generator.extract_path_parameters("/users")

    assert parameters == []
def test_converter_to_openapi_schema_returns_integer(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.converter_to_openapi_schema("int")

    assert schema == {
        "type": "integer",
    }


def test_converter_to_openapi_schema_returns_float(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.converter_to_openapi_schema("float")

    assert schema == {
        "type": "number",
        "format": "float",
    }


def test_converter_to_openapi_schema_returns_uuid(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.converter_to_openapi_schema("uuid")

    assert schema == {
        "type": "string",
        "format": "uuid",
    }


def test_converter_to_openapi_schema_uses_string_for_unknown_converter(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.converter_to_openapi_schema("custom")

    assert schema == {
        "type": "string",
    }
def test_build_openapi_path_parameters_returns_integer_parameter(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    parameters = generator.build_openapi_path_parameters(
        "/users/<int:user_id>"
    )

    assert parameters == [
        {
            "name": "user_id",
            "in": "path",
            "required": True,
            "schema": {
                "type": "integer",
            },
        }
    ]


def test_build_openapi_path_parameters_returns_multiple_parameters(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    parameters = generator.build_openapi_path_parameters(
        "/users/<int:user_id>/posts/<uuid:post_id>"
    )

    assert parameters == [
        {
            "name": "user_id",
            "in": "path",
            "required": True,
            "schema": {
                "type": "integer",
            },
        },
        {
            "name": "post_id",
            "in": "path",
            "required": True,
            "schema": {
                "type": "string",
                "format": "uuid",
            },
        },
    ]


def test_build_openapi_path_parameters_returns_empty_list(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    parameters = generator.build_openapi_path_parameters("/users")

    assert parameters == []
def test_build_openapi_operation_returns_basic_operation(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    route = RouteDefinition(
        function_name="get_users",
        path="/users",
        methods=["GET"],
    )

    operation = generator.build_openapi_operation(route)

    assert operation == {
        "operationId": "get_users",
        "parameters": [],
        "responses": {
            "200": {
                "description": "HTTP 200 response",
            }
        },
    }


def test_build_openapi_operation_includes_path_parameters(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    route = RouteDefinition(
        function_name="get_user",
        path="/users/<int:user_id>",
        methods=["GET"],
    )

    operation = generator.build_openapi_operation(route)

    assert operation["operationId"] == "get_user"

    assert operation["parameters"] == [
        {
            "name": "user_id",
            "in": "path",
            "required": True,
            "schema": {
                "type": "integer",
            },
        }
    ]

    assert operation["responses"] == {
        "200": {
            "description": "HTTP 200 response",
        }
    }
def test_build_openapi_paths_creates_get_operation(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    routes = [
        RouteDefinition(
            function_name="get_user",
            path="/users/<int:user_id>",
            methods=["GET"],
        )
    ]

    paths = generator.build_openapi_paths(routes)

    assert "/users/{user_id}" in paths
    assert "get" in paths["/users/{user_id}"]

    assert (
        paths["/users/{user_id}"]["get"]["operationId"]
        == "get_user"
    )


def test_build_openapi_paths_supports_multiple_methods(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    routes = [
        RouteDefinition(
            function_name="users",
            path="/users",
            methods=["GET", "POST"],
        )
    ]

    paths = generator.build_openapi_paths(routes)

    assert "get" in paths["/users"]
    assert "post" in paths["/users"]

    assert paths["/users"]["get"]["operationId"] == "users_get"
    assert paths["/users"]["post"]["operationId"] == "users_post"


def test_build_openapi_paths_combines_same_path(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    routes = [
        RouteDefinition(
            function_name="get_users",
            path="/users",
            methods=["GET"],
        ),
        RouteDefinition(
            function_name="create_user",
            path="/users",
            methods=["POST"],
        ),
    ]

    paths = generator.build_openapi_paths(routes)

    assert len(paths) == 1
    assert "get" in paths["/users"]
    assert "post" in paths["/users"]
def test_build_openapi_paths_creates_get_operation(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    routes = [
        RouteDefinition(
            function_name="get_user",
            path="/users/<int:user_id>",
            methods=["GET"],
        )
    ]

    paths = generator.build_openapi_paths(routes)

    assert "/users/{user_id}" in paths
    assert "get" in paths["/users/{user_id}"]

    assert (
        paths["/users/{user_id}"]["get"]["operationId"]
        == "get_user"
    )


def test_build_openapi_paths_supports_multiple_methods(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    routes = [
        RouteDefinition(
            function_name="users",
            path="/users",
            methods=["GET", "POST"],
        )
    ]

    paths = generator.build_openapi_paths(routes)

    assert "get" in paths["/users"]
    assert "post" in paths["/users"]

    assert paths["/users"]["get"]["operationId"] == "users_get"
    assert paths["/users"]["post"]["operationId"] == "users_post"


def test_build_openapi_paths_combines_same_path(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    routes = [
        RouteDefinition(
            function_name="get_users",
            path="/users",
            methods=["GET"],
        ),
        RouteDefinition(
            function_name="create_user",
            path="/users",
            methods=["POST"],
        ),
    ]

    paths = generator.build_openapi_paths(routes)

    assert len(paths) == 1
    assert "get" in paths["/users"]
    assert "post" in paths["/users"]
def test_build_openapi_spec_returns_complete_spec(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    routes = [
        RouteDefinition(
            function_name="get_users",
            path="/users",
            methods=["GET"],
        )
    ]

    spec = generator.build_openapi_spec(
        routes,
        title="User API",
        version="1.0.0",
    )

    assert spec["openapi"] == "3.0.3"

    assert spec["info"] == {
        "title": "User API",
        "version": "1.0.0",
    }

    assert "/users" in spec["paths"]
    assert "get" in spec["paths"]["/users"]


def test_build_openapi_spec_uses_default_info(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    spec = generator.build_openapi_spec([])

    assert spec["info"] == {
        "title": "Flask API",
        "version": "1.0.0",
    }

    assert spec["paths"] == {}
def test_generate_builds_spec_from_python_files(tmp_path):
    app_file = tmp_path / "app.py"

    app_file.write_text(
        """
@app.route("/users", methods=["GET"])
def get_users():
    pass
""",
        encoding="utf-8",
    )

    generator = FlaskASTOpenAPI(tmp_path)

    spec = generator.generate(
        title="User API",
        version="2.0.0",
    )

    assert spec["openapi"] == "3.0.3"

    assert spec["info"] == {
        "title": "User API",
        "version": "2.0.0",
    }

    assert "/users" in spec["paths"]
    assert "get" in spec["paths"]["/users"]


def test_generate_collects_routes_from_multiple_files(tmp_path):
    users_file = tmp_path / "users.py"
    products_file = tmp_path / "products.py"

    users_file.write_text(
        """
@app.route("/users")
def get_users():
    pass
""",
        encoding="utf-8",
    )

    products_file.write_text(
        """
@app.route("/products", methods=["POST"])
def create_product():
    pass
""",
        encoding="utf-8",
    )

    generator = FlaskASTOpenAPI(tmp_path)
    spec = generator.generate()

    assert "get" in spec["paths"]["/users"]
    assert "post" in spec["paths"]["/products"]
def test_package_exports_flask_ast_openapi(tmp_path):
    generator = PublicFlaskASTOpenAPI(tmp_path)

    assert isinstance(generator, FlaskASTOpenAPI)
def test_write_json_creates_openapi_file(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "Test API",
            "version": "1.0.0",
        },
        "paths": {},
    }

    output_path = tmp_path / "openapi.json"

    result = generator.write_json(spec, output_path)

    assert result == output_path
    assert output_path.exists()

    saved_spec = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert saved_spec == spec


def test_write_json_preserves_unicode_text(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    spec = {
        "info": {
            "title": "رابط برنامه‌نویسی",
        }
    }

    output_path = tmp_path / "openapi.json"

    generator.write_json(spec, output_path)

    content = output_path.read_text(encoding="utf-8")

    assert "رابط برنامه‌نویسی" in content
def test_extract_query_parameter_names_returns_query_names(tmp_path):
    source_code = """
def get_users():
    page = request.args.get("page")
    search = request.args.get("search")
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    parameter_names = generator.extract_query_parameter_names(function)

    assert parameter_names == ["page", "search"]


def test_extract_query_parameter_names_ignores_other_get_calls(tmp_path):
    source_code = """
def get_users():
    value = data.get("name")
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    parameter_names = generator.extract_query_parameter_names(function)

    assert parameter_names == []


def test_extract_query_parameter_names_returns_empty_list(tmp_path):
    source_code = """
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    parameter_names = generator.extract_query_parameter_names(function)

    assert parameter_names == []
def test_build_openapi_query_parameters_returns_parameters(tmp_path):
    source_code = """
def get_users():
    page = request.args.get("page")
    search = request.args.get("search")
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    parameters = generator.build_openapi_query_parameters(function)

    assert parameters == [
        {
            "name": "page",
            "in": "query",
            "required": False,
            "schema": {
                "type": "string",
            },
        },
        {
            "name": "search",
            "in": "query",
            "required": False,
            "schema": {
                "type": "string",
            },
        },
    ]


def test_build_openapi_query_parameters_returns_empty_list(tmp_path):
    source_code = """
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    parameters = generator.build_openapi_query_parameters(function)

    assert parameters == []
def test_extract_routes_includes_query_parameter_names(tmp_path):
    source_code = """
@app.route("/users")
def get_users():
    page = request.args.get("page")
    search = request.args.get("search")
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 1
    assert routes[0].query_parameter_names == [
        "page",
        "search",
    ]


def test_build_openapi_operation_includes_query_parameters(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    route = RouteDefinition(
        function_name="get_users",
        path="/users",
        methods=["GET"],
        query_parameter_names=["page", "search"],
    )

    operation = generator.build_openapi_operation(route)

    assert operation["parameters"] == [
        {
            "name": "page",
            "in": "query",
            "required": False,
            "schema": {
                "type": "string",
            },
        },
        {
            "name": "search",
            "in": "query",
            "required": False,
            "schema": {
                "type": "string",
            },
        },
    ]


def test_build_openapi_operation_combines_path_and_query_parameters(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    route = RouteDefinition(
        function_name="get_user",
        path="/users/<int:user_id>",
        methods=["GET"],
        query_parameter_names=["detail"],
    )

    operation = generator.build_openapi_operation(route)

    assert operation["parameters"] == [
        {
            "name": "user_id",
            "in": "path",
            "required": True,
            "schema": {
                "type": "integer",
            },
        },
        {
            "name": "detail",
            "in": "query",
            "required": False,
            "schema": {
                "type": "string",
            },
        },
    ]
def test_function_uses_json_body_detects_get_json(tmp_path):
    source_code = """
def create_user():
    data = request.get_json()
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.function_uses_json_body(function) is True


def test_function_uses_json_body_detects_request_json(tmp_path):
    source_code = """
def create_user():
    data = request.json
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.function_uses_json_body(function) is True


def test_function_uses_json_body_returns_false_without_json(tmp_path):
    source_code = """
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.function_uses_json_body(function) is False
def test_extract_routes_detects_json_body(tmp_path):
    source_code = """
@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 1
    assert routes[0].uses_json_body is True


def test_build_openapi_operation_includes_json_request_body(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    route = RouteDefinition(
        function_name="create_user",
        path="/users",
        methods=["POST"],
        uses_json_body=True,
        json_body_field_names=["name", "email"],
    )

    operation = generator.build_openapi_operation(route)

    assert operation["requestBody"] == {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                        },
                        "email": {
                            "type": "string",
                        },
                    },
                }
            }
        },
    }
def test_build_openapi_operation_omits_request_body_when_unused(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    route = RouteDefinition(
        function_name="get_users",
        path="/users",
        methods=["GET"],
        uses_json_body=False,
    )

    operation = generator.build_openapi_operation(route)

    assert "requestBody" not in operation
def test_extract_json_body_field_names_from_get_calls(tmp_path):
    source_code = """
def create_user():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    field_names = generator.extract_json_body_field_names(function)

    assert field_names == ["name", "email"]


def test_extract_json_body_field_names_from_subscripts(tmp_path):
    source_code = """
def create_user():
    data = request.get_json()
    name = data["name"]
    email = data["email"]
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    field_names = generator.extract_json_body_field_names(function)

    assert field_names == ["name", "email"]


def test_extract_json_body_field_names_supports_request_json(tmp_path):
    source_code = """
def create_user():
    payload = request.json
    name = payload.get("name")
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    field_names = generator.extract_json_body_field_names(function)

    assert field_names == ["name"]


def test_extract_json_body_field_names_avoids_duplicates(tmp_path):
    source_code = """
def create_user():
    data = request.get_json()
    first_name = data.get("name")
    second_name = data["name"]
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    field_names = generator.extract_json_body_field_names(function)

    assert field_names == ["name"]


def test_extract_json_body_field_names_returns_empty_list_without_json(
    tmp_path,
):
    source_code = """
def get_users():
    name = query_data.get("name")
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    field_names = generator.extract_json_body_field_names(function)

    assert field_names == []
def test_build_json_body_schema_creates_properties(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.build_json_body_schema(
        ["name", "email"]
    )

    assert schema == {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
            },
            "email": {
                "type": "string",
            },
        },
    }


def test_build_json_body_schema_supports_empty_fields(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.build_json_body_schema([])

    assert schema == {
        "type": "object",
        "properties": {},
    }
def test_extract_routes_includes_json_body_field_names(tmp_path):
    source_code = """
@app.route("/users", methods=["POST"])
def create_user():
    data = request.get_json()
    name = data.get("name")
    email = data["email"]
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 1
    assert routes[0].uses_json_body is True
    assert routes[0].json_body_field_names == [
        "name",
        "email",
    ]
def test_extract_function_description_returns_docstring(tmp_path):
    source_code = '''
def get_users():
    """Return all registered users."""
    return []
'''

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    description = generator.extract_function_description(function)

    assert description == "Return all registered users."


def test_extract_function_description_returns_none_without_docstring(
    tmp_path,
):
    source_code = """
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)
    description = generator.extract_function_description(function)

    assert description is None
def test_extract_routes_includes_description(tmp_path):
    source_code = '''
@app.route("/users")
def get_users():
    """Return all registered users."""
    return []
'''

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 1
    assert routes[0].description == "Return all registered users."


def test_build_openapi_operation_includes_description(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    route = RouteDefinition(
        function_name="get_users",
        path="/users",
        methods=["GET"],
        description="Return all registered users.",
    )

    operation = generator.build_openapi_operation(route)

    assert operation["description"] == "Return all registered users."
def test_is_http_method_decorator_returns_true_for_get(tmp_path):
    source_code = """
@app.get("/users")
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.is_http_method_decorator(decorator) is True


def test_is_http_method_decorator_returns_true_for_post(tmp_path):
    source_code = """
@app.post("/users")
def create_user():
    return {}
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.is_http_method_decorator(decorator) is True


def test_is_http_method_decorator_returns_false_for_route(tmp_path):
    source_code = """
@app.route("/users")
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.is_http_method_decorator(decorator) is False


def test_is_http_method_decorator_returns_false_for_unsupported_method(
    tmp_path,
):
    source_code = """
@app.options("/users")
def users_options():
    return {}
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.is_http_method_decorator(decorator) is False
def test_is_flask_route_decorator_supports_route(tmp_path):
    source_code = """
@app.route("/users")
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.is_flask_route_decorator(decorator) is True


def test_is_flask_route_decorator_supports_get(tmp_path):
    source_code = """
@app.get("/users")
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.is_flask_route_decorator(decorator) is True


def test_is_flask_route_decorator_supports_post(tmp_path):
    source_code = """
@app.post("/users")
def create_user():
    return {}
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.is_flask_route_decorator(decorator) is True


def test_is_flask_route_decorator_rejects_unrelated_decorator(
    tmp_path,
):
    source_code = """
@staticmethod
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    function = tree.body[0]
    decorator = function.decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.is_flask_route_decorator(decorator) is False
def test_find_route_functions_supports_get_decorator(tmp_path):
    source_code = """
@app.get("/users")
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    functions = generator.find_route_functions(tree)

    assert len(functions) == 1
    assert functions[0].name == "get_users"


def test_find_route_functions_supports_post_decorator(tmp_path):
    source_code = """
@app.post("/users")
def create_user():
    return {}
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    functions = generator.find_route_functions(tree)

    assert len(functions) == 1
    assert functions[0].name == "create_user"


def test_find_route_functions_supports_async_method_decorator(
    tmp_path,
):
    source_code = """
@app.get("/users")
async def get_users():
    return []
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    functions = generator.find_route_functions(tree)

    assert len(functions) == 1
    assert functions[0].name == "get_users"
    assert isinstance(functions[0], ast.AsyncFunctionDef)


def test_find_route_functions_ignores_unrelated_decorators(
    tmp_path,
):
    source_code = """
@staticmethod
def helper():
    return None
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    functions = generator.find_route_functions(tree)

    assert functions == []
def test_extract_route_path_supports_blueprint_decorator(tmp_path):
    source_code = """
@users_bp.patch("/users/<int:user_id>")
def update_user(user_id):
    return {}
"""

    tree = ast.parse(source_code)
    decorator = tree.body[0].decorator_list[0]
    generator = FlaskASTOpenAPI(tmp_path)

    assert (
        generator.extract_route_path(decorator)
        == "/users/<int:user_id>"
    )
def test_extract_required_json_body_field_names_detects_subscript(
    tmp_path,
):
    source_code = """
def create_user():
    data = request.get_json()
    email = data["email"]
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    required_fields = (
        generator.extract_required_json_body_field_names(function)
    )

    assert required_fields == ["email"]


def test_extract_required_json_body_field_names_ignores_get(
    tmp_path,
):
    source_code = """
def create_user():
    data = request.get_json()
    name = data.get("name")
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    required_fields = (
        generator.extract_required_json_body_field_names(function)
    )

    assert required_fields == []


def test_extract_required_json_body_field_names_supports_request_json(
    tmp_path,
):
    source_code = """
def create_user():
    payload = request.json
    email = payload["email"]
    password = payload["password"]
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    required_fields = (
        generator.extract_required_json_body_field_names(function)
    )

    assert required_fields == [
        "email",
        "password",
    ]


def test_extract_required_json_body_field_names_removes_duplicates(
    tmp_path,
):
    source_code = """
def create_user():
    data = request.get_json()

    email = data["email"]

    if data["email"]:
        return data["email"]
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    required_fields = (
        generator.extract_required_json_body_field_names(function)
    )

    assert required_fields == ["email"]


def test_extract_required_json_body_field_names_ignores_unrelated_dict(
    tmp_path,
):
    source_code = """
def create_user():
    data = request.get_json()
    config = {"token": "abc"}

    email = data["email"]
    token = config["token"]
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    required_fields = (
        generator.extract_required_json_body_field_names(function)
    )

    assert required_fields == ["email"]


def test_extract_required_json_body_field_names_handles_mixed_fields(
    tmp_path,
):
    source_code = """
def create_user():
    data = request.get_json()

    name = data.get("name")
    email = data["email"]
    age = data.get("age")
    password = data["password"]
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    required_fields = (
        generator.extract_required_json_body_field_names(function)
    )

    assert required_fields == [
        "email",
        "password",
    ]


def test_extract_required_json_body_field_names_returns_empty_without_json(
    tmp_path,
):
    source_code = """
def get_users():
    page = request.args.get("page")
    return []
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    required_fields = (
        generator.extract_required_json_body_field_names(function)
    )

    assert required_fields == []
def test_build_json_body_schema_includes_required_fields(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.build_json_body_schema(
        field_names=["name", "email", "password"],
        required_field_names=["email", "password"],
    )

    assert schema == {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
            },
            "email": {
                "type": "string",
            },
            "password": {
                "type": "string",
            },
        },
        "required": [
            "email",
            "password",
        ],
    }


def test_build_json_body_schema_omits_empty_required_fields(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.build_json_body_schema(
        field_names=["name"],
        required_field_names=[],
    )

    assert schema == {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
            },
        },
    }


def test_extract_routes_includes_required_json_fields(tmp_path):
    source_code = """
@app.post("/users")
def create_user():
    data = request.get_json()

    name = data.get("name")
    email = data["email"]
    password = data["password"]

    return {}
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 1

    route = routes[0]

    assert route.json_body_field_names == [
        "name",
        "email",
        "password",
    ]

    assert route.required_json_body_field_names == [
        "email",
        "password",
    ]


def test_build_openapi_operation_includes_required_json_fields(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    route = RouteDefinition(
        function_name="create_user",
        path="/users",
        methods=["POST"],
        uses_json_body=True,
        json_body_field_names=[
            "name",
            "email",
            "password",
        ],
        required_json_body_field_names=[
            "email",
            "password",
        ],
    )

    operation = generator.build_openapi_operation(route)

    schema = operation["requestBody"]["content"][
        "application/json"
    ]["schema"]

    assert schema == {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
            },
            "email": {
                "type": "string",
            },
            "password": {
                "type": "string",
            },
        },
        "required": [
            "email",
            "password",
        ],
    }
def test_infer_openapi_schema_from_boolean(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Constant(value=False)

    assert generator.infer_openapi_schema_from_value(node) == {
        "type": "boolean",
    }


def test_infer_openapi_schema_from_integer(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Constant(value=42)

    assert generator.infer_openapi_schema_from_value(node) == {
        "type": "integer",
    }


def test_infer_openapi_schema_from_float(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Constant(value=3.14)

    assert generator.infer_openapi_schema_from_value(node) == {
        "type": "number",
        "format": "float",
    }


def test_infer_openapi_schema_from_string(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Constant(value="hello")

    assert generator.infer_openapi_schema_from_value(node) == {
        "type": "string",
    }


def test_infer_openapi_schema_from_list(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.List(
        elts=[],
        ctx=ast.Load(),
    )

    assert generator.infer_openapi_schema_from_value(node) == {
        "type": "array",
        "items": {},
    }


def test_infer_openapi_schema_from_tuple(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Tuple(
        elts=[],
        ctx=ast.Load(),
    )

    assert generator.infer_openapi_schema_from_value(node) == {
        "type": "array",
        "items": {},
    }


def test_infer_openapi_schema_from_set(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Set(elts=[])

    assert generator.infer_openapi_schema_from_value(node) == {
        "type": "array",
        "items": {},
    }


def test_infer_openapi_schema_from_dict(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Dict(
        keys=[],
        values=[],
    )

    assert generator.infer_openapi_schema_from_value(node) == {
        "type": "object",
    }


def test_infer_openapi_schema_defaults_to_string_for_unknown_node(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Name(
        id="some_variable",
        ctx=ast.Load(),
    )

    assert generator.infer_openapi_schema_from_value(node) == {
        "type": "string",
    }


def test_boolean_is_not_mistaken_for_integer(tmp_path):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Constant(value=True)

    schema = generator.infer_openapi_schema_from_value(node)

    assert schema["type"] == "boolean"
    assert schema["type"] != "integer"
def test_extract_json_body_field_schemas_infers_multiple_types(
    tmp_path,
):
    source_code = """
def create_user():
    data = request.get_json()

    name = data.get("name", "")
    age = data.get("age", 0)
    score = data.get("score", 0.0)
    active = data.get("active", False)
    tags = data.get("tags", [])
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_json_body_field_schemas(
        function
    )

    assert schemas == {
        "name": {
            "type": "string",
        },
        "age": {
            "type": "integer",
        },
        "score": {
            "type": "number",
            "format": "float",
        },
        "active": {
            "type": "boolean",
        },
        "tags": {
            "type": "array",
            "items": {},
        },
    }


def test_extract_json_body_field_schemas_supports_request_json(
    tmp_path,
):
    source_code = """
def create_user():
    payload = request.json

    name = payload.get("name", "")
    enabled = payload.get("enabled", True)
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_json_body_field_schemas(
        function
    )

    assert schemas == {
        "name": {
            "type": "string",
        },
        "enabled": {
            "type": "boolean",
        },
    }


def test_extract_json_body_field_schemas_defaults_to_string_without_default(
    tmp_path,
):
    source_code = """
def create_user():
    data = request.get_json()

    name = data.get("name")
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_json_body_field_schemas(
        function
    )

    assert schemas == {
        "name": {
            "type": "string",
        },
    }


def test_extract_json_body_field_schemas_supports_required_subscript(
    tmp_path,
):
    source_code = """
def create_user():
    data = request.get_json()

    email = data["email"]
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_json_body_field_schemas(
        function
    )

    assert schemas == {
        "email": {
            "type": "string",
        },
    }


def test_extract_json_body_field_schemas_does_not_override_inferred_type(
    tmp_path,
):
    source_code = """
def update_user():
    data = request.get_json()

    age = data.get("age", 0)

    if data["age"]:
        return data["age"]
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_json_body_field_schemas(
        function
    )

    assert schemas == {
        "age": {
            "type": "integer",
        },
    }


def test_extract_json_body_field_schemas_ignores_unrelated_dicts(
    tmp_path,
):
    source_code = """
def create_user():
    data = request.get_json()
    config = {}

    name = data.get("name", "")
    timeout = config.get("timeout", 30)
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_json_body_field_schemas(
        function
    )

    assert schemas == {
        "name": {
            "type": "string",
        },
    }


def test_extract_json_body_field_schemas_supports_object_default(
    tmp_path,
):
    source_code = """
def create_user():
    data = request.get_json()

    metadata = data.get("metadata", {})
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_json_body_field_schemas(
        function
    )

    assert schemas == {
        "metadata": {
            "type": "object",
        },
    }


def test_extract_json_body_field_schemas_returns_empty_without_json(
    tmp_path,
):
    source_code = """
def get_users():
    page = request.args.get("page", 1)
    return []
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_json_body_field_schemas(
        function
    )

    assert schemas == {}
def test_extract_routes_includes_json_body_field_schemas(
    tmp_path,
):
    source_code = """
@app.post("/users")
def create_user():
    data = request.get_json()

    name = data.get("name", "")
    age = data.get("age", 0)
    active = data.get("active", False)
    email = data["email"]

    return {}
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 1

    route = routes[0]

    assert route.json_body_field_schemas == {
        "name": {
            "type": "string",
        },
        "age": {
            "type": "integer",
        },
        "active": {
            "type": "boolean",
        },
        "email": {
            "type": "string",
        },
    }
def test_extract_routes_keeps_required_and_schema_information(
    tmp_path,
):
    source_code = """
@app.post("/users")
def create_user():
    data = request.get_json()

    name = data.get("name", "")
    age = data.get("age", 0)
    email = data["email"]

    return {}
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    route = routes[0]

    assert route.json_body_field_names == [
        "name",
        "age",
        "email",
    ]

    assert route.required_json_body_field_names == [
        "email",
    ]

    assert route.json_body_field_schemas == {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "email": {"type": "string"},
    }
def test_build_openapi_operation_uses_inferred_json_field_schemas(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    route = RouteDefinition(
        function_name="create_user",
        path="/users",
        methods=["POST"],
        uses_json_body=True,
        json_body_field_names=[
            "name",
            "age",
            "active",
            "email",
        ],
        required_json_body_field_names=[
            "email",
        ],
        json_body_field_schemas={
            "name": {
                "type": "string",
            },
            "age": {
                "type": "integer",
            },
            "active": {
                "type": "boolean",
            },
            "email": {
                "type": "string",
            },
        },
    )

    operation = generator.build_openapi_operation(route)

    schema = operation["requestBody"]["content"][
        "application/json"
    ]["schema"]

    assert schema == {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
            },
            "age": {
                "type": "integer",
            },
            "active": {
                "type": "boolean",
            },
            "email": {
                "type": "string",
            },
        },
        "required": [
            "email",
        ],
    }
def test_generate_includes_inferred_json_types(
    tmp_path,
):
    controller_file = tmp_path / "user_controller.py"

    controller_file.write_text(
        """
from flask import request


@app.post("/users")
def create_user():
    data = request.get_json()

    name = data.get("name", "")
    age = data.get("age", 0)
    score = data.get("score", 0.0)
    active = data.get("active", False)
    email = data["email"]

    return {}
""",
        encoding="utf-8",
    )

    generator = FlaskASTOpenAPI(tmp_path)

    spec = generator.generate()

    schema = spec["paths"]["/users"]["post"][
        "requestBody"
    ]["content"]["application/json"]["schema"]

    assert schema == {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
            },
            "age": {
                "type": "integer",
            },
            "score": {
                "type": "number",
                "format": "float",
            },
            "active": {
                "type": "boolean",
            },
            "email": {
                "type": "string",
            },
        },
        "required": [
            "email",
        ],
    }
def test_extract_response_status_codes_detects_single_status(
    tmp_path,
):
    source_code = """
def create_user():
    return {"message": "created"}, 201
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    status_codes = generator.extract_response_status_codes(
        function
    )

    assert status_codes == [201]


def test_extract_response_status_codes_detects_multiple_statuses(
    tmp_path,
):
    source_code = """
def get_user():
    if not found:
        return {"error": "not found"}, 404

    return {"user": user}, 200
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    status_codes = generator.extract_response_status_codes(
        function
    )

    assert status_codes == [
        404,
        200,
    ]


def test_extract_response_status_codes_removes_duplicates(
    tmp_path,
):
    source_code = """
def update_user():
    if not found:
        return {"error": "not found"}, 404

    if not allowed:
        return {"error": "forbidden"}, 404

    return {"message": "updated"}, 200
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    status_codes = generator.extract_response_status_codes(
        function
    )

    assert status_codes == [
        404,
        200,
    ]


def test_extract_response_status_codes_supports_jsonify(
    tmp_path,
):
    source_code = """
def create_user():
    return jsonify({"message": "created"}), 201
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    status_codes = generator.extract_response_status_codes(
        function
    )

    assert status_codes == [201]


def test_extract_response_status_codes_ignores_return_without_status(
    tmp_path,
):
    source_code = """
def get_users():
    return {"users": []}
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    status_codes = generator.extract_response_status_codes(
        function
    )

    assert status_codes == []


def test_extract_response_status_codes_detects_multiple_statuses(
    tmp_path,
):
    source_code = """
def get_user():
    if not found:
        return {"error": "not found"}, 404

    return {"user": user}, 200
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    status_codes = generator.extract_response_status_codes(
        function
    )

    assert set(status_codes) == {
        404,
        200,
    }
def test_extract_response_status_codes_removes_duplicates(
    tmp_path,
):
    source_code = """
def update_user():
    if not found:
        return {"error": "not found"}, 404

    if not allowed:
        return {"error": "forbidden"}, 404

    return {"message": "updated"}, 200
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    status_codes = generator.extract_response_status_codes(
        function
    )

    assert set(status_codes) == {
        404,
        200,
    }

    assert len(status_codes) == 2
def test_extract_routes_includes_response_status_codes(
    tmp_path,
):
    source_code = """
@app.post("/users")
def create_user():
    if invalid:
        return {"error": "invalid"}, 400

    if conflict:
        return {"error": "conflict"}, 409

    return {"message": "created"}, 201
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 1

    route = routes[0]

    assert set(route.response_status_codes) == {
        201,
        400,
        409,
    }
def test_extract_routes_has_empty_response_status_codes_without_explicit_status(
    tmp_path,
):
    source_code = """
@app.get("/users")
def get_users():
    return {"users": []}
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 1
    assert routes[0].response_status_codes == []
def test_build_openapi_responses_uses_detected_status_codes(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    responses = generator.build_openapi_responses(
        [201, 400, 409]
    )

    assert responses == {
        "201": {
            "description": "HTTP 201 response",
        },
        "400": {
            "description": "HTTP 400 response",
        },
        "409": {
            "description": "HTTP 409 response",
        },
    }


def test_build_openapi_responses_defaults_to_200(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    responses = generator.build_openapi_responses([])

    assert responses == {
        "200": {
            "description": "HTTP 200 response",
        },
    }


def test_build_openapi_operation_uses_route_response_status_codes(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    route = RouteDefinition(
        function_name="create_user",
        path="/users",
        methods=["POST"],
        response_status_codes=[
            201,
            400,
        ],
    )

    operation = generator.build_openapi_operation(route)

    assert operation["responses"] == {
        "201": {
            "description": "HTTP 201 response",
        },
        "400": {
            "description": "HTTP 400 response",
        },
    }


def test_generate_includes_detected_response_status_codes(
    tmp_path,
):
    controller_file = tmp_path / "user_controller.py"

    controller_file.write_text(
        """
@app.post("/users")
def create_user():
    if invalid:
        return {"error": "invalid"}, 400

    return {"message": "created"}, 201
""",
        encoding="utf-8",
    )

    generator = FlaskASTOpenAPI(tmp_path)

    spec = generator.generate()

    responses = spec["paths"]["/users"]["post"]["responses"]

    assert set(responses.keys()) == {
        "201",
        "400",
    }
def test_infer_openapi_schema_from_expression_detects_string(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Constant(value="hello")

    assert generator.infer_openapi_schema_from_expression(node) == {
        "type": "string",
    }


def test_infer_openapi_schema_from_expression_detects_integer(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Constant(value=42)

    assert generator.infer_openapi_schema_from_expression(node) == {
        "type": "integer",
    }


def test_infer_openapi_schema_from_expression_detects_boolean(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Constant(value=True)

    assert generator.infer_openapi_schema_from_expression(node) == {
        "type": "boolean",
    }


def test_infer_openapi_schema_from_expression_detects_float(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Constant(value=3.14)

    assert generator.infer_openapi_schema_from_expression(node) == {
        "type": "number",
        "format": "float",
    }


def test_infer_openapi_schema_from_expression_detects_none(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Constant(value=None)

    assert generator.infer_openapi_schema_from_expression(node) == {
        "nullable": True,
    }


def test_infer_openapi_schema_from_expression_detects_object(
    tmp_path,
):
    source_code = """
value = {
    "id": 1,
    "name": "Nima",
    "active": True,
}
"""

    tree = ast.parse(source_code)
    assignment = tree.body[0]
    node = assignment.value

    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.infer_openapi_schema_from_expression(
        node
    )

    assert schema == {
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
            },
            "name": {
                "type": "string",
            },
            "active": {
                "type": "boolean",
            },
        },
    }


def test_infer_openapi_schema_from_expression_detects_nested_object(
    tmp_path,
):
    source_code = """
value = {
    "user": {
        "id": 1,
        "name": "Nima",
    },
    "success": True,
}
"""

    tree = ast.parse(source_code)
    node = tree.body[0].value

    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.infer_openapi_schema_from_expression(
        node
    )

    assert schema == {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                    },
                    "name": {
                        "type": "string",
                    },
                },
            },
            "success": {
                "type": "boolean",
            },
        },
    }


def test_infer_openapi_schema_from_expression_detects_array(
    tmp_path,
):
    source_code = """
value = [1, 2, 3]
"""

    tree = ast.parse(source_code)
    node = tree.body[0].value

    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.infer_openapi_schema_from_expression(
        node
    )

    assert schema == {
        "type": "array",
        "items": {
            "type": "integer",
        },
    }


def test_infer_openapi_schema_from_expression_detects_array_of_objects(
    tmp_path,
):
    source_code = """
value = [
    {
        "id": 1,
        "name": "Nima",
    }
]
"""

    tree = ast.parse(source_code)
    node = tree.body[0].value

    generator = FlaskASTOpenAPI(tmp_path)

    schema = generator.infer_openapi_schema_from_expression(
        node
    )

    assert schema == {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                },
                "name": {
                    "type": "string",
                },
            },
        },
    }


def test_infer_openapi_schema_from_expression_returns_empty_for_unknown_expression(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    node = ast.Name(
        id="user",
        ctx=ast.Load(),
    )

    assert generator.infer_openapi_schema_from_expression(node) == {}
def test_extract_response_schemas_detects_default_200(
    tmp_path,
):
    source_code = """
def get_user():
    return {
        "id": 1,
        "name": "Nima",
    }
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_response_schemas(function)

    assert schemas == {
        200: {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                },
                "name": {
                    "type": "string",
                },
            },
        },
    }


def test_extract_response_schemas_detects_explicit_status_code(
    tmp_path,
):
    source_code = """
def create_user():
    return {
        "id": 1,
        "created": True,
    }, 201
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_response_schemas(function)

    assert schemas == {
        201: {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                },
                "created": {
                    "type": "boolean",
                },
            },
        },
    }


def test_extract_response_schemas_supports_jsonify(
    tmp_path,
):
    source_code = """
def create_user():
    return jsonify({
        "message": "created",
        "id": 1,
    }), 201
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_response_schemas(function)

    assert schemas == {
        201: {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                },
                "id": {
                    "type": "integer",
                },
            },
        },
    }


def test_extract_response_schemas_detects_multiple_status_codes(
    tmp_path,
):
    source_code = """
def get_user():
    if not found:
        return {
            "error": "not found",
        }, 404

    return {
        "id": 1,
        "name": "Nima",
    }, 200
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_response_schemas(function)

    assert set(schemas.keys()) == {
        200,
        404,
    }

    assert schemas[404] == {
        "type": "object",
        "properties": {
            "error": {
                "type": "string",
            },
        },
    }

    assert schemas[200] == {
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
            },
            "name": {
                "type": "string",
            },
        },
    }


def test_extract_response_schemas_detects_nested_response(
    tmp_path,
):
    source_code = """
def get_user():
    return {
        "user": {
            "id": 1,
            "name": "Nima",
        },
        "success": True,
    }, 200
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_response_schemas(function)

    assert schemas[200] == {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                    },
                    "name": {
                        "type": "string",
                    },
                },
            },
            "success": {
                "type": "boolean",
            },
        },
    }


def test_extract_response_schemas_detects_array_response(
    tmp_path,
):
    source_code = """
def get_users():
    return [
        {
            "id": 1,
            "name": "Nima",
        }
    ], 200
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_response_schemas(function)

    assert schemas[200] == {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                },
                "name": {
                    "type": "string",
                },
            },
        },
    }


def test_extract_response_schemas_ignores_dynamic_response(
    tmp_path,
):
    source_code = """
def get_user():
    result = build_response()
    return result, 200
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_response_schemas(function)

    assert schemas == {}


def test_extract_response_schemas_ignores_dynamic_status_code(
    tmp_path,
):
    source_code = """
def get_user():
    status_code = 201

    return {
        "message": "created",
    }, status_code
"""

    tree = ast.parse(source_code)
    function = tree.body[0]

    generator = FlaskASTOpenAPI(tmp_path)

    schemas = generator.extract_response_schemas(function)

    assert schemas == {
        200: {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                },
            },
        },
    }
def test_extract_routes_includes_response_schemas(
    tmp_path,
):
    source_code = """
@app.get("/users/<int:user_id>")
def get_user(user_id):
    if not found:
        return {
            "error": "not found",
        }, 404

    return {
        "id": 1,
        "name": "Nima",
        "active": True,
    }, 200
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 1

    route = routes[0]

    assert set(route.response_schemas.keys()) == {
        200,
        404,
    }

    assert route.response_schemas[200] == {
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
            },
            "name": {
                "type": "string",
            },
            "active": {
                "type": "boolean",
            },
        },
    }

    assert route.response_schemas[404] == {
        "type": "object",
        "properties": {
            "error": {
                "type": "string",
            },
        },
    }
def test_extract_routes_has_empty_response_schemas_for_dynamic_response(
    tmp_path,
):
    source_code = """
@app.get("/users")
def get_users():
    result = load_users()
    return result
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    routes = generator.extract_routes(tree)

    assert len(routes) == 1
    assert routes[0].response_schemas == {}
def test_build_openapi_responses_includes_schema(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    responses = generator.build_openapi_responses(
        status_codes=[200],
        response_schemas={
            200: {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                    },
                    "name": {
                        "type": "string",
                    },
                },
            }
        },
    )

    assert responses == {
        "200": {
            "description": "HTTP 200 response",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "integer",
                            },
                            "name": {
                                "type": "string",
                            },
                        },
                    }
                }
            },
        }
    }
def test_build_openapi_responses_supports_multiple_schemas(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    responses = generator.build_openapi_responses(
        status_codes=[
            200,
            404,
        ],
        response_schemas={
            200: {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                    },
                },
            },
            404: {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "string",
                    },
                },
            },
        },
    )

    assert responses["200"]["content"][
        "application/json"
    ]["schema"] == {
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
            },
        },
    }

    assert responses["404"]["content"][
        "application/json"
    ]["schema"] == {
        "type": "object",
        "properties": {
            "error": {
                "type": "string",
            },
        },
    }
def test_generate_includes_response_body_schema(
    tmp_path,
):
    controller_file = tmp_path / "user_controller.py"

    controller_file.write_text(
        """
@app.get("/users/<int:user_id>")
def get_user(user_id):
    if not found:
        return {
            "error": "not found",
        }, 404

    return {
        "id": 1,
        "name": "Nima",
        "active": True,
    }, 200
""",
        encoding="utf-8",
    )

    generator = FlaskASTOpenAPI(tmp_path)

    spec = generator.generate()

    responses = spec["paths"][
        "/users/{user_id}"
    ]["get"]["responses"]

    assert responses["200"]["content"][
        "application/json"
    ]["schema"] == {
        "type": "object",
        "properties": {
            "id": {
                "type": "integer",
            },
            "name": {
                "type": "string",
            },
            "active": {
                "type": "boolean",
            },
        },
    }

    assert responses["404"]["content"][
        "application/json"
    ]["schema"] == {
        "type": "object",
        "properties": {
            "error": {
                "type": "string",
            },
        },
    }
def test_extract_blueprint_prefixes_detects_single_blueprint(
    tmp_path,
):
    source_code = """
users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/users",
)
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    prefixes = generator.extract_blueprint_prefixes(tree)

    assert prefixes == {
        "users_bp": "/api/users",
    }


def test_extract_blueprint_prefixes_supports_multiple_blueprints(
    tmp_path,
):
    source_code = """
users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/users",
)

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/admin",
)
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    prefixes = generator.extract_blueprint_prefixes(tree)

    assert prefixes == {
        "users_bp": "/api/users",
        "admin_bp": "/api/admin",
    }


def test_extract_blueprint_prefixes_defaults_to_empty_prefix(
    tmp_path,
):
    source_code = """
health_bp = Blueprint(
    "health",
    __name__,
)
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    prefixes = generator.extract_blueprint_prefixes(tree)

    assert prefixes == {
        "health_bp": "",
    }


def test_extract_blueprint_prefixes_ignores_unrelated_assignments(
    tmp_path,
):
    source_code = """
name = "users"

value = create_something()

users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/users",
)
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    prefixes = generator.extract_blueprint_prefixes(tree)

    assert prefixes == {
        "users_bp": "/api/users",
    }


def test_extract_blueprint_prefixes_ignores_dynamic_prefix(
    tmp_path,
):
    source_code = """
API_PREFIX = "/api/users"

users_bp = Blueprint(
    "users",
    __name__,
    url_prefix=API_PREFIX,
)
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    prefixes = generator.extract_blueprint_prefixes(tree)

    assert prefixes == {
        "users_bp": "",
    }


def test_extract_blueprint_prefixes_ignores_attribute_based_blueprint_call(
    tmp_path,
):
    source_code = """
users_bp = flask.Blueprint(
    "users",
    __name__,
    url_prefix="/api/users",
)
"""

    tree = ast.parse(source_code)
    generator = FlaskASTOpenAPI(tmp_path)

    prefixes = generator.extract_blueprint_prefixes(tree)

    assert prefixes == {}
def test_extract_decorator_owner_detects_app(
    tmp_path,
):
    source_code = """
@app.get("/health")
def health():
    return {}
"""

    tree = ast.parse(source_code)
    decorator = tree.body[0].decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.extract_decorator_owner(decorator) == "app"


def test_extract_decorator_owner_detects_blueprint(
    tmp_path,
):
    source_code = """
@users_bp.post("/users")
def create_user():
    return {}
"""

    tree = ast.parse(source_code)
    decorator = tree.body[0].decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert (
        generator.extract_decorator_owner(decorator)
        == "users_bp"
    )


def test_extract_decorator_owner_supports_route_decorator(
    tmp_path,
):
    source_code = """
@users_bp.route("/users", methods=["GET"])
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    decorator = tree.body[0].decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert (
        generator.extract_decorator_owner(decorator)
        == "users_bp"
    )


def test_extract_decorator_owner_returns_none_for_unrelated_decorator(
    tmp_path,
):
    source_code = """
@staticmethod
def helper():
    return None
"""

    tree = ast.parse(source_code)
    decorator = tree.body[0].decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.extract_decorator_owner(decorator) is None


def test_extract_decorator_owner_returns_none_for_nested_owner(
    tmp_path,
):
    source_code = """
@api.users.get("/users")
def get_users():
    return []
"""

    tree = ast.parse(source_code)
    decorator = tree.body[0].decorator_list[0]

    generator = FlaskASTOpenAPI(tmp_path)

    assert generator.extract_decorator_owner(decorator) is None
def test_combine_url_prefix_and_path_combines_normal_values(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    result = generator.combine_url_prefix_and_path(
        "/api/users",
        "/<int:user_id>",
    )

    assert result == "/api/users/<int:user_id>"


def test_combine_url_prefix_and_path_removes_duplicate_slashes(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    result = generator.combine_url_prefix_and_path(
        "/api/users/",
        "/create",
    )

    assert result == "/api/users/create"


def test_combine_url_prefix_and_path_supports_empty_prefix(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    result = generator.combine_url_prefix_and_path(
        "",
        "/health",
    )

    assert result == "/health"


def test_combine_url_prefix_and_path_supports_path_without_leading_slash(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    result = generator.combine_url_prefix_and_path(
        "/api",
        "users",
    )

    assert result == "/api/users"


def test_combine_url_prefix_and_path_supports_empty_path(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    result = generator.combine_url_prefix_and_path(
        "/api/users",
        "",
    )

    assert result == "/api/users"


def test_combine_url_prefix_and_path_supports_root_path(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    result = generator.combine_url_prefix_and_path(
        "/api/users",
        "/",
    )

    assert result == "/api/users"


def test_combine_url_prefix_and_path_handles_empty_prefix_and_path(
    tmp_path,
):
    generator = FlaskASTOpenAPI(tmp_path)

    result = generator.combine_url_prefix_and_path(
        "",
        "",
    )

    assert result == "/"