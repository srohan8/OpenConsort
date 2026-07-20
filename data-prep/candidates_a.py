# -*- coding: utf-8 -*-
"""Candidate task->code pairs, part A: crud, pydantic-models, path-query-params,
response-status-codes, error-handling, dependency-injection.

Each entry is {task, category, code, check}. `check(client)` returns a notes string
and raises on failure. Kept intentionally verbose/explicit so each snippet is a good
training example on its own.
"""

def _assert(cond, msg="assertion failed"):
    if not cond:
        raise AssertionError(msg)
    return True


CANDIDATES = []

# --------------------------------------------------------------------------- crud
CANDIDATES.append({
    "task": "Create a FastAPI app with an in-memory list of items and a GET /items endpoint that returns all items.",
    "category": "crud",
    "code": '''
from fastapi import FastAPI

app = FastAPI()
items = [{"id": 1, "name": "apple"}, {"id": 2, "name": "banana"}]

@app.get("/items")
def list_items():
    return items
''',
    "check": lambda c: (lambda r: (r.raise_for_status(), _assert(r.json() == [{"id":1,"name":"apple"},{"id":2,"name":"banana"}]), "GET /items -> 200 with 2 items")[-1])(c.get("/items")),
})

CANDIDATES.append({
    "task": "Create a FastAPI POST /items endpoint that accepts a JSON body with a name and returns the created item with an assigned integer id, using status code 201.",
    "category": "crud",
    "code": '''
from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI()
_db = {}
_counter = {"n": 0}

class ItemIn(BaseModel):
    name: str

@app.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(item: ItemIn):
    _counter["n"] += 1
    new = {"id": _counter["n"], "name": item.name}
    _db[new["id"]] = new
    return new
''',
    "check": lambda c: (lambda r: (_assert(r.status_code == 201, f"status {r.status_code}"), _assert(r.json()["id"] == 1 and r.json()["name"] == "pear"), "POST /items -> 201, id=1")[-1])(c.post("/items", json={"name": "pear"})),
})

CANDIDATES.append({
    "task": "Create a FastAPI GET /items/{item_id} endpoint that returns a single item by id, or 404 if it does not exist.",
    "category": "crud",
    "code": '''
from fastapi import FastAPI, HTTPException

app = FastAPI()
items = {1: {"id": 1, "name": "apple"}}

@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    return items[item_id]
''',
    "check": lambda c: (_assert(c.get("/items/1").json()["name"] == "apple"), _assert(c.get("/items/999").status_code == 404), "GET existing=200, missing=404")[-1],
})

CANDIDATES.append({
    "task": "Create a FastAPI PUT /items/{item_id} endpoint that fully updates an existing item and returns the updated item, or 404 if missing.",
    "category": "crud",
    "code": '''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
items = {1: {"id": 1, "name": "apple", "price": 1.0}}

class ItemUpdate(BaseModel):
    name: str
    price: float

@app.put("/items/{item_id}")
def update_item(item_id: int, item: ItemUpdate):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    items[item_id] = {"id": item_id, "name": item.name, "price": item.price}
    return items[item_id]
''',
    "check": lambda c: (_assert(c.put("/items/1", json={"name": "cherry", "price": 2.5}).json() == {"id": 1, "name": "cherry", "price": 2.5}), _assert(c.put("/items/9", json={"name": "x", "price": 1.0}).status_code == 404), "PUT updates, missing=404")[-1],
})

CANDIDATES.append({
    "task": "Create a FastAPI DELETE /items/{item_id} endpoint that deletes an item and returns 204 No Content, or 404 if missing.",
    "category": "crud",
    "code": '''
from fastapi import FastAPI, HTTPException, status

app = FastAPI()
items = {1: {"id": 1, "name": "apple"}}

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    del items[item_id]
    return None
''',
    "check": lambda c: (_assert(c.delete("/items/1").status_code == 204), _assert(c.delete("/items/1").status_code == 404), "DELETE existing=204, then 404")[-1],
})

CANDIDATES.append({
    "task": "Create a FastAPI PATCH /items/{item_id} endpoint that partially updates an item (only provided fields) and returns the updated item.",
    "category": "crud",
    "code": '''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()
items = {1: {"id": 1, "name": "apple", "price": 1.0}}

class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

@app.patch("/items/{item_id}")
def patch_item(item_id: int, patch: ItemPatch):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    stored = items[item_id]
    update = patch.model_dump(exclude_unset=True)
    stored.update(update)
    return stored
''',
    "check": lambda c: (_assert(c.patch("/items/1", json={"price": 9.0}).json() == {"id": 1, "name": "apple", "price": 9.0}), "PATCH only price changed")[-1],
})

CANDIDATES.append({
    "task": "Create a FastAPI app that manages a to-do list with in-memory storage supporting create (POST /todos) and list (GET /todos).",
    "category": "crud",
    "code": '''
from fastapi import FastAPI, status
from pydantic import BaseModel

app = FastAPI()
_todos = []

class TodoIn(BaseModel):
    title: str
    done: bool = False

@app.get("/todos")
def list_todos():
    return _todos

@app.post("/todos", status_code=status.HTTP_201_CREATED)
def add_todo(todo: TodoIn):
    record = {"id": len(_todos) + 1, "title": todo.title, "done": todo.done}
    _todos.append(record)
    return record
''',
    "check": lambda c: (_assert(c.post("/todos", json={"title": "buy milk"}).status_code == 201), _assert(len(c.get("/todos").json()) == 1), "create then list has 1")[-1],
})

CANDIDATES.append({
    "task": "Create a FastAPI endpoint POST /users that rejects a duplicate username with a 409 Conflict.",
    "category": "crud",
    "code": '''
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI()
_users = {}

class UserIn(BaseModel):
    username: str

@app.post("/users", status_code=201)
def create_user(user: UserIn):
    if user.username in _users:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username taken")
    _users[user.username] = {"username": user.username}
    return _users[user.username]
''',
    "check": lambda c: (_assert(c.post("/users", json={"username": "sam"}).status_code == 201), _assert(c.post("/users", json={"username": "sam"}).status_code == 409), "dup -> 409")[-1],
})

# ------------------------------------------------------------------- pydantic-models
CANDIDATES.append({
    "task": "Define a Pydantic model for a product with name (str), price (float > 0), and optional description, and expose it via POST /products.",
    "category": "pydantic-models",
    "code": '''
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

class Product(BaseModel):
    name: str
    price: float = Field(gt=0)
    description: Optional[str] = None

@app.post("/products")
def create_product(product: Product):
    return product
''',
    "check": lambda c: (_assert(c.post("/products", json={"name": "pen", "price": 1.5}).status_code == 200), _assert(c.post("/products", json={"name": "pen", "price": -1}).status_code == 422), "valid=200, price<=0 -> 422")[-1],
})

CANDIDATES.append({
    "task": "Create a FastAPI endpoint that uses a response_model to hide the password field from the response when creating a user.",
    "category": "pydantic-models",
    "code": '''
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class UserIn(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    username: str

@app.post("/register", response_model=UserOut)
def register(user: UserIn):
    return user
''',
    "check": lambda c: (lambda j: (_assert("password" not in j), _assert(j["username"] == "amy"), "password filtered from response")[-1])(c.post("/register", json={"username": "amy", "password": "secret"}).json()),
})

CANDIDATES.append({
    "task": "Create a Pydantic model with a nested model (an order containing a list of line items) and validate it via POST /orders.",
    "category": "pydantic-models",
    "code": '''
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

class LineItem(BaseModel):
    sku: str
    qty: int

class Order(BaseModel):
    customer: str
    items: List[LineItem]

@app.post("/orders")
def create_order(order: Order):
    total_qty = sum(i.qty for i in order.items)
    return {"customer": order.customer, "total_qty": total_qty}
''',
    "check": lambda c: (_assert(c.post("/orders", json={"customer": "bob", "items": [{"sku": "a", "qty": 2}, {"sku": "b", "qty": 3}]}).json()["total_qty"] == 5), "nested list summed to 5")[-1],
})

CANDIDATES.append({
    "task": "Create a Pydantic model that validates an email field and a string field with min/max length constraints.",
    "category": "pydantic-models",
    "code": '''
from fastapi import FastAPI
from pydantic import BaseModel, Field, EmailStr

app = FastAPI()

class Signup(BaseModel):
    email: EmailStr
    display_name: str = Field(min_length=3, max_length=20)

@app.post("/signup")
def signup(data: Signup):
    return {"email": data.email, "display_name": data.display_name}
''',
    "check": lambda c: (_assert(c.post("/signup", json={"email": "a@b.com", "display_name": "cleo"}).status_code == 200), _assert(c.post("/signup", json={"email": "notanemail", "display_name": "cleo"}).status_code == 422), _assert(c.post("/signup", json={"email": "a@b.com", "display_name": "xy"}).status_code == 422), "email + length validated")[-1],
})

CANDIDATES.append({
    "task": "Use a Pydantic field validator to ensure a password contains at least one digit.",
    "category": "pydantic-models",
    "code": '''
from fastapi import FastAPI
from pydantic import BaseModel, field_validator

app = FastAPI()

class Cred(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def has_digit(cls, v):
        if not any(ch.isdigit() for ch in v):
            raise ValueError("password must contain a digit")
        return v

@app.post("/cred")
def set_cred(cred: Cred):
    return {"ok": True}
''',
    "check": lambda c: (_assert(c.post("/cred", json={"password": "abc123"}).status_code == 200), _assert(c.post("/cred", json={"password": "abcdef"}).status_code == 422), "validator enforces digit")[-1],
})

CANDIDATES.append({
    "task": "Create a Pydantic model using an Enum field to constrain a status to one of {active, inactive, pending}.",
    "category": "pydantic-models",
    "code": '''
from fastapi import FastAPI
from pydantic import BaseModel
from enum import Enum

app = FastAPI()

class Status(str, Enum):
    active = "active"
    inactive = "inactive"
    pending = "pending"

class Account(BaseModel):
    name: str
    status: Status

@app.post("/accounts")
def create_account(account: Account):
    return {"name": account.name, "status": account.status.value}
''',
    "check": lambda c: (_assert(c.post("/accounts", json={"name": "n", "status": "active"}).json()["status"] == "active"), _assert(c.post("/accounts", json={"name": "n", "status": "bogus"}).status_code == 422), "enum constrained")[-1],
})

CANDIDATES.append({
    "task": "Create a response using response_model with a computed field returning a full name from first and last name.",
    "category": "pydantic-models",
    "code": '''
from fastapi import FastAPI
from pydantic import BaseModel, computed_field

app = FastAPI()

class PersonOut(BaseModel):
    first: str
    last: str

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first} {self.last}"

@app.get("/person", response_model=PersonOut)
def person():
    return {"first": "Ada", "last": "Lovelace"}
''',
    "check": lambda c: (_assert(c.get("/person").json()["full_name"] == "Ada Lovelace"), "computed full_name")[-1],
})

# ---------------------------------------------------------------- path-query-params
CANDIDATES.append({
    "task": "Create a FastAPI endpoint with a typed integer path parameter that squares the number.",
    "category": "path-query-params",
    "code": '''
from fastapi import FastAPI

app = FastAPI()

@app.get("/square/{n}")
def square(n: int):
    return {"n": n, "square": n * n}
''',
    "check": lambda c: (_assert(c.get("/square/5").json()["square"] == 25), _assert(c.get("/square/notint").status_code == 422), "typed path param")[-1],
})

CANDIDATES.append({
    "task": "Create a search endpoint GET /search with an optional query parameter q and a default limit of 10.",
    "category": "path-query-params",
    "code": '''
from fastapi import FastAPI
from typing import Optional

app = FastAPI()

@app.get("/search")
def search(q: Optional[str] = None, limit: int = 10):
    return {"q": q, "limit": limit}
''',
    "check": lambda c: (_assert(c.get("/search").json() == {"q": None, "limit": 10}), _assert(c.get("/search?q=cats&limit=5").json() == {"q": "cats", "limit": 5}), "optional q + default limit")[-1],
})

CANDIDATES.append({
    "task": "Create an endpoint that uses Query() to enforce a maximum limit of 100 on a query parameter.",
    "category": "path-query-params",
    "code": '''
from fastapi import FastAPI, Query

app = FastAPI()

@app.get("/feed")
def feed(limit: int = Query(default=20, ge=1, le=100)):
    return {"limit": limit}
''',
    "check": lambda c: (_assert(c.get("/feed").json()["limit"] == 20), _assert(c.get("/feed?limit=100").status_code == 200), _assert(c.get("/feed?limit=101").status_code == 422), _assert(c.get("/feed?limit=0").status_code == 422), "limit bounded 1..100")[-1],
})

CANDIDATES.append({
    "task": "Create an endpoint using Path() to validate that a path parameter id is greater than 0.",
    "category": "path-query-params",
    "code": '''
from fastapi import FastAPI, Path

app = FastAPI()

@app.get("/records/{record_id}")
def get_record(record_id: int = Path(gt=0)):
    return {"record_id": record_id}
''',
    "check": lambda c: (_assert(c.get("/records/5").status_code == 200), _assert(c.get("/records/0").status_code == 422), "path id>0")[-1],
})

CANDIDATES.append({
    "task": "Create an endpoint that accepts a list query parameter (e.g. ?tag=a&tag=b) and returns the list.",
    "category": "path-query-params",
    "code": '''
from fastapi import FastAPI, Query
from typing import List

app = FastAPI()

@app.get("/filter")
def filter_items(tag: List[str] = Query(default=[])):
    return {"tags": tag}
''',
    "check": lambda c: (_assert(c.get("/filter?tag=a&tag=b").json()["tags"] == ["a", "b"]), _assert(c.get("/filter").json()["tags"] == []), "repeated query -> list")[-1],
})

CANDIDATES.append({
    "task": "Create an endpoint with an Enum path parameter to select a model name from a fixed set.",
    "category": "path-query-params",
    "code": '''
from fastapi import FastAPI
from enum import Enum

app = FastAPI()

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"

@app.get("/models/{name}")
def get_model(name: ModelName):
    return {"model": name.value}
''',
    "check": lambda c: (_assert(c.get("/models/resnet").json()["model"] == "resnet"), _assert(c.get("/models/unknown").status_code == 422), "enum path")[-1],
})

# ------------------------------------------------------------- response-status-codes
CANDIDATES.append({
    "task": "Create a POST endpoint that explicitly returns HTTP 201 on creation.",
    "category": "response-status-codes",
    "code": '''
from fastapi import FastAPI, status

app = FastAPI()

@app.post("/things", status_code=status.HTTP_201_CREATED)
def create_thing():
    return {"created": True}
''',
    "check": lambda c: (_assert(c.post("/things").status_code == 201), "explicit 201")[-1],
})

CANDIDATES.append({
    "task": "Create a DELETE endpoint that returns 204 No Content with an empty body.",
    "category": "response-status-codes",
    "code": '''
from fastapi import FastAPI, status

app = FastAPI()

@app.delete("/things/{tid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thing(tid: int):
    return None
''',
    "check": lambda c: (lambda r: (_assert(r.status_code == 204), _assert(r.content == b""), "204 empty body")[-1])(c.delete("/things/1")),
})

CANDIDATES.append({
    "task": "Create an endpoint that returns a custom JSONResponse with a specific status code and header.",
    "category": "response-status-codes",
    "code": '''
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/teapot")
def teapot():
    return JSONResponse(status_code=418, content={"detail": "I'm a teapot"}, headers={"X-Brew": "tea"})
''',
    "check": lambda c: (lambda r: (_assert(r.status_code == 418), _assert(r.headers["X-Brew"] == "tea"), "custom JSONResponse 418 + header")[-1])(c.get("/teapot")),
})

CANDIDATES.append({
    "task": "Create an endpoint that returns plain text using PlainTextResponse.",
    "category": "response-status-codes",
    "code": '''
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.get("/ping", response_class=PlainTextResponse)
def ping():
    return "pong"
''',
    "check": lambda c: (lambda r: (_assert(r.text == "pong"), _assert(r.headers["content-type"].startswith("text/plain")), "plain text pong")[-1])(c.get("/ping")),
})

CANDIDATES.append({
    "task": "Create an endpoint using response_model_exclude to omit a field from the serialized response.",
    "category": "response-status-codes",
    "code": '''
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    id: int
    name: str
    secret: str

@app.get("/item", response_model=Item, response_model_exclude={"secret"})
def get_item():
    return {"id": 1, "name": "widget", "secret": "hidden"}
''',
    "check": lambda c: (lambda j: (_assert("secret" not in j), _assert(j["name"] == "widget"), "secret excluded")[-1])(c.get("/item").json()),
})

# --------------------------------------------------------------------- error-handling
CANDIDATES.append({
    "task": "Create an endpoint that raises HTTPException with status 400 and a detail message when a divisor is zero.",
    "category": "error-handling",
    "code": '''
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/divide")
def divide(a: float, b: float):
    if b == 0:
        raise HTTPException(status_code=400, detail="division by zero")
    return {"result": a / b}
''',
    "check": lambda c: (_assert(c.get("/divide?a=6&b=3").json()["result"] == 2), lambda: None, _assert(c.get("/divide?a=6&b=0").status_code == 400), _assert(c.get("/divide?a=6&b=0").json()["detail"] == "division by zero"), "400 on zero divisor")[-1],
})

CANDIDATES.append({
    "task": "Register a custom exception handler for a domain-specific exception that returns a 422 with a custom body.",
    "category": "error-handling",
    "code": '''
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

class OutOfStock(Exception):
    def __init__(self, sku: str):
        self.sku = sku

@app.exception_handler(OutOfStock)
def out_of_stock_handler(request: Request, exc: OutOfStock):
    return JSONResponse(status_code=422, content={"error": "out_of_stock", "sku": exc.sku})

@app.post("/buy/{sku}")
def buy(sku: str):
    if sku == "empty":
        raise OutOfStock(sku)
    return {"bought": sku}
''',
    "check": lambda c: (lambda r: (_assert(r.status_code == 422), _assert(r.json() == {"error": "out_of_stock", "sku": "empty"}), "custom handler 422")[-1])(c.post("/buy/empty")),
})

CANDIDATES.append({
    "task": "Add custom headers to an HTTPException response (e.g. an X-Error header).",
    "category": "error-handling",
    "code": '''
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/secure")
def secure():
    raise HTTPException(status_code=401, detail="unauthorized", headers={"X-Error": "no-token"})
''',
    "check": lambda c: (lambda r: (_assert(r.status_code == 401), _assert(r.headers["X-Error"] == "no-token"), "exception header set")[-1])(c.get("/secure")),
})

CANDIDATES.append({
    "task": "Override the default RequestValidationError handler to return a simplified error payload.",
    "category": "error-handling",
    "code": '''
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

class Payload(BaseModel):
    count: int

@app.exception_handler(RequestValidationError)
def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "invalid_input", "fields": len(exc.errors())})

@app.post("/payload")
def submit(payload: Payload):
    return {"count": payload.count}
''',
    "check": lambda c: (lambda r: (_assert(r.status_code == 400), _assert(r.json()["error"] == "invalid_input"), "custom validation handler")[-1])(c.post("/payload", json={"count": "not-a-number"})),
})

CANDIDATES.append({
    "task": "Create an endpoint that returns a 404 with a JSON detail when a resource key is not found in a dict store.",
    "category": "error-handling",
    "code": '''
from fastapi import FastAPI, HTTPException

app = FastAPI()
store = {"a": 1}

@app.get("/store/{key}")
def read(key: str):
    if key not in store:
        raise HTTPException(status_code=404, detail=f"key '{key}' not found")
    return {"key": key, "value": store[key]}
''',
    "check": lambda c: (_assert(c.get("/store/a").json()["value"] == 1), _assert(c.get("/store/z").status_code == 404), "missing key 404")[-1],
})

CANDIDATES.append({
    "task": "Create an endpoint that validates business logic and raises a 400 when an age is negative.",
    "category": "error-handling",
    "code": '''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Person(BaseModel):
    name: str
    age: int

@app.post("/people")
def add_person(p: Person):
    if p.age < 0:
        raise HTTPException(status_code=400, detail="age cannot be negative")
    return {"name": p.name, "age": p.age}
''',
    "check": lambda c: (_assert(c.post("/people", json={"name": "x", "age": 5}).status_code == 200), _assert(c.post("/people", json={"name": "x", "age": -1}).status_code == 400), "negative age 400")[-1],
})

# ------------------------------------------------------------- dependency-injection
CANDIDATES.append({
    "task": "Create a shared dependency that supplies common pagination parameters (skip, limit) to multiple endpoints.",
    "category": "dependency-injection",
    "code": '''
from fastapi import FastAPI, Depends

app = FastAPI()

def pagination(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}

@app.get("/a")
def endpoint_a(p: dict = Depends(pagination)):
    return {"endpoint": "a", **p}

@app.get("/b")
def endpoint_b(p: dict = Depends(pagination)):
    return {"endpoint": "b", **p}
''',
    "check": lambda c: (_assert(c.get("/a?skip=5").json() == {"endpoint": "a", "skip": 5, "limit": 10}), _assert(c.get("/b?limit=3").json()["limit"] == 3), "shared dependency reused")[-1],
})

CANDIDATES.append({
    "task": "Create a class-based dependency that holds configuration and is injected into an endpoint.",
    "category": "dependency-injection",
    "code": '''
from fastapi import FastAPI, Depends

app = FastAPI()

class Settings:
    def __init__(self, app_name: str = "demo"):
        self.app_name = app_name

def get_settings():
    return Settings(app_name="myapp")

@app.get("/config")
def config(settings: Settings = Depends(get_settings)):
    return {"app_name": settings.app_name}
''',
    "check": lambda c: (_assert(c.get("/config").json()["app_name"] == "myapp"), "class dependency injected")[-1],
})

CANDIDATES.append({
    "task": "Create a dependency that validates an API key from a header and returns 401 when missing or wrong.",
    "category": "dependency-injection",
    "code": '''
from fastapi import FastAPI, Depends, HTTPException, Header
from typing import Optional

app = FastAPI()
VALID_KEY = "s3cr3t"

def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if x_api_key != VALID_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")
    return x_api_key

@app.get("/protected", dependencies=[Depends(require_api_key)])
def protected():
    return {"ok": True}
''',
    "check": lambda c: (_assert(c.get("/protected").status_code == 401), _assert(c.get("/protected", headers={"x-api-key": "s3cr3t"}).status_code == 200), "api key dependency guards route")[-1],
})

CANDIDATES.append({
    "task": "Create a sub-dependency chain where one dependency depends on another.",
    "category": "dependency-injection",
    "code": '''
from fastapi import FastAPI, Depends

app = FastAPI()

def query_extractor(q: str = "default"):
    return q

def query_or_default(q: str = Depends(query_extractor)):
    return q.upper()

@app.get("/echo")
def echo(value: str = Depends(query_or_default)):
    return {"value": value}
''',
    "check": lambda c: (_assert(c.get("/echo?q=hello").json()["value"] == "HELLO"), _assert(c.get("/echo").json()["value"] == "DEFAULT"), "sub-dependency chain")[-1],
})

CANDIDATES.append({
    "task": "Create a dependency with yield that sets up and tears down a resource (setup/teardown pattern).",
    "category": "dependency-injection",
    "code": '''
from fastapi import FastAPI, Depends

app = FastAPI()
events = []

def get_resource():
    events.append("open")
    try:
        yield {"conn": "live"}
    finally:
        events.append("close")

@app.get("/use")
def use(res: dict = Depends(get_resource)):
    return {"conn": res["conn"], "events_so_far": list(events)}
''',
    "check": lambda c: (lambda r: (_assert(r.json()["conn"] == "live"), _assert(r.json()["events_so_far"][-1] == "open"), "yield dependency setup/teardown")[-1])(c.get("/use")),
})

CANDIDATES.append({
    "task": "Use dependency_overrides in tests to swap a dependency, demonstrating testability.",
    "category": "dependency-injection",
    "code": '''
from fastapi import FastAPI, Depends

app = FastAPI()

def get_db():
    return {"env": "prod"}

@app.get("/env")
def env(db: dict = Depends(get_db)):
    return db

def fake_db():
    return {"env": "test"}

app.dependency_overrides[get_db] = fake_db
''',
    "check": lambda c: (_assert(c.get("/env").json()["env"] == "test"), "dependency override applied")[-1],
})
