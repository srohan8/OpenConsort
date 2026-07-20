# FastAPI Backend Specialist — Task Categories

**Purpose:** This document defines the task categories used to generate the training
dataset (`fastapi-backend-pairs.jsonl`) and the held-out evaluation suite
(`fastapi-eval-suite.jsonl`) for the FastAPI backend specialist model (Phase 1 combo:
FastAPI + React/Vite, PostgreSQL, JWT auth).

The categories below were chosen by cross-referencing three sources rather than inventing
them from general knowledge alone:

1. The **official FastAPI tutorial** table of contents (fastapi.tiangolo.com/tutorial/),
   which is the de-facto canonical curriculum: path/query params, request body &
   Pydantic models, response models, dependencies, security/OAuth2+JWT, error handling,
   background tasks, SQL databases, bigger-applications (APIRouter), middleware & CORS,
   file uploads, testing.
2. **Common real-world FastAPI project structure** (the widely-copied
   `models / schemas / crud / api / core(security) / deps` layering seen in
   full-stack-fastapi templates and "best architecture" repos) — confirms the
   model/schema/CRUD/service/DI split maps onto real code, not just tutorials.
3. The **Phase 1 locked stack** from the architecture doc — JWT auth (not sessions),
   PostgreSQL/SQLAlchemy, API-first CRUD, role/permission dependencies — which biases
   category weighting toward what this specialist will actually be asked to emit.

Scope note: **backend only.** No frontend/React pairs. Payments (Stripe) is deliberately
excluded — the architecture treats it as a separate shared module, not something this
specialist generates.

---

## Categories

### 1. `crud` — Basic CRUD endpoints
Create/read/update/delete over a resource, the single most common request shape ("build
an API for X"). Covers `POST/GET/PUT/PATCH/DELETE`, path parameters for item lookup,
returning 404 for missing items, and 201 on create. In-memory store is fine at the
snippet level; the DB-backed version lives in `database-sqlalchemy`.
**Rationale:** This is the "generic CRUD app with an API" case the architecture doc names
as the highest-demand bucket. It is the backbone category.

### 2. `pydantic-models` — Request/response models & validation
Defining `BaseModel` request bodies and response models, field types, optional/default
fields, nested models, `Field(...)` constraints (min/max length, ge/le, regex), and
`response_model` to shape/filter output (e.g. stripping a password field).
**Rationale:** Pydantic validation is FastAPI's headline feature and appears in nearly
every endpoint. Worth isolating so the model learns validation independently of routing.

### 3. `path-query-params` — Path & query parameter handling
Typed path params, query params with defaults, optional queries, enums for constrained
values, and validation via `Path()`/`Query()` (e.g. `Query(default=10, le=100)`).
**Rationale:** Distinct skill from body validation; the FastAPI tutorial dedicates several
early chapters to it, and it is a frequent source of subtle bugs (type coercion, required
vs optional).

### 4. `response-status-codes` — Status codes & response shaping
Explicit `status_code=`, `201 Created`, `204 No Content`, `response_model` filtering,
`response_model_exclude`, and returning custom responses (`JSONResponse`,
`PlainTextResponse`).
**Rationale:** Correct status-code semantics are a common correctness failure for
generated code (e.g. returning 200 on create). Machine-checkable and high-value.

### 5. `error-handling` — Errors & exceptions
`HTTPException` with status/detail, custom exception handlers
(`@app.exception_handler`), validation-error responses, and consistent error payloads.
**Rationale:** Explicitly called out in the brief and the FastAPI tutorial; the specialist
must reliably raise the right error rather than let a 500 leak.

### 6. `dependency-injection` — Dependencies (`Depends`)
Function and class dependencies, shared/reusable dependencies, sub-dependencies,
`yield` dependencies (setup/teardown, e.g. DB session), and dependency-level validation
(e.g. a `verify_api_key` dependency returning 401).
**Rationale:** DI is FastAPI's core architectural primitive — the search results
repeatedly frame it as "everything from auth to DB connections." The specialist must
compose dependencies, not just use them incidentally.

### 7. `auth-jwt` — Authentication & JWT
`OAuth2PasswordBearer`, password hashing (passlib/bcrypt), login endpoint issuing a JWT,
a `get_current_user` dependency decoding the token, protected routes returning 401 on
bad/missing tokens, and token expiry.
**Rationale:** Phase 1 auth is explicitly JWT-based. This is a high-stakes, high-frequency
category and a classic place small models get details wrong (algorithm, claims, 401 vs
403).

### 8. `pagination` — Paginated list endpoints
`skip`/`limit` (offset) and `page`/`size` pagination, bounded page sizes, and envelope
responses (`{items, total, page, size}`).
**Rationale:** Named directly in the brief. Extremely common on list endpoints and easy
to get subtly wrong (off-by-one, unbounded limit).

### 9. `database-sqlalchemy` — SQL models & sessions
SQLAlchemy models, a session dependency via `yield`, CRUD backed by a real DB
(SQLite in-memory / temp file is sufficient for verification), and Pydantic<->ORM
conversion (`from_attributes`/`orm_mode`).
**Rationale:** The locked stack is PostgreSQL + SQLAlchemy. SQLite is API-compatible for
verification, so pairs are executable here while remaining representative of the pattern.

### 10. `background-tasks` — Background tasks
`BackgroundTasks` to run work after returning a response (send email, write log, etc.).
**Rationale:** Explicitly listed in the brief and the tutorial. A small, well-bounded
category with a clear correctness check (side effect observed after the request).

### 11. `file-upload` — File uploads & form data
`UploadFile`, `File()`, `Form()` fields, multipart handling, reading file contents, and
validating content type/size.
**Rationale:** Common real-world need (avatars, CSV import) with its own API surface
(`python-multipart`) distinct from JSON bodies.

### 12. `routing-structure` — Routers & app structure
`APIRouter` with `prefix`/`tags`, mounting routers on the app, and splitting endpoints
across modules ("bigger applications").
**Rationale:** The tutorial's "Bigger Applications" chapter; essential once an app grows
past a single file, and the shape the specialist must emit for any non-trivial project.

### 13. `middleware-cors` — Middleware & CORS
`CORSMiddleware` configuration, custom middleware (timing header, request logging), and
per-request processing.
**Rationale:** Phase 1 is a web app with a separate React frontend, so CORS is
effectively mandatory. Custom middleware is a common, checkable pattern (added response
header).

---

## Weighting guidance (for dataset generation)

Not all categories deserve equal counts. Suggested emphasis for the first verified batch,
reflecting real request frequency for the SaaS/dashboard vertical:

| Tier | Categories | Rationale |
|---|---|---|
| **Heavy** | `crud`, `pydantic-models`, `auth-jwt`, `dependency-injection` | The daily bread of an API-first web app; also where correctness matters most. |
| **Medium** | `path-query-params`, `error-handling`, `pagination`, `database-sqlalchemy`, `response-status-codes` | Frequent, but narrower per-instance surface. |
| **Light** | `background-tasks`, `file-upload`, `routing-structure`, `middleware-cors` | Real but lower-frequency; a handful of solid verified examples each is enough for the first pass. |

## Deliberately excluded (for this phase)
- **Payments / Stripe** — separate shared module per the architecture doc.
- **WebSockets / real-time** — listed as "possibly" in the combo table; deferred until
  the core CRUD/auth surface is solid.
- **Rate limiting** — real, but usually a third-party dependency (slowapi); can be folded
  into `dependency-injection`/`middleware-cors` later rather than as its own category now.
- **Frontend, SSR, SEO** — out of backend scope entirely.
