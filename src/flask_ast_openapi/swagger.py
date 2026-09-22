"""Swagger UI integration for Flask applications."""

from functools import lru_cache
from pathlib import Path

from flask import Blueprint, Response, jsonify

from .generator import FlaskASTOpenAPI


_SWAGGER_UI_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title} - Swagger UI</title>

    <link
        rel="stylesheet"
        href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
    >
</head>

<body>
    <div id="swagger-ui"></div>

    <script
        src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js">
    </script>

    <script>
        window.onload = function() {{
            SwaggerUIBundle({{
                url: "{spec_url}",
                dom_id: "#swagger-ui",
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis
                ]
            }});
        }};
    </script>
</body>
</html>
"""


def create_swagger_blueprint(
    source_dir: str | Path,
    *,
    title: str = "Flask API",
    version: str = "1.0.0",
    docs_url: str = "/docs",
    spec_url: str = "/openapi.json",
    auth_decorator_names: set[str] | None = None,
    auth_scheme_mapping: dict[str, list[str]] | None = None,
    auth_scheme_modes: dict[str, str] | None = None,
    security_schemes: dict[str, dict] | None = None,
    excluded_dir_names: set[str] | None = None,
) -> Blueprint:
    """Create a Flask Blueprint serving OpenAPI JSON and Swagger UI."""

    source_path = Path(source_dir)

    swagger_bp = Blueprint(
        "flask_ast_openapi_swagger",
        __name__,
    )

    @lru_cache(maxsize=1)
    def get_spec() -> dict:
        generator = FlaskASTOpenAPI(
            source_path,
            auth_decorator_names=auth_decorator_names,
            auth_scheme_mapping=auth_scheme_mapping,
            auth_scheme_modes=auth_scheme_modes,
            security_schemes=security_schemes,
            excluded_dir_names=excluded_dir_names,
        )

        return generator.generate(
            title=title,
            version=version,
        )

    @swagger_bp.route(
        spec_url,
        methods=["GET"],
    )
    def openapi_spec():
        """Serve the generated OpenAPI specification."""

        return jsonify(
            get_spec()
        )

    @swagger_bp.route(
        docs_url,
        methods=["GET"],
    )
    def swagger_ui():
        """Serve Swagger UI."""

        html = _SWAGGER_UI_HTML_TEMPLATE.format(
            title=title,
            spec_url=spec_url,
        )

        return Response(
            html,
            mimetype="text/html",
        )

    return swagger_bp
