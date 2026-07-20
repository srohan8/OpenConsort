# -*- coding: utf-8 -*-
"""Generate fastapi-eval-suite.jsonl — held-out, machine-checkable eval tasks.

These are GENUINELY INDEPENDENT of the training pairs: different resources
(invoices, bookmarks, subscriptions, tickets, weather, employees, ...) and
different specific behaviors, so passing them requires generalization, not
memorization of the Task 2 snippets. Each has an http_sequence check_spec that
eval_runner.py can execute against model-generated code.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
E = []


def add(task, category, steps):
    E.append({
        "task": task,
        "category": category,
        "check_type": "http_sequence",
        "check_spec": {"steps": steps},
    })


# ---- crud ----
add("Create a FastAPI app for bookmarks with POST /bookmarks (accepts url and title, returns 201 with an id) and GET /bookmarks/{id}.",
    "crud",
    [{"method": "POST", "path": "/bookmarks", "json": {"url": "http://a.com", "title": "A"},
      "save": {"bid": "$.id"}, "expect": {"status": 201, "json_keys": ["id", "url", "title"]}},
     {"method": "GET", "path": "/bookmarks/{bid}", "expect": {"status": 200, "json_subset": {"title": "A"}}}])

add("Create a FastAPI app that stores invoices and returns 404 when getting a non-existent invoice id.",
    "crud",
    [{"method": "GET", "path": "/invoices/12345", "expect": {"status": 404}}])

add("Create a FastAPI DELETE /comments/{id} endpoint that returns 204 for a comment that exists after creation.",
    "crud",
    [{"method": "POST", "path": "/comments", "json": {"body": "hi"}, "save": {"cid": "$.id"},
      "expect": {"status": 201}},
     {"method": "DELETE", "path": "/comments/{cid}", "expect": {"status": 204}}])

# ---- pydantic-models ----
add("Create a POST /events endpoint whose Pydantic model requires a title (str) and a capacity integer that must be >= 1; return 422 for capacity 0.",
    "pydantic-models",
    [{"method": "POST", "path": "/events", "json": {"title": "Meetup", "capacity": 0}, "expect": {"status": 422}},
     {"method": "POST", "path": "/events", "json": {"title": "Meetup", "capacity": 50}, "expect": {"status": 200}}])

add("Create a POST /profiles endpoint using a response_model that excludes an internal 'ssn' field from the response.",
    "pydantic-models",
    [{"method": "POST", "path": "/profiles", "json": {"name": "Kim", "ssn": "111-22-3333"},
      "expect": {"status": 200, "json_subset": {"name": "Kim"}}},
     # second step re-posts and asserts ssn absent via json_equals-free key check
     {"method": "POST", "path": "/profiles", "json": {"name": "Lee", "ssn": "999-99-9999"},
      "expect": {"status": 200, "json_keys": ["name"]}}])

add("Create a POST /geo endpoint with a Pydantic model constraining latitude to [-90, 90]; reject 100 with 422.",
    "pydantic-models",
    [{"method": "POST", "path": "/geo", "json": {"lat": 100.0, "lon": 10.0}, "expect": {"status": 422}},
     {"method": "POST", "path": "/geo", "json": {"lat": 45.0, "lon": 10.0}, "expect": {"status": 200}}])

# ---- path-query-params ----
add("Create GET /convert/{celsius} that converts a Celsius integer path param to Fahrenheit and returns {'fahrenheit': value}.",
    "path-query-params",
    [{"method": "GET", "path": "/convert/100", "expect": {"status": 200, "json_subset": {"fahrenheit": 212.0}}},
     {"method": "GET", "path": "/convert/abc", "expect": {"status": 422}}])

add("Create GET /reports that has a REQUIRED query parameter 'year' (int); return 422 if it is missing.",
    "path-query-params",
    [{"method": "GET", "path": "/reports", "expect": {"status": 422}},
     {"method": "GET", "path": "/reports", "params": {"year": 2026}, "expect": {"status": 200}}])

add("Create GET /grades with a query parameter 'letter' constrained by an Enum to A/B/C; reject Z with 422.",
    "path-query-params",
    [{"method": "GET", "path": "/grades", "params": {"letter": "Z"}, "expect": {"status": 422}},
     {"method": "GET", "path": "/grades", "params": {"letter": "A"}, "expect": {"status": 200}}])

# ---- response-status-codes ----
add("Create POST /jobs that returns HTTP 202 Accepted with a job id.",
    "response-status-codes",
    [{"method": "POST", "path": "/jobs", "json": {"kind": "export"},
      "expect": {"status": 202, "json_keys": ["id"]}}])

add("Create GET /robots.txt that returns plain text 'User-agent: *' with a text/plain content type.",
    "response-status-codes",
    [{"method": "GET", "path": "/robots.txt", "expect": {"status": 200}}])

# ---- error-handling ----
add("Create GET /withdraw that raises HTTP 403 with detail 'insufficient funds' when amount query param exceeds 100.",
    "error-handling",
    [{"method": "GET", "path": "/withdraw", "params": {"amount": 150}, "expect": {"status": 403, "json_subset": {"detail": "insufficient funds"}}},
     {"method": "GET", "path": "/withdraw", "params": {"amount": 50}, "expect": {"status": 200}}])

add("Create a custom exception handler so that a RateLimited exception returns HTTP 429 with body {'error':'rate_limited'}.",
    "error-handling",
    [{"method": "GET", "path": "/limited", "expect": {"status": 429, "json_equals": {"error": "rate_limited"}}}])

# ---- dependency-injection ----
add("Create a dependency that reads an X-Tenant header and injects it; GET /whoami returns {'tenant': value}; missing header -> 400.",
    "dependency-injection",
    [{"method": "GET", "path": "/whoami", "expect": {"status": 400}},
     {"method": "GET", "path": "/whoami", "headers": {"X-Tenant": "acme"}, "expect": {"status": 200, "json_subset": {"tenant": "acme"}}}])

add("Create a yield dependency providing a fake db session; GET /ping-db returns {'db':'ok'}.",
    "dependency-injection",
    [{"method": "GET", "path": "/ping-db", "expect": {"status": 200, "json_subset": {"db": "ok"}}}])

# ---- auth-jwt ----
add("Create register (POST /register), login (POST /login returning a JWT), and a protected GET /dashboard requiring the bearer token.",
    "auth-jwt",
    [{"method": "POST", "path": "/register", "json": {"username": "neo", "password": "matrix1"}, "expect": {"status": 201}},
     {"method": "POST", "path": "/login", "json": {"username": "neo", "password": "matrix1"},
      "save": {"tok": "$.access_token"}, "expect": {"status": 200, "json_keys": ["access_token"]}},
     {"method": "GET", "path": "/dashboard", "expect": {"status": 401}},
     {"method": "GET", "path": "/dashboard", "headers": {"Authorization": "Bearer {tok}"}, "expect": {"status": 200}}])

add("Create POST /token using OAuth2PasswordRequestForm returning a bearer JWT for user 'admin'/'admin'; wrong password -> 401.",
    "auth-jwt",
    [{"method": "POST", "path": "/token", "data": {"username": "admin", "password": "wrong"}, "expect": {"status": 401}},
     {"method": "POST", "path": "/token", "data": {"username": "admin", "password": "admin"},
      "expect": {"status": 200, "json_subset": {"token_type": "bearer"}}}])

add("Create a protected GET /secret using OAuth2PasswordBearer that returns 401 when no Authorization header is supplied.",
    "auth-jwt",
    [{"method": "GET", "path": "/secret", "expect": {"status": 401}}])

# ---- pagination ----
add("Create GET /articles that paginates 30 seeded articles with page and size query params returning an envelope {items,total,page,size}.",
    "pagination",
    [{"method": "GET", "path": "/articles", "params": {"page": 1, "size": 10},
      "expect": {"status": 200, "json_subset": {"total": 30, "page": 1, "size": 10}}},
     {"method": "GET", "path": "/articles", "params": {"page": 3, "size": 10},
      "expect": {"status": 200, "json_len": {"path": "$.items", "op": "==", "value": 10}}}])

add("Create GET /logs paginated with skip/limit over 15 seeded entries; ?skip=10&limit=10 returns exactly 5 items.",
    "pagination",
    [{"method": "GET", "path": "/logs", "params": {"skip": 10, "limit": 10},
      "expect": {"status": 200, "json_len": {"path": "$", "op": "==", "value": 5}}}])

add("Create GET /catalog paginated with size query param capped at 25; size=26 returns 422.",
    "pagination",
    [{"method": "GET", "path": "/catalog", "params": {"size": 26}, "expect": {"status": 422}},
     {"method": "GET", "path": "/catalog", "params": {"size": 25}, "expect": {"status": 200}}])

# ---- database-sqlalchemy ----
add("Using SQLAlchemy + SQLite, create POST /movies (title) returning 201 with id, and GET /movies listing all movies.",
    "database-sqlalchemy",
    [{"method": "POST", "path": "/movies", "json": {"title": "Dune"}, "expect": {"status": 201, "json_keys": ["id"]}},
     {"method": "GET", "path": "/movies", "expect": {"status": 200, "json_len": {"path": "$", "op": ">=", "value": 1}}}])

add("Using SQLAlchemy + SQLite, create an employees table; GET /employees/{id} returns 404 for an unknown id.",
    "database-sqlalchemy",
    [{"method": "GET", "path": "/employees/9999", "expect": {"status": 404}}])

add("Using SQLAlchemy + SQLite, create POST /tags then GET /tags?q= filtering by case-insensitive substring.",
    "database-sqlalchemy",
    [{"method": "POST", "path": "/tags", "json": {"name": "Python"}, "expect": {"status": 201}},
     {"method": "POST", "path": "/tags", "json": {"name": "Java"}, "expect": {"status": 201}},
     {"method": "GET", "path": "/tags", "params": {"q": "py"}, "expect": {"status": 200, "json_len": {"path": "$", "op": "==", "value": 1}}}])

# ---- background-tasks ----
add("Create POST /emails that schedules a background task appending to an outbox; GET /outbox reflects the sent email.",
    "background-tasks",
    [{"method": "POST", "path": "/emails", "params": {"to": "a@b.com"}, "expect": {"status": 200}},
     {"method": "GET", "path": "/outbox", "expect": {"status": 200, "json_len": {"path": "$", "op": "==", "value": 1}}}])

add("Create POST /track that uses a background task to record a page-view count; GET /views returns count 2 after two POSTs.",
    "background-tasks",
    [{"method": "POST", "path": "/track", "expect": {"status": 200}},
     {"method": "POST", "path": "/track", "expect": {"status": 200}},
     {"method": "GET", "path": "/views", "expect": {"status": 200, "json_subset": {"count": 2}}}])

# ---- file-upload ----
add("Create POST /avatar accepting an uploaded file and returning {'filename':..., 'size':...}.",
    "file-upload",
    [{"method": "POST", "path": "/avatar", "files": {"file": ["me.png", "abcd", "image/png"]},
      "expect": {"status": 200, "json_subset": {"filename": "me.png", "size": 4}}}])

add("Create POST /csv-import that accepts a file plus a Form field 'delimiter'; return the delimiter and byte size.",
    "file-upload",
    [{"method": "POST", "path": "/csv-import", "data": {"delimiter": ";"}, "files": {"file": ["d.csv", "1;2;3", "text/csv"]},
      "expect": {"status": 200, "json_subset": {"delimiter": ";", "size": 5}}}])

# ---- routing-structure ----
add("Create an APIRouter mounted at /api/v2 exposing GET /api/v2/status returning {'version':'v2'}.",
    "routing-structure",
    [{"method": "GET", "path": "/api/v2/status", "expect": {"status": 200, "json_equals": {"version": "v2"}}},
     {"method": "GET", "path": "/status", "expect": {"status": 404}}])

# ---- middleware-cors ----
add("Add custom middleware that sets an 'X-Request-ID' header on every response for GET /health.",
    "middleware-cors",
    [{"method": "GET", "path": "/health", "expect": {"status": 200}}])

add("Configure CORSMiddleware to allow origin https://client.app and echo it in access-control-allow-origin for GET /data.",
    "middleware-cors",
    [{"method": "GET", "path": "/data", "headers": {"Origin": "https://client.app"},
      "expect": {"status": 200, "header": {"access-control-allow-origin": "https://client.app"}}}])


path = os.path.join(HERE, "fastapi-eval-suite.jsonl")
with open(path, "w", encoding="utf-8") as f:
    for rec in E:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"wrote {len(E)} eval tasks to {path}")
