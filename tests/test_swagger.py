from flask import Flask

from flask_ast_openapi.swagger import create_swagger_blueprint
from flask import Flask

from flask_ast_openapi.swagger import create_swagger_blueprint
def test_swagger_blueprint_serves_openapi_json(
    tmp_path,
):
    controller_file = tmp_path / "app.py"

    controller_file.write_text(
        """
from flask import Flask

app = Flask(__name__)


@app.get("/health")
def health():
    return {"status": "ok"}, 200
""",
        encoding="utf-8",
    )

    app = Flask(__name__)

    swagger_bp = create_swagger_blueprint(
        tmp_path,
        title="Test API",
        version="1.0.0",
    )

    app.register_blueprint(swagger_bp)

    client = app.test_client()

    response = client.get(
        "/openapi.json"
    )

    assert response.status_code == 200

    spec = response.get_json()

    assert spec["openapi"] == "3.0.3"
    assert spec["info"]["title"] == "Test API"
    assert spec["info"]["version"] == "1.0.0"
    assert "/health" in spec["paths"]
def test_swagger_blueprint_serves_swagger_ui(
    tmp_path,
):
    app = Flask(__name__)

    swagger_bp = create_swagger_blueprint(
        tmp_path,
        title="Test API",
    )

    app.register_blueprint(swagger_bp)

    client = app.test_client()

    response = client.get(
        "/docs"
    )

    assert response.status_code == 200
    assert response.mimetype == "text/html"

    html = response.get_data(
        as_text=True
    )

    assert "SwaggerUIBundle" in html
    assert "/openapi.json" in html
    assert "Test API" in html
def test_swagger_blueprint_supports_custom_urls(
    tmp_path,
):
    app = Flask(__name__)

    swagger_bp = create_swagger_blueprint(
        tmp_path,
        docs_url="/api/docs",
        spec_url="/api/openapi.json",
    )

    app.register_blueprint(swagger_bp)

    client = app.test_client()

    docs_response = client.get(
        "/api/docs"
    )

    spec_response = client.get(
        "/api/openapi.json"
    )

    assert docs_response.status_code == 200
    assert spec_response.status_code == 200
def test_swagger_blueprint_supports_multiple_auth_schemes_with_or_mode(
    tmp_path,
):
    controller_file = tmp_path / "controller.py"

    controller_file.write_text(
        """
from flask import Flask

app = Flask(__name__)


@app.get("/protected")
@require_auth
def protected():
    return {"status": "ok"}, 200
""",
        encoding="utf-8",
    )

    app = Flask(__name__)

    swagger_bp = create_swagger_blueprint(
        tmp_path,
        auth_decorator_names={
            "require_auth",
        },
        auth_scheme_mapping={
            "require_auth": [
                "BearerAuth",
                "ApiTokenAuth",
            ],
        },
        auth_scheme_modes={
            "require_auth": "or",
        },
        security_schemes={
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            },
            "ApiTokenAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Api-Token",
            },
        },
    )

    app.register_blueprint(swagger_bp)

    client = app.test_client()

    response = client.get("/openapi.json")

    assert response.status_code == 200

    spec = response.get_json()

    assert spec["components"]["securitySchemes"] == {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
        "ApiTokenAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Api-Token",
        },
    }

    assert spec["paths"]["/protected"]["get"]["security"] == [
        {
            "BearerAuth": [],
        },
        {
            "ApiTokenAuth": [],
        },
    ]