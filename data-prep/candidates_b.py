# -*- coding: utf-8 -*-
"""Candidate task->code pairs, part B: auth-jwt, pagination, database-sqlalchemy,
background-tasks, file-upload, routing-structure, middleware-cors."""


def _assert(cond, msg="assertion failed"):
    if not cond:
        raise AssertionError(msg)
    return True


CANDIDATES = []

# --------------------------------------------------------------------------- auth-jwt
CANDIDATES.append({
    "task": "Create a FastAPI login endpoint (POST /login) that verifies a hardcoded user with bcrypt and returns a JWT access token.",
    "category": "auth-jwt",
    "code": '''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt

app = FastAPI()
SECRET = "change-me"
ALGO = "HS256"
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_users = {"alice": pwd.hash("wonderland")}

class LoginIn(BaseModel):
    username: str
    password: str

@app.post("/login")
def login(data: LoginIn):
    hashed = _users.get(data.username)
    if not hashed or not pwd.verify(data.password, hashed):
        raise HTTPException(status_code=401, detail="bad credentials")
    token = jwt.encode({"sub": data.username}, SECRET, algorithm=ALGO)
    return {"access_token": token, "token_type": "bearer"}
''',
    "check": lambda c: (lambda r: (_assert(r.status_code == 200), _assert(set(r.json()) == {"access_token", "token_type"}), _assert(c.post("/login", json={"username": "alice", "password": "wrong"}).status_code == 401), "login issues JWT, wrong pw 401")[-1])(c.post("/login", json={"username": "alice", "password": "wonderland"})),
})

CANDIDATES.append({
    "task": "Create a protected endpoint GET /me that requires a valid JWT bearer token via OAuth2PasswordBearer and returns the current user.",
    "category": "auth-jwt",
    "code": '''
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

app = FastAPI()
SECRET = "change-me"
ALGO = "HS256"
oauth2 = OAuth2PasswordBearer(tokenUrl="login")

def make_token(sub):
    return jwt.encode({"sub": sub}, SECRET, algorithm=ALGO)

def get_current_user(token: str = Depends(oauth2)):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid token")
    return payload["sub"]

@app.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"user": user}

@app.get("/token-for-test")
def token_for_test():
    return {"token": make_token("bob")}
''',
    "check": lambda c: (lambda tok: (_assert(c.get("/me").status_code == 401), _assert(c.get("/me", headers={"Authorization": f"Bearer {tok}"}).json() == {"user": "bob"}), _assert(c.get("/me", headers={"Authorization": "Bearer garbage"}).status_code == 401), "JWT-protected route")[-1])(c.get("/token-for-test").json()["token"]),
})

CANDIDATES.append({
    "task": "Create a full login flow using OAuth2PasswordRequestForm that returns a JWT token from form-encoded credentials.",
    "category": "auth-jwt",
    "code": '''
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt

app = FastAPI()
SECRET = "k"
_users = {"user1": "pass1"}

@app.post("/token")
def token(form: OAuth2PasswordRequestForm = Depends()):
    if _users.get(form.username) != form.password:
        raise HTTPException(status_code=401, detail="bad creds")
    access = jwt.encode({"sub": form.username}, SECRET, algorithm="HS256")
    return {"access_token": access, "token_type": "bearer"}
''',
    "check": lambda c: (lambda r: (_assert(r.status_code == 200), _assert(r.json()["token_type"] == "bearer"), _assert(c.post("/token", data={"username": "user1", "password": "nope"}).status_code == 401), "form-based OAuth2 token")[-1])(c.post("/token", data={"username": "user1", "password": "pass1"})),
})

CANDIDATES.append({
    "task": "Create a JWT that includes an expiry claim and an endpoint that rejects an already-expired token with 401.",
    "category": "auth-jwt",
    "code": '''
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone

app = FastAPI()
SECRET = "k"
oauth2 = OAuth2PasswordBearer(tokenUrl="login")

def make_token(sub, minutes):
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({"sub": sub, "exp": exp}, SECRET, algorithm="HS256")

def current_user(token: str = Depends(oauth2)):
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="expired or invalid")
    return payload["sub"]

@app.get("/profile")
def profile(user: str = Depends(current_user)):
    return {"user": user}

@app.get("/expired-token")
def expired_token():
    return {"token": make_token("z", -1)}

@app.get("/valid-token")
def valid_token():
    return {"token": make_token("z", 10)}
''',
    "check": lambda c: (_assert(c.get("/profile", headers={"Authorization": "Bearer " + c.get("/expired-token").json()["token"]}).status_code == 401), _assert(c.get("/profile", headers={"Authorization": "Bearer " + c.get("/valid-token").json()["token"]}).status_code == 200), "expired token rejected")[-1],
})

CANDIDATES.append({
    "task": "Hash a password with bcrypt on registration and verify it on login, storing only the hash.",
    "category": "auth-jwt",
    "code": '''
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from passlib.context import CryptContext

app = FastAPI()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_store = {}

class Cred(BaseModel):
    username: str
    password: str

@app.post("/register", status_code=201)
def register(c: Cred):
    _store[c.username] = pwd.hash(c.password)
    return {"username": c.username}

@app.post("/verify")
def verify(c: Cred):
    h = _store.get(c.username)
    ok = bool(h) and pwd.verify(c.password, h)
    if not ok:
        raise HTTPException(status_code=401, detail="no")
    return {"verified": True}
''',
    "check": lambda c: (_assert(c.post("/register", json={"username": "u", "password": "p@ss"}).status_code == 201), _assert(c.post("/verify", json={"username": "u", "password": "p@ss"}).json()["verified"] is True), _assert(c.post("/verify", json={"username": "u", "password": "x"}).status_code == 401), "bcrypt register+verify")[-1],
})

CANDIDATES.append({
    "task": "Create a role-based dependency that only allows users whose JWT contains role=admin to access an endpoint.",
    "category": "auth-jwt",
    "code": '''
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError

app = FastAPI()
SECRET = "k"
oauth2 = OAuth2PasswordBearer(tokenUrl="login")

def token_for(role):
    return jwt.encode({"sub": "u", "role": role}, SECRET, algorithm="HS256")

def require_admin(token: str = Depends(oauth2)):
    try:
        payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid")
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="forbidden")
    return payload["sub"]

@app.get("/admin", dependencies=[Depends(require_admin)])
def admin_area():
    return {"area": "admin"}

@app.get("/mint/{role}")
def mint(role: str):
    return {"token": token_for(role)}
''',
    "check": lambda c: (_assert(c.get("/admin", headers={"Authorization": "Bearer " + c.get("/mint/user").json()["token"]}).status_code == 403), _assert(c.get("/admin", headers={"Authorization": "Bearer " + c.get("/mint/admin").json()["token"]}).status_code == 200), "role check 403 vs 200")[-1],
})

CANDIDATES.append({
    "task": "Return 401 with WWW-Authenticate: Bearer header when no token is supplied to a protected route.",
    "category": "auth-jwt",
    "code": '''
from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()
oauth2 = OAuth2PasswordBearer(tokenUrl="login")

@app.get("/secret")
def secret(token: str = Depends(oauth2)):
    return {"token_seen": bool(token)}
''',
    "check": lambda c: (lambda r: (_assert(r.status_code == 401), _assert(r.headers.get("www-authenticate", "").lower() == "bearer"), "401 + WWW-Authenticate")[-1])(c.get("/secret")),
})

# ------------------------------------------------------------------------- pagination
CANDIDATES.append({
    "task": "Create a GET /users endpoint that paginates an in-memory list using skip and limit query parameters.",
    "category": "pagination",
    "code": '''
from fastapi import FastAPI, Query

app = FastAPI()
_users = [{"id": i, "name": f"user{i}"} for i in range(1, 101)]

@app.get("/users")
def list_users(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    return _users[skip: skip + limit]
''',
    "check": lambda c: (_assert(len(c.get("/users").json()) == 10), _assert(c.get("/users?skip=0&limit=5").json()[0]["id"] == 1), _assert(c.get("/users?skip=10&limit=5").json()[0]["id"] == 11), "skip/limit pagination")[-1],
})

CANDIDATES.append({
    "task": "Create a paginated endpoint that returns an envelope with items, total, page, and size.",
    "category": "pagination",
    "code": '''
from fastapi import FastAPI, Query

app = FastAPI()
_data = list(range(1, 46))  # 45 records

@app.get("/records")
def records(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100)):
    start = (page - 1) * size
    items = _data[start: start + size]
    return {"items": items, "total": len(_data), "page": page, "size": size}
''',
    "check": lambda c: (lambda j: (_assert(j["total"] == 45), _assert(j["page"] == 2), _assert(j["items"][0] == 11), _assert(len(j["items"]) == 10), "page envelope")[-1])(c.get("/records?page=2&size=10").json()),
})

CANDIDATES.append({
    "task": "Create a paginated endpoint whose last page returns the remaining (partial) items only.",
    "category": "pagination",
    "code": '''
from fastapi import FastAPI, Query

app = FastAPI()
_data = list(range(1, 26))  # 25 records

@app.get("/page")
def page(page: int = Query(1, ge=1), size: int = Query(10, ge=1)):
    start = (page - 1) * size
    return {"items": _data[start:start + size]}
''',
    "check": lambda c: (_assert(len(c.get("/page?page=3&size=10").json()["items"]) == 5), _assert(c.get("/page?page=4&size=10").json()["items"] == []), "partial last page")[-1],
})

CANDIDATES.append({
    "task": "Create a pagination endpoint that computes and returns total_pages given a page size.",
    "category": "pagination",
    "code": '''
from fastapi import FastAPI, Query
import math

app = FastAPI()
_data = list(range(1, 34))  # 33 records

@app.get("/list")
def list_endpoint(page: int = Query(1, ge=1), size: int = Query(10, ge=1)):
    total = len(_data)
    total_pages = math.ceil(total / size)
    start = (page - 1) * size
    return {"items": _data[start:start + size], "total_pages": total_pages}
''',
    "check": lambda c: (_assert(c.get("/list?size=10").json()["total_pages"] == 4), _assert(c.get("/list?size=33").json()["total_pages"] == 1), "total_pages computed")[-1],
})

CANDIDATES.append({
    "task": "Reject an out-of-range page size above the allowed maximum with a 422.",
    "category": "pagination",
    "code": '''
from fastapi import FastAPI, Query

app = FastAPI()
_data = list(range(50))

@app.get("/paged")
def paged(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=50)):
    start = (page - 1) * size
    return {"items": _data[start:start + size]}
''',
    "check": lambda c: (_assert(c.get("/paged?size=50").status_code == 200), _assert(c.get("/paged?size=51").status_code == 422), "size cap enforced")[-1],
})

# ------------------------------------------------------------------ database-sqlalchemy
CANDIDATES.append({
    "task": "Set up SQLAlchemy with an in-memory SQLite database, a User model, and a GET/POST /users CRUD using a session dependency.",
    "category": "database-sqlalchemy",
    "code": '''
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class UserIn(BaseModel):
    name: str

class UserOut(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

@app.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserIn, db: Session = Depends(get_db)):
    user = User(name=payload.name)
    db.add(user); db.commit(); db.refresh(user)
    return user

@app.get("/users/{uid}", response_model=UserOut)
def get_user(uid: int, db: Session = Depends(get_db)):
    user = db.get(User, uid)
    if not user:
        raise HTTPException(status_code=404, detail="not found")
    return user
''',
    "check": lambda c: (lambda r: (_assert(r.status_code == 201), _assert(r.json()["id"] == 1), _assert(c.get(f"/users/{r.json()['id']}").json()["name"] == "dana"), _assert(c.get("/users/999").status_code == 404), "SQLAlchemy CRUD roundtrip")[-1])(c.post("/users", json={"name": "dana"})),
})

CANDIDATES.append({
    "task": "Create a SQLAlchemy-backed GET /products list endpoint that returns all rows via a session dependency.",
    "category": "database-sqlalchemy",
    "code": '''
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)

Base.metadata.create_all(bind=engine)

# seed
_s = SessionLocal()
_s.add_all([Product(name="a"), Product(name="b")])
_s.commit(); _s.close()

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/products")
def products(db: Session = Depends(get_db)):
    return [{"id": p.id, "name": p.name} for p in db.query(Product).all()]
''',
    "check": lambda c: (_assert(len(c.get("/products").json()) == 2), _assert(c.get("/products").json()[0]["name"] == "a"), "list from DB")[-1],
})

CANDIDATES.append({
    "task": "Create a SQLAlchemy delete endpoint that removes a row and returns 204, or 404 if not present.",
    "category": "database-sqlalchemy",
    "code": '''
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    text = Column(String)

Base.metadata.create_all(bind=engine)
_s = SessionLocal(); _s.add(Note(id=1, text="hi")); _s.commit(); _s.close()

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.delete("/notes/{nid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(nid: int, db: Session = Depends(get_db)):
    obj = db.get(Note, nid)
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(obj); db.commit()
    return None
''',
    "check": lambda c: (_assert(c.delete("/notes/1").status_code == 204), _assert(c.delete("/notes/1").status_code == 404), "DB delete 204 then 404")[-1],
})

CANDIDATES.append({
    "task": "Create a SQLAlchemy update endpoint (PUT) that modifies a row's fields and returns the updated record.",
    "category": "database-sqlalchemy",
    "code": '''
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String)

Base.metadata.create_all(bind=engine)
_s = SessionLocal(); _s.add(Task(id=1, title="old")); _s.commit(); _s.close()

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class TaskIn(BaseModel):
    title: str

@app.put("/tasks/{tid}")
def update_task(tid: int, payload: TaskIn, db: Session = Depends(get_db)):
    obj = db.get(Task, tid)
    if not obj:
        raise HTTPException(status_code=404, detail="not found")
    obj.title = payload.title
    db.commit(); db.refresh(obj)
    return {"id": obj.id, "title": obj.title}
''',
    "check": lambda c: (_assert(c.put("/tasks/1", json={"title": "new"}).json() == {"id": 1, "title": "new"}), _assert(c.put("/tasks/9", json={"title": "x"}).status_code == 404), "DB update")[-1],
})

CANDIDATES.append({
    "task": "Create a SQLAlchemy endpoint that filters rows by a query parameter (case-insensitive name search).",
    "category": "database-sqlalchemy",
    "code": '''
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class City(Base):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True)
    name = Column(String)

Base.metadata.create_all(bind=engine)
_s = SessionLocal(); _s.add_all([City(name="London"), City(name="Lisbon"), City(name="Paris")]); _s.commit(); _s.close()

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/cities")
def cities(q: str = "", db: Session = Depends(get_db)):
    rows = db.query(City).filter(City.name.ilike(f"%{q}%")).all()
    return [r.name for r in rows]
''',
    "check": lambda c: (_assert(sorted(c.get("/cities?q=l").json()) == ["Lisbon", "London"]), _assert(c.get("/cities?q=paris").json() == ["Paris"]), "ilike filter")[-1],
})

# ------------------------------------------------------------------- background-tasks
CANDIDATES.append({
    "task": "Create an endpoint that schedules a background task to append to a log after returning the response.",
    "category": "background-tasks",
    "code": '''
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()
_log = []

def write_log(message: str):
    _log.append(message)

@app.post("/notify")
def notify(msg: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(write_log, msg)
    return {"queued": True}

@app.get("/log")
def get_log():
    return _log
''',
    "check": lambda c: (_assert(c.post("/notify?msg=hello").json() == {"queued": True}), _assert("hello" in c.get("/log").json()), "background task ran")[-1],
})

CANDIDATES.append({
    "task": "Create an endpoint that uses a background task to increment a counter, and verify the side effect.",
    "category": "background-tasks",
    "code": '''
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()
_state = {"count": 0}

def bump(n: int):
    _state["count"] += n

@app.post("/bump")
def do_bump(n: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(bump, n)
    return {"scheduled": n}

@app.get("/count")
def count():
    return _state
''',
    "check": lambda c: (c.post("/bump?n=3"), c.post("/bump?n=4"), _assert(c.get("/count").json()["count"] == 7), "counter bumped in background")[-1],
})

CANDIDATES.append({
    "task": "Create an endpoint that passes a background task added by a dependency (reusable background side-effect).",
    "category": "background-tasks",
    "code": '''
from fastapi import FastAPI, BackgroundTasks, Depends

app = FastAPI()
_audit = []

def audit_dep(background_tasks: BackgroundTasks):
    background_tasks.add_task(_audit.append, "accessed")
    return True

@app.get("/resource", dependencies=[Depends(audit_dep)])
def resource():
    return {"data": 1}

@app.get("/audit")
def audit():
    return _audit
''',
    "check": lambda c: (c.get("/resource"), _assert(c.get("/audit").json() == ["accessed"]), "dependency-scheduled background task")[-1],
})

CANDIDATES.append({
    "task": "Create an endpoint that schedules multiple background tasks that run in order.",
    "category": "background-tasks",
    "code": '''
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()
_seq = []

@app.post("/multi")
def multi(background_tasks: BackgroundTasks):
    background_tasks.add_task(_seq.append, "a")
    background_tasks.add_task(_seq.append, "b")
    background_tasks.add_task(_seq.append, "c")
    return {"ok": True}

@app.get("/seq")
def seq():
    return _seq
''',
    "check": lambda c: (c.post("/multi"), _assert(c.get("/seq").json() == ["a", "b", "c"]), "ordered background tasks")[-1],
})

# ------------------------------------------------------------------------ file-upload
CANDIDATES.append({
    "task": "Create an endpoint that accepts an uploaded file and returns its filename and byte size.",
    "category": "file-upload",
    "code": '''
from fastapi import FastAPI, UploadFile, File

app = FastAPI()

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    return {"filename": file.filename, "size": len(content)}
''',
    "check": lambda c: (lambda j: (_assert(j["filename"] == "hi.txt"), _assert(j["size"] == 5), "upload filename+size")[-1])(c.post("/upload", files={"file": ("hi.txt", b"hello", "text/plain")}).json()),
})

CANDIDATES.append({
    "task": "Create an endpoint that accepts a file plus a form field (description) via multipart form data.",
    "category": "file-upload",
    "code": '''
from fastapi import FastAPI, UploadFile, File, Form

app = FastAPI()

@app.post("/docs")
async def docs(description: str = Form(...), file: UploadFile = File(...)):
    data = await file.read()
    return {"description": description, "filename": file.filename, "bytes": len(data)}
''',
    "check": lambda c: (lambda j: (_assert(j["description"] == "notes"), _assert(j["filename"] == "a.bin"), _assert(j["bytes"] == 3), "file + form field")[-1])(c.post("/docs", data={"description": "notes"}, files={"file": ("a.bin", b"abc")}).json()),
})

CANDIDATES.append({
    "task": "Create an endpoint that rejects an uploaded file with a 400 when its content type is not text/csv.",
    "category": "file-upload",
    "code": '''
from fastapi import FastAPI, UploadFile, File, HTTPException

app = FastAPI()

@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    if file.content_type != "text/csv":
        raise HTTPException(status_code=400, detail="only CSV allowed")
    content = await file.read()
    rows = content.decode().strip().splitlines()
    return {"rows": len(rows)}
''',
    "check": lambda c: (_assert(c.post("/import", files={"file": ("d.csv", b"a,b\n1,2", "text/csv")}).json()["rows"] == 2), _assert(c.post("/import", files={"file": ("d.png", b"x", "image/png")}).status_code == 400), "content-type gate")[-1],
})

CANDIDATES.append({
    "task": "Create an endpoint that accepts multiple uploaded files and returns the count and total size.",
    "category": "file-upload",
    "code": '''
from fastapi import FastAPI, UploadFile, File
from typing import List

app = FastAPI()

@app.post("/batch")
async def batch(files: List[UploadFile] = File(...)):
    total = 0
    for f in files:
        total += len(await f.read())
    return {"count": len(files), "total_size": total}
''',
    "check": lambda c: (lambda j: (_assert(j["count"] == 2), _assert(j["total_size"] == 7), "multi-file upload")[-1])(c.post("/batch", files=[("files", ("a.txt", b"abc")), ("files", ("b.txt", b"defg"))]).json()),
})

# ------------------------------------------------------------------- routing-structure
CANDIDATES.append({
    "task": "Create an APIRouter with a prefix /items and a tag, then include it in the main app.",
    "category": "routing-structure",
    "code": '''
from fastapi import FastAPI, APIRouter

router = APIRouter(prefix="/items", tags=["items"])

@router.get("/")
def list_items():
    return ["a", "b"]

@router.get("/{item_id}")
def get_item(item_id: int):
    return {"item_id": item_id}

app = FastAPI()
app.include_router(router)
''',
    "check": lambda c: (_assert(c.get("/items/").json() == ["a", "b"]), _assert(c.get("/items/7").json() == {"item_id": 7}), "router prefix mounted")[-1],
})

CANDIDATES.append({
    "task": "Create two APIRouters (users and posts) with separate prefixes and mount both on the app.",
    "category": "routing-structure",
    "code": '''
from fastapi import FastAPI, APIRouter

users = APIRouter(prefix="/users", tags=["users"])
posts = APIRouter(prefix="/posts", tags=["posts"])

@users.get("/")
def list_users():
    return ["alice"]

@posts.get("/")
def list_posts():
    return ["post1"]

app = FastAPI()
app.include_router(users)
app.include_router(posts)
''',
    "check": lambda c: (_assert(c.get("/users/").json() == ["alice"]), _assert(c.get("/posts/").json() == ["post1"]), "two routers mounted")[-1],
})

CANDIDATES.append({
    "task": "Create an APIRouter with a router-level dependency applied to all its routes.",
    "category": "routing-structure",
    "code": '''
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Header
from typing import Optional

def require_token(x_token: Optional[str] = Header(default=None)):
    if x_token != "let-me-in":
        raise HTTPException(status_code=401, detail="no")

admin = APIRouter(prefix="/admin", dependencies=[Depends(require_token)])

@admin.get("/stats")
def stats():
    return {"ok": True}

app = FastAPI()
app.include_router(admin)
''',
    "check": lambda c: (_assert(c.get("/admin/stats").status_code == 401), _assert(c.get("/admin/stats", headers={"x-token": "let-me-in"}).status_code == 200), "router-level dependency")[-1],
})

CANDIDATES.append({
    "task": "Create an app with a versioned API by mounting a router under a /api/v1 prefix.",
    "category": "routing-structure",
    "code": '''
from fastapi import FastAPI, APIRouter

v1 = APIRouter()

@v1.get("/health")
def health():
    return {"status": "ok"}

app = FastAPI()
app.include_router(v1, prefix="/api/v1")
''',
    "check": lambda c: (_assert(c.get("/api/v1/health").json() == {"status": "ok"}), _assert(c.get("/health").status_code == 404), "versioned prefix")[-1],
})

# -------------------------------------------------------------------- middleware-cors
CANDIDATES.append({
    "task": "Configure CORSMiddleware to allow a specific origin and verify the CORS header on the response.",
    "category": "middleware-cors",
    "code": '''
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/data")
def data():
    return {"data": 1}
''',
    "check": lambda c: (lambda r: (_assert(r.status_code == 200), _assert(r.headers.get("access-control-allow-origin") == "https://example.com"), "CORS origin echoed")[-1])(c.get("/data", headers={"Origin": "https://example.com"})),
})

CANDIDATES.append({
    "task": "Write a custom HTTP middleware that adds an X-Process-Time header to every response.",
    "category": "middleware-cors",
    "code": '''
import time
from fastapi import FastAPI, Request

app = FastAPI()

@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.perf_counter() - start)
    return response

@app.get("/")
def root():
    return {"hello": "world"}
''',
    "check": lambda c: (lambda r: (_assert("x-process-time" in r.headers), _assert(float(r.headers["x-process-time"]) >= 0), "process-time header added")[-1])(c.get("/")),
})

CANDIDATES.append({
    "task": "Write a custom middleware that rejects requests missing an X-Client header with a 400.",
    "category": "middleware-cors",
    "code": '''
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.middleware("http")
async def require_client(request: Request, call_next):
    if "x-client" not in request.headers:
        return JSONResponse(status_code=400, content={"detail": "missing X-Client"})
    return await call_next(request)

@app.get("/")
def root():
    return {"ok": True}
''',
    "check": lambda c: (_assert(c.get("/").status_code == 400), _assert(c.get("/", headers={"x-client": "web"}).status_code == 200), "middleware gate on header")[-1],
})

CANDIDATES.append({
    "task": "Configure CORS to allow credentials and a preflight OPTIONS request from an allowed origin.",
    "category": "middleware-cors",
    "code": '''
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.local"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.post("/submit")
def submit():
    return {"ok": True}
''',
    "check": lambda c: (lambda r: (_assert(r.status_code in (200, 204)), _assert(r.headers.get("access-control-allow-origin") == "https://app.local"), "preflight allowed")[-1])(c.options("/submit", headers={"Origin": "https://app.local", "Access-Control-Request-Method": "POST"})),
})
