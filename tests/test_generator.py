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
                "description": "Successful response",
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
            "description": "Successful response",
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