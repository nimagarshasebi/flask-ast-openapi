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