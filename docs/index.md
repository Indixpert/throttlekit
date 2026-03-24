# Getting Started

Welcome to ThrottleKit! A plug-and-play rate limiting library for Python web frameworks.

## Installation

Install ThrottleKit using pip:

```bash
pip install throttlekit
```

You will also need to install the dependencies for the framework you are using, for example `fastapi` and `uvicorn` for FastAPI, or `flask` for Flask.

## Basic Usage (FastAPI)

Wrap your FastAPI application with `ThrottleMiddleware`.

```python
from fastapi import FastAPI
from throttlekit import Limiter
from throttlekit.middleware.fastapi import ThrottleMiddleware

app = FastAPI()
limiter = Limiter()

# Apply a default rate limit of 100 requests per hour to all routes
app.add_middleware(
    ThrottleMiddleware,
    limiter=limiter,
    default_limit="100/hour"
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/special")
@limiter.limit("5/minute")
def special_endpoint():
    return {"message": "This is a specially-limited endpoint."}
```

## Basic Usage (Flask)

Initialize throttling for your Flask application using `init_throttle`.

```python
from flask import Flask, jsonify
from throttlekit import Limiter
from throttlekit.middleware.flask import init_throttle

app = Flask(__name__)
limiter = Limiter()

# Apply a default rate limit of 100 requests per hour to all routes
init_throttle(app, limiter, default_limit="100/hour")

@app.route("/")
def index():
    return jsonify(status="ok")

@app.route("/special")
@limiter.limit("5/minute")
def special_endpoint():
    return jsonify(message="This is a specially-limited endpoint.")
```
