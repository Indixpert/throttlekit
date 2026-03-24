import time
import pytest
from flask import Flask, jsonify

from throttlekit.core import Limiter
from throttlekit.middleware.flask import init_throttle

@pytest.fixture
def limiter():
    return Limiter()

@pytest.fixture
def app(limiter):
    app = Flask(__name__)
    app.config["TESTING"] = True

    init_throttle(app, limiter, default_limit="5/second")

    @app.route("/unlimited")
    def unlimited():
        return jsonify(status="ok")

    @app.route("/limited")
    @limiter.limit("2/second")
    def limited():
        return jsonify(status="ok")

    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_flask_default_limit_is_applied(client):
    for _ in range(5):
        resp = client.get("/unlimited")
        assert resp.status_code == 200
        assert "X-RateLimit-Limit" in resp.headers
        assert resp.headers["X-RateLimit-Limit"] == "5"

    resp = client.get("/unlimited")
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers

def test_flask_limited_route_gets_throttled(client):
    for i in range(2):
        resp = client.get("/limited")
        assert resp.status_code == 200
        assert resp.json == {"status": "ok"}
        assert "X-RateLimit-Limit" in resp.headers
        assert resp.headers["X-RateLimit-Limit"] == "2"
        assert resp.headers["X-RateLimit-Remaining"] == str(1 - i)

    resp = client.get("/limited")
    assert resp.status_code == 429
    assert resp.json["error"] == "rate_limit_exceeded"
    assert "Retry-After" in resp.headers
    assert resp.headers["X-RateLimit-Limit"] == "2"
    assert resp.headers["X-RateLimit-Remaining"] == "0"

def test_flask_throttled_request_can_be_retried_after_window(client):
    for _ in range(2):
        client.get("/limited")

    resp = client.get("/limited")
    assert resp.status_code == 429
    retry_after = int(resp.headers["Retry-After"])
    assert retry_after >= 0

    time.sleep(retry_after + 0.2)  # Sleep until after the window expires

    resp = client.get("/limited")
    assert resp.status_code == 200
    assert resp.headers["X-RateLimit-Remaining"] == "1"

def test_flask_no_default_limit(limiter):
    app = Flask(__name__)
    init_throttle(app, limiter, default_limit=None)

    @app.route("/unlimited")
    def unlimited():
        return jsonify(status="ok")

    client = app.test_client()

    for _ in range(10):
        resp = client.get("/unlimited")
        assert resp.status_code == 200
        assert "X-RateLimit-Limit" not in resp.headers
