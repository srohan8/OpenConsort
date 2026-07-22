# -*- coding: utf-8 -*-
"""Round 2 dataset augmentation candidates, per doc/kickoff-brief-round2-augmentation.md.

Each entry: task (free-text), category, code (the reference solution), check_spec
(http_sequence, same schema as fastapi-eval-suite-v3.jsonl), verification_notes
(filled in after running). Verified via eval_runner.run_eval before being added
to fastapi-backend-pairs-v3.jsonl - nothing here is trusted on visual inspection alone.
"""

EXAMPLES = []

# ============================================================
# PRIORITY 1 - Field placement (5 varied examples: query-only,
# body-only, path-only, and two path+body mixed cases; distinct
# field names/methods each, none reused from Round 1)
# ============================================================

EXAMPLES.append({
    "task": "Create a FastAPI GET /search endpoint that requires a query parameter 'keyword' (string) and returns matching items from an in-memory list, filtering by whether the keyword is a substring of the item's name.",
    "category": "path-query-params",
    "code": '''from fastapi import FastAPI

app = FastAPI()

catalog = [{"id": 1, "name": "wireless mouse"}, {"id": 2, "name": "wired keyboard"}, {"id": 3, "name": "usb hub"}]

@app.get("/search")
def search(keyword: str):
    return [item for item in catalog if keyword.lower() in item["name"].lower()]
''',
    "check_spec": {
        "steps": [
            {"method": "GET", "path": "/search", "expect": {"status": 422}},
            {"method": "GET", "path": "/search", "params": {"keyword": "wireless"}, "expect": {"status": 200, "json_len": {"path": "$", "op": "==", "value": 1}}},
        ]
    },
})

EXAMPLES.append({
    "task": "Create a FastAPI POST /reviews endpoint that requires a JSON body with 'rating' (integer) and 'comment' (string) fields, and returns the created review with a 201 status and a generated id.",
    "category": "pydantic-models",
    "code": '''from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
reviews = []
next_id = 1

class Review(BaseModel):
    rating: int
    comment: str

@app.post("/reviews", status_code=201)
def create_review(review: Review):
    global next_id
    rid = next_id
    next_id += 1
    record = {"id": rid, "rating": review.rating, "comment": review.comment}
    reviews.append(record)
    return record
''',
    "check_spec": {
        "steps": [
            {"method": "POST", "path": "/reviews", "json": {}, "expect": {"status": 422}},
            {"method": "POST", "path": "/reviews", "json": {"rating": 5, "comment": "great"}, "expect": {"status": 201, "json_keys": ["id", "rating", "comment"]}},
        ]
    },
})

EXAMPLES.append({
    "task": "Create a FastAPI DELETE /sessions/{session_id} endpoint (path parameter only, no body) that removes a session from an in-memory store and returns 204, or 404 if the session_id doesn't exist.",
    "category": "crud",
    "code": '''from fastapi import FastAPI, HTTPException, Response

app = FastAPI()
sessions = {"abc123": {"user": "alice"}, "def456": {"user": "bob"}}

@app.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="session not found")
    del sessions[session_id]
    return Response(status_code=204)
''',
    "check_spec": {
        "steps": [
            {"method": "DELETE", "path": "/sessions/doesnotexist", "expect": {"status": 404}},
            {"method": "DELETE", "path": "/sessions/abc123", "expect": {"status": 204}},
        ]
    },
})

EXAMPLES.append({
    "task": "Create a FastAPI PUT /accounts/{account_id} endpoint that takes the account_id from the path and a JSON body with a 'balance' (float) field, updates the account's balance, and returns the updated account.",
    "category": "crud",
    "code": '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
accounts = {1: {"id": 1, "balance": 100.0}, 2: {"id": 2, "balance": 50.0}}

class BalanceUpdate(BaseModel):
    balance: float

@app.put("/accounts/{account_id}")
def update_balance(account_id: int, update: BalanceUpdate):
    if account_id not in accounts:
        raise HTTPException(status_code=404, detail="account not found")
    accounts[account_id]["balance"] = update.balance
    return accounts[account_id]
''',
    "check_spec": {
        "steps": [
            {"method": "PUT", "path": "/accounts/1", "json": {"balance": 250.5}, "expect": {"status": 200, "json_subset": {"id": 1, "balance": 250.5}}},
            {"method": "PUT", "path": "/accounts/999", "json": {"balance": 10.0}, "expect": {"status": 404}},
        ]
    },
})

EXAMPLES.append({
    "task": "Create a FastAPI PATCH /orders/{order_id} endpoint that takes the order_id from the path and a JSON body with a 'status' (string) field, updates only the order's status, and returns the updated order.",
    "category": "crud",
    "code": '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
orders = {1: {"id": 1, "status": "pending", "total": 42.0}}

class StatusUpdate(BaseModel):
    status: str

@app.patch("/orders/{order_id}")
def update_status(order_id: int, update: StatusUpdate):
    if order_id not in orders:
        raise HTTPException(status_code=404, detail="order not found")
    orders[order_id]["status"] = update.status
    return orders[order_id]
''',
    "check_spec": {
        "steps": [
            {"method": "PATCH", "path": "/orders/1", "json": {"status": "shipped"}, "expect": {"status": 200, "json_subset": {"id": 1, "status": "shipped", "total": 42.0}}},
            {"method": "PATCH", "path": "/orders/1", "json": {}, "expect": {"status": 422}},
        ]
    },
})

# ============================================================
# PRIORITY 2 - Undefined-name/missing-import generalization
# (3 examples, DIFFERENT categories from Round 1's SQLAlchemy fix,
# each a complete, self-consistent example where every custom
# class/exception/dependency used is actually defined/imported)
# ============================================================

EXAMPLES.append({
    "task": "Create a FastAPI POST /coupons/apply endpoint that takes a JSON body with a 'code' field. If the code is not in a known list of valid coupon codes, raise a custom InvalidCoupon exception (handled by a registered exception handler that returns 400 with a JSON detail message). If valid, return the discount percentage.",
    "category": "pydantic-models",
    "code": '''from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

VALID_COUPONS = {"SAVE10": 10, "SAVE20": 20}

class InvalidCoupon(Exception):
    def __init__(self, code: str):
        self.code = code

@app.exception_handler(InvalidCoupon)
def invalid_coupon_handler(request: Request, exc: InvalidCoupon):
    return JSONResponse(status_code=400, content={"detail": f"invalid coupon code: {exc.code}"})

class CouponRequest(BaseModel):
    code: str

@app.post("/coupons/apply")
def apply_coupon(req: CouponRequest):
    if req.code not in VALID_COUPONS:
        raise InvalidCoupon(req.code)
    return {"code": req.code, "discount_percent": VALID_COUPONS[req.code]}
''',
    "check_spec": {
        "steps": [
            {"method": "POST", "path": "/coupons/apply", "json": {"code": "BOGUS"}, "expect": {"status": 400}},
            {"method": "POST", "path": "/coupons/apply", "json": {"code": "SAVE10"}, "expect": {"status": 200, "json_subset": {"discount_percent": 10}}},
        ]
    },
})

EXAMPLES.append({
    "task": "Create a FastAPI GET /downloads/{file_id} endpoint that simulates rate limiting: track request counts per file_id in memory, and if a file has been requested more than 2 times, raise a custom RateLimited exception (handled by a registered exception handler returning 429). Otherwise return the file info.",
    "category": "error-handling",
    "code": '''from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

request_counts = {}
files = {"f1": {"file_id": "f1", "name": "report.pdf"}}

class RateLimited(Exception):
    def __init__(self, file_id: str):
        self.file_id = file_id

@app.exception_handler(RateLimited)
def rate_limited_handler(request: Request, exc: RateLimited):
    return JSONResponse(status_code=429, content={"detail": f"too many requests for {exc.file_id}"})

@app.get("/downloads/{file_id}")
def download(file_id: str):
    request_counts[file_id] = request_counts.get(file_id, 0) + 1
    if request_counts[file_id] > 2:
        raise RateLimited(file_id)
    if file_id not in files:
        return {"file_id": file_id, "name": "unknown"}
    return files[file_id]
''',
    "check_spec": {
        "steps": [
            {"method": "GET", "path": "/downloads/f1", "expect": {"status": 200}},
            {"method": "GET", "path": "/downloads/f1", "expect": {"status": 200}},
            {"method": "GET", "path": "/downloads/f1", "expect": {"status": 429}},
        ]
    },
})

EXAMPLES.append({
    "task": "Create a FastAPI GET /admin/stats endpoint that uses a dependency function require_admin (defined via Depends) which checks for a 'X-Admin-Token' header equal to 'secret-token'; raise 403 if missing or wrong via the dependency itself. The endpoint returns a fixed stats object if the dependency passes.",
    "category": "dependency-injection",
    "code": '''from fastapi import FastAPI, Header, HTTPException, Depends

app = FastAPI()

def require_admin(x_admin_token: str = Header(None)):
    if x_admin_token != "secret-token":
        raise HTTPException(status_code=403, detail="admin access required")
    return True

@app.get("/admin/stats")
def get_stats(admin: bool = Depends(require_admin)):
    return {"users": 42, "active_sessions": 7}
''',
    "check_spec": {
        "steps": [
            {"method": "GET", "path": "/admin/stats", "expect": {"status": 403}},
            {"method": "GET", "path": "/admin/stats", "headers": {"X-Admin-Token": "secret-token"}, "expect": {"status": 200, "json_subset": {"users": 42}}},
        ]
    },
})

# ============================================================
# PRIORITY 3 - Business-logic depth (3 examples: ownership-based
# auth 403 (not the X-Role pattern from Round 1), a differently-
# triggered rate limit, and pagination with TRUE total count +
# 422 validation on bad page/limit)
# ============================================================

EXAMPLES.append({
    "task": "Create a FastAPI DELETE /posts/{post_id} endpoint that requires a 'X-User-Id' header. Only the post's owner (matching owner_id) may delete it; return 403 if the header's user id doesn't match the post's owner_id, 404 if the post doesn't exist, 204 on success.",
    "category": "auth-jwt",
    "code": '''from fastapi import FastAPI, Header, HTTPException, Response

app = FastAPI()

posts = {1: {"id": 1, "owner_id": "u1", "title": "Hello"}, 2: {"id": 2, "owner_id": "u2", "title": "World"}}

@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int, x_user_id: str = Header(None)):
    if post_id not in posts:
        raise HTTPException(status_code=404, detail="post not found")
    if posts[post_id]["owner_id"] != x_user_id:
        raise HTTPException(status_code=403, detail="not the owner")
    del posts[post_id]
    return Response(status_code=204)
''',
    "check_spec": {
        "steps": [
            {"method": "DELETE", "path": "/posts/1", "headers": {"X-User-Id": "u2"}, "expect": {"status": 403}},
            {"method": "DELETE", "path": "/posts/999", "headers": {"X-User-Id": "u1"}, "expect": {"status": 404}},
            {"method": "DELETE", "path": "/posts/1", "headers": {"X-User-Id": "u1"}, "expect": {"status": 204}},
        ]
    },
})

EXAMPLES.append({
    "task": "Create a FastAPI POST /messages endpoint that requires a 'X-Client-Id' header identifying the caller, and rate-limits each distinct client to at most 3 messages per client, returning 429 once exceeded. Successful posts return 201 with the message id.",
    "category": "error-handling",
    "code": '''from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI()
client_counts = {}
next_id = 1

class Message(BaseModel):
    text: str

@app.post("/messages", status_code=201)
def post_message(msg: Message, x_client_id: str = Header(None)):
    global next_id
    count = client_counts.get(x_client_id, 0)
    if count >= 3:
        raise HTTPException(status_code=429, detail="rate limit exceeded for this client")
    client_counts[x_client_id] = count + 1
    mid = next_id
    next_id += 1
    return {"id": mid, "text": msg.text}
''',
    "check_spec": {
        "steps": [
            {"method": "POST", "path": "/messages", "json": {"text": "1"}, "headers": {"X-Client-Id": "c1"}, "expect": {"status": 201}},
            {"method": "POST", "path": "/messages", "json": {"text": "2"}, "headers": {"X-Client-Id": "c1"}, "expect": {"status": 201}},
            {"method": "POST", "path": "/messages", "json": {"text": "3"}, "headers": {"X-Client-Id": "c1"}, "expect": {"status": 201}},
            {"method": "POST", "path": "/messages", "json": {"text": "4"}, "headers": {"X-Client-Id": "c1"}, "expect": {"status": 429}},
            {"method": "POST", "path": "/messages", "json": {"text": "1"}, "headers": {"X-Client-Id": "c2"}, "expect": {"status": 201}},
        ]
    },
})

EXAMPLES.append({
    "task": "Create a FastAPI GET /products endpoint supporting pagination via 'page' (default 1) and 'limit' (default 10, max 100) query parameters. Return a JSON object with 'items' (the page slice), 'total' (the TRUE total count of all products, not the page size), 'page', and 'limit'. Return 422 if page < 1 or limit < 1 or limit > 100.",
    "category": "pagination",
    "code": '''from fastapi import FastAPI, Query

app = FastAPI()

all_products = [{"id": i, "name": f"product-{i}"} for i in range(1, 26)]

@app.get("/products")
def list_products(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    start = (page - 1) * limit
    end = start + limit
    return {
        "items": all_products[start:end],
        "total": len(all_products),
        "page": page,
        "limit": limit,
    }
''',
    "check_spec": {
        "steps": [
            {"method": "GET", "path": "/products", "params": {"page": 0}, "expect": {"status": 422}},
            {"method": "GET", "path": "/products", "params": {"limit": 101}, "expect": {"status": 422}},
            {"method": "GET", "path": "/products", "params": {"page": 1, "limit": 5}, "expect": {"status": 200, "json_subset": {"total": 25, "page": 1, "limit": 5}}},
        ]
    },
})
