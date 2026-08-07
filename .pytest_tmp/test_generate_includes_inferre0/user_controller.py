
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
