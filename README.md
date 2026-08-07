# flask-ast-openapi

Generate OpenAPI 3 specifications from Flask source code using Python's Abstract Syntax Tree (AST).

`flask-ast-openapi` analyzes Flask controller source files without importing or executing them and generates an OpenAPI specification that can be exported as JSON or served through Swagger UI.

## Features

* Flask route detection
* `@app.route(...)`
* `@app.get(...)`
* `@app.post(...)`
* `@app.put(...)`
* `@app.patch(...)`
* `@app.delete(...)`
* Blueprint URL prefix detection
* Path parameter conversion
* Query parameter detection
* JSON request body detection
* Response status code detection
* Response schema inference
* Marshmallow schema support
* Marshmallow required fields
* Nested Marshmallow schemas
* `List(Nested(...))` support
* OpenAPI `components.schemas`
* Route docstring descriptions
* `:request:` schema references
* `:response:` schema references
* Configurable authentication decorators
* Multiple OpenAPI security schemes
* AND / OR authentication modes
* JSON output
* Command-line interface
* Built-in Swagger UI integration for Flask

## Installation

Install from PyPI:

```bash
pip install flask-ast-openapi
```

To install a specific version:

```bash
pip install flask-ast-openapi==0.1.0
```

## CLI Usage

Generate an OpenAPI JSON file from a Flask controller directory:

```bash
flask-ast-openapi ./controllers -o openapi.json
```

Specify the API title and version:

```bash
flask-ast-openapi ./controllers \
    -o openapi.json \
    --title "My API" \
    --version "1.0.0"
```

On PowerShell:

```powershell
flask-ast-openapi `
    ".\controllers" `
    -o openapi.json `
    --title "My API" `
    --version "1.0.0"
```

## Python Usage

```python
from flask_ast_openapi import FlaskASTOpenAPI

generator = FlaskASTOpenAPI(
    "./controllers"
)

spec = generator.generate(
    title="My API",
    version="1.0.0",
)

generator.write_json(
    spec,
    "openapi.json",
)
```

## Swagger UI Integration

The package can expose both the generated OpenAPI specification and Swagger UI directly from an existing Flask application.

```python
from flask import Flask

from flask_ast_openapi import create_swagger_blueprint


app = Flask(__name__)

swagger_bp = create_swagger_blueprint(
    "./controllers",
    title="My API",
    version="1.0.0",
    docs_url="/api/docs",
    spec_url="/api/openapi.json",
)

app.register_blueprint(swagger_bp)
```

Then open:

```text
http://localhost:5000/api/docs
```

for Swagger UI.

The raw OpenAPI specification is available at:

```text
http://localhost:5000/api/openapi.json
```

## Flask Route Example

Given:

```python
@app.get("/users/<int:user_id>")
def get_user(user_id):
    """Get a user by ID."""

    return {
        "id": user_id,
        "name": "John",
    }, 200
```

The generated OpenAPI path will contain:

```text
/users/{user_id}
```

with an integer path parameter named `user_id`.

## Marshmallow Support

The package can use Marshmallow schemas referenced from route docstrings.

Example:

```python
from marshmallow import Schema, fields


class UserRequestSchema(Schema):
    name = fields.String(required=True)
    age = fields.Integer()


class UserResponseSchema(Schema):
    id = fields.Integer(required=True)
    name = fields.String(required=True)


@app.post("/users")
def create_user():
    """
    Create a user.

    :request: UserRequestSchema
    :response: UserResponseSchema
    """

    ...
```

`flask-ast-openapi` detects:

```text
:request: UserRequestSchema
```

and:

```text
:response: UserResponseSchema
```

and converts those Marshmallow schemas into OpenAPI schemas.

### Nested Schemas

Nested Marshmallow schemas are supported:

```python
class ProfileSchema(Schema):
    bio = fields.String()


class UserSchema(Schema):
    name = fields.String(required=True)
    profile = fields.Nested(ProfileSchema)
```

The nested schema is represented using an OpenAPI `$ref`:

```json
{
  "$ref": "#/components/schemas/ProfileSchema"
}
```

Lists of nested schemas are also supported:

```python
members = fields.List(
    fields.Nested(UserSchema)
)
```

## Authentication

Authentication decorator names can be configured.

```python
generator = FlaskASTOpenAPI(
    "./controllers",
    auth_decorator_names={
        "require_auth",
        "jwt_required",
    },
)
```

Security schemes can also be configured:

```python
generator = FlaskASTOpenAPI(
    "./controllers",
    auth_decorator_names={
        "require_auth",
    },
    auth_scheme_mapping={
        "require_auth": [
            "BearerAuth",
            "ApiKeyAuth",
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
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Token",
        },
    },
)
```

With:

```python
auth_scheme_modes={
    "require_auth": "or",
}
```

the generated OpenAPI security requirement means:

```text
BearerAuth OR ApiKeyAuth
```

Using:

```python
auth_scheme_modes={
    "require_auth": "and",
}
```

means both schemes are required.

## How It Works

The library uses Python's built-in `ast` module to parse source files.

The general flow is:

```text
Python source files
        |
        v
      AST
        |
        v
Flask route discovery
        |
        v
Request / response analysis
        |
        v
Marshmallow schema analysis
        |
        v
OpenAPI 3 specification
```

The Flask application itself does not need to be imported or executed during static OpenAPI generation.

## Development

Clone the repository:

```bash
git clone <repository-url>
cd flask-ast-openapi
```

Create a virtual environment and install the project in editable mode:

```bash
python -m pip install -e ".[dev]"
```

Run the test suite:

```bash
python -m pytest -v
```

On systems where the temporary directory causes pytest issues:

```bash
python -m pytest -v --basetemp=.pytest_tmp
```

## Current Limitations

AST-based analysis is static, so some highly dynamic Flask patterns may not be detectable.

Examples include:

* Dynamically constructed route paths
* Dynamically generated decorators
* Runtime-only schema definitions
* Complex request validation implemented outside the controller
* Response structures assembled through highly dynamic code
* Custom Marshmallow fields that cannot be inferred statically

Unknown field types currently fall back to a basic OpenAPI-compatible representation where possible.

## Python Support

Python 3.10 or newer is required.

## License

See the `LICENSE` file for license information.

## Version

Current release:

```text
0.1.0
```
