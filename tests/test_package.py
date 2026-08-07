def test_create_swagger_blueprint_is_publicly_importable():
    from flask_ast_openapi import create_swagger_blueprint

    assert callable(create_swagger_blueprint)