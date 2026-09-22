# flask-ast-openapi

Generate OpenAPI 3 specifications from Flask source code using Python's Abstract Syntax Tree (AST).

`flask-ast-openapi` statically analyzes Flask source files without importing or executing the application. It discovers routes, request parameters, response structures, Marshmallow schemas, authentication requirements, Blueprint prefixes, and other API metadata, then generates an OpenAPI 3.0.3 specification.

It also provides optional Swagger UI integration for Flask applications.

## Features

* Static Flask source-code analysis using Python AST
* No need to run or import the target Flask application
* Recursive Python file discovery
* Flask route detection
* Flask shorthand route detection:

  * `@app.get(...)`
  * `@app.post(...)`
  * `@app.put(...)`
  * `@app.patch(...)`
  * `@app.delete(...)`
* Blueprint route support
* Blueprint `url_prefix` support
* Nested and cross-file Blueprint registration support
* Automatic Blueprint tags for Swagger UI grouping
* Flask path parameter conversion to OpenAPI format
* Flask converter support:

  * `string`
  * `int`
  * `float`
  * `path`
  * `uuid`
* Query parameter detection
* JSON request-body detection
* JSON field inference
* Required JSON field detection
* Request field type inference
* Response status-code detection
* Response schema inference
* Function docstrings as OpenAPI descriptions
* Synchronous and asynchronous Flask route support
* Marshmallow request schema support
* Marshmallow response schema support
* Cross-file Marshmallow schema resolution
* Automatic request content-type detection for JSON and multipart forms
* Request and response content-type docstring overrides
* Nested Marshmallow schema support
* OpenAPI component schema generation
* Configurable authentication decorators
* Multiple OpenAPI security schemes
* Authentication scheme `AND` / `OR` support
* JWT Bearer authentication support
* API-key authentication support
* Swagger UI integration
* JSON OpenAPI output
* Command-line interface
* Python API

## Requirements

* Python 3.10+
* Flask 3.0+

## Installation

Install the latest stable release from PyPI:

```bash
pip install flask-ast-openapi
```

To install this specific release:

```bash
pip install flask-ast-openapi==0.1.1
```

## Quick Start

Assume the following Flask application:

```python
from flask import Flask, request

app = Flask(__name__)


@app.post("/users/<int:user_id>")
def update_user(user_id):
    """Update a user."""

    name = request.json["name"]
    active = request.json.get("active", True)

    return {
        "id": user_id,
        "name": name,
        "active": active,
    }, 200
```

Generate an OpenAPI specification using the command line:

```bash
flask-ast-openapi ./src -o openapi.json
```

The generated specification contains the detected route:

```text
POST /users/{user_id}
```

along with its path parameter, request fields, response information, and description.

## Command-Line Usage

Basic usage:

```bash
flask-ast-openapi <source_dir>
```

Example:

```bash
flask-ast-openapi ./app
```

By default, the specification is written to:

```text
openapi.json
```

### Custom output file

```bash
flask-ast-openapi ./app -o api-spec.json
```

or:

```bash
flask-ast-openapi ./app --output api-spec.json
```

### Custom API title

```bash
flask-ast-openapi ./app \
    --title "My API"
```

### Custom API version

```bash
flask-ast-openapi ./app \
    --version "2.0.0"
```

### Complete CLI example

```bash
flask-ast-openapi ./app \
    -o openapi.json \
    --title "My Flask API" \
    --version "1.0.0"
```

## Python API

The generator can also be used directly from Python.

```python
from flask_ast_openapi import FlaskASTOpenAPI


generator = FlaskASTOpenAPI(
    "./app"
)

spec = generator.generate(
    title="My Flask API",
    version="1.0.0",
)

generator.write_json(
    spec,
    "openapi.json",
)
```

## Swagger UI Integration

The package can expose both the generated OpenAPI document and Swagger UI directly from a Flask application.

```python
from flask import Flask

from flask_ast_openapi import create_swagger_blueprint


app = Flask(__name__)

swagger_bp = create_swagger_blueprint(
    "./app/controllers",
    title="My Flask API",
    version="1.0.0",
    docs_url="/docs",
    spec_url="/openapi.json",
)

app.register_blueprint(swagger_bp)
```

Swagger UI is then available at:

```text
/docs
```

and the generated OpenAPI JSON at:

```text
/openapi.json
```

Custom paths can also be used:

```python
swagger_bp = create_swagger_blueprint(
    "./app/controllers",
    docs_url="/api/docs",
    spec_url="/api/openapi.json",
)
```

## Authentication

Authentication decorators can be mapped to OpenAPI security schemes.

For example, assume protected Flask endpoints use:

```python
@require_auth
@app.get("/protected")
def protected():
    return {"status": "ok"}
```

The generator can be configured to associate `require_auth` with an OpenAPI security scheme.

```python
from flask_ast_openapi import FlaskASTOpenAPI


generator = FlaskASTOpenAPI(
    "./app",
    auth_decorator_names={
        "require_auth",
    },
    auth_scheme_mapping={
        "require_auth": [
            "BearerAuth",
        ],
    },
    security_schemes={
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        },
    },
)
```

This produces an OpenAPI security definition for JWT Bearer authentication.

## Multiple Authentication Schemes

Version `0.1.1` allows authentication configuration to be passed directly to `create_swagger_blueprint()`.

For example, an API may allow either:

* a JWT Bearer token for users and administrators, or
* an API token for devices and external services.

```python
from flask_ast_openapi import create_swagger_blueprint


swagger_bp = create_swagger_blueprint(
    "./app/controllers",
    title="My Flask API",
    version="1.0.0",
    docs_url="/api/docs",
    spec_url="/api/openapi.json",
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
            "description": "JWT Token for admin/users",
        },
        "ApiTokenAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Api-Token",
            "description": (
                "API Token for edge devices and external services"
            ),
        },
    },
)
```

The generated OpenAPI operation contains:

```json
{
  "security": [
    {
      "BearerAuth": []
    },
    {
      "ApiTokenAuth": []
    }
  ]
}
```

In OpenAPI, separate objects inside the `security` array represent an `OR` relationship.

Therefore:

```text
BearerAuth OR ApiTokenAuth
```

Either authentication method can independently authorize the request.

## AND Authentication Mode

If an endpoint requires all configured authentication schemes simultaneously, use:

```python
auth_scheme_modes={
    "require_auth": "and",
}
```

The generated OpenAPI security requirement becomes:

```json
{
  "security": [
    {
      "BearerAuth": [],
      "ApiTokenAuth": []
    }
  ]
}
```

This represents:

```text
BearerAuth AND ApiTokenAuth
```

The default authentication mode is `and` unless another mode is explicitly configured.

Supported values are:

```text
and
or
```

## Marshmallow Integration

`flask-ast-openapi` can generate OpenAPI schemas from Marshmallow schema classes.

Example:

```python
from marshmallow import Schema, fields


class UserRequestSchema(Schema):
    name = fields.String(required=True)
    age = fields.Integer()
    active = fields.Boolean()
```

A route can reference the schema from its docstring:

```python
@app.post("/users")
def create_user():
    """
    Create a user.

    :request: UserRequestSchema
    """

    ...
```

JSON bodies are detected from `request.get_json()` and `request.json`.
Multipart bodies are detected from `request.form` and `request.files`.
For custom media types, use docstring directives:

```python
@app.post("/documents")
def upload_document():
    """
    :request: DocumentUploadSchema
    :response: DocumentResponseSchema
    :request-content-type: multipart/form-data
    :response-content-type: application/json
    """

    ...
```

The generator detects `UserRequestSchema` and creates an OpenAPI request-body schema.

## Response Schemas

Response schemas can be declared similarly:

```python
class UserResponseSchema(Schema):
    id = fields.Integer(required=True)
    name = fields.String(required=True)
```

Reference it in the route docstring:

```python
@app.post("/users")
def create_user():
    """
    Create a user.

    :request: UserRequestSchema
    :response: UserResponseSchema
    """

    ...
```

The response schema is then included in the generated OpenAPI specification.

## Nested Marshmallow Schemas

Nested Marshmallow schemas are supported.

```python
class ProfileSchema(Schema):
    email = fields.String(required=True)


class UserSchema(Schema):
    name = fields.String(required=True)
    profile = fields.Nested(ProfileSchema)
```

The generated OpenAPI schema uses component references:

```json
{
  "profile": {
    "$ref": "#/components/schemas/ProfileSchema"
  }
}
```

Lists of nested schemas are also supported:

```python
class TeamSchema(Schema):
    members = fields.List(
        fields.Nested(UserSchema)
    )
```

which generates an array whose items reference the corresponding OpenAPI component.

## Supported Marshmallow Fields

The current release recognizes common Marshmallow fields including:

| Marshmallow field | OpenAPI representation |
| ----------------- | ---------------------- |
| `fields.String`   | `string`               |
| `fields.Integer`  | `integer`              |
| `fields.Float`    | `number / float`       |
| `fields.Boolean`  | `boolean`              |
| `fields.DateTime` | `string / date-time`   |
| `fields.Date`     | `string / date`        |
| `fields.UUID`     | `string / uuid`        |
| `fields.Dict`     | `object`               |
| `fields.List`     | `array`                |
| `fields.Nested`   | `$ref`                 |
| `fields.Raw`      | unrestricted schema    |

Unknown field types currently fall back to a string schema.

## Blueprint Support

Flask Blueprints are supported.

Example:

```python
from flask import Blueprint


users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/users",
)


@users_bp.get("/<int:user_id>")
def get_user(user_id):
    return {"id": user_id}
```

The generated OpenAPI route becomes:

```text
GET /api/users/{user_id}
```

## Path Parameters

Flask-style parameters:

```text
/users/<int:user_id>
```

are converted to OpenAPI-style paths:

```text
/users/{user_id}
```

Converter information is used to determine the OpenAPI parameter schema.

For example:

```text
<int:user_id>
```

becomes an integer path parameter.

## Query Parameters

Query parameters accessed using Flask's request object can be detected.

Example:

```python
search = request.args.get("search")
page = request.args.get("page")
```

The generated operation contains `search` and `page` as query parameters.

## JSON Request Bodies

The generator detects common Flask JSON access patterns such as:

```python
data = request.get_json()
```

and:

```python
data = request.json
```

It also detects direct field access:

```python
name = request.json["name"]
```

and optional field access:

```python
active = request.json.get(
    "active",
    True,
)
```

Subscript access is treated as a required field where it can be determined statically.

## Response Detection

The generator analyzes common Flask return patterns.

For example:

```python
return {
    "status": "created",
}, 201
```

The `201` status code and response structure can be added to the generated OpenAPI operation.

Multiple statically detectable response status codes can be collected from a route.

## Route Descriptions

Function docstrings are used as OpenAPI descriptions.

```python
@app.get("/users")
def list_users():
    """Return all registered users."""

    ...
```

produces a corresponding operation description.

## Generated OpenAPI Version

The current release generates:

```text
OpenAPI 3.0.3
```

## How It Works

The package uses Python's built-in `ast` module.

At a high level:

```text
Python source files
        |
        v
AST parsing
        |
        v
Route discovery
        |
        v
Request / response analysis
        |
        v
Schema and security analysis
        |
        v
OpenAPI model generation
        |
        v
openapi.json
```

Because analysis is static, the target Flask application does not need to be executed during specification generation.

This makes the library useful for projects where importing the application would otherwise initialize databases, message brokers, hardware integrations, external services, or other runtime dependencies.

## Development

Clone the repository:

```bash
git clone <repository-url>
cd flask-ast-openapi
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the project in editable mode with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the test suite:

```bash
python -m pytest -v
```

If you need a project-local pytest temporary directory:

```bash
python -m pytest -v --basetemp=.pytest_tmp
```

The `.pytest_tmp/` directory should not be committed to version control.

## Building the Package

Install build tools:

```bash
python -m pip install build twine
```

Build the distribution:

```bash
python -m build
```

Validate the generated packages:

```bash
python -m twine check dist/*
```

## Current Limitations

`flask-ast-openapi` performs static source-code analysis, so some highly dynamic Flask patterns cannot be resolved reliably.

Current limitations include:

* Dynamically generated route paths may not be detected.
* Dynamically generated decorators may not be detected.
* Runtime-generated schemas cannot be statically inferred.
* Marshmallow schema references imported from another module may not always be resolved from a route docstring.
* String-based nested declarations such as `fields.Nested("UserSchema")` are not fully supported.
* Annotated schema assignments using some `AnnAssign` patterns are not currently handled.
* Advanced Marshmallow options such as aliases, `load_only`, `dump_only`, validators, and custom field metadata are not fully represented.
* Custom Marshmallow field classes currently fall back to a basic schema.
* CLI authentication configuration is not currently exposed as command-line arguments; advanced security configuration should use the Python API.
* Swagger UI assets are currently loaded from a CDN.
* Swagger-generated specifications are cached by the Swagger Blueprint for the lifetime of the running process. Restart the application after controller changes when regeneration is required.
* The library does not execute Flask application code to discover routes created only at runtime.

These limitations are candidates for future releases.

## Project Goals

The project aims to provide a lightweight and extensible static-analysis alternative for documenting existing Flask applications.

Future development may include:

* More advanced Marshmallow support
* Cross-module schema resolution
* Better type inference
* YAML output
* Additional Flask extension support
* OpenAPI validation
* Improved diagnostics and warnings
* Offline Swagger UI assets
* More configurable CLI options
* CI/CD and automated PyPI releases

## Version

Current version:

```text
0.2.1
```

Version `0.2.1` adds automatic JSON and multipart request content-type
detection, explicit request/response media-type overrides, and avoids creating
request bodies for header-only and path-only inputs.

## License

See the `LICENSE` file in the repository for license information.
