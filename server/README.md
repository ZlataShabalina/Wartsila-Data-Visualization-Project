# FastAPI Server – README (Multi‑User, Dataset‑Scoped API)

This backend ingests CSVs **into a database as datasets** and serves queries **per request** based on:
- **DB connection** (`connection_id`), and
- **Dataset** (`dataset_id`) within that DB.

There is **no global “active source.”** Multiple users can concurrently query different datasets and DBs.

---

## 1) Install environment & dependencies

**Prereqs**
- Python **3.11+** (tested with 3.12)
- pip

```bash
# from the server/ directory
python -m venv .venv

# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# upgrade pip (optional)
python -m pip install --upgrade pip

# install dependencies
pip install -r requirements.txt
```

Environment variables (optional):
- `DATABASE_URL` — default local graph DB URL (used to bootstrap tables)
  - default: `sqlite+aiosqlite:///./data/app.db`
- `REGISTRY_DATABASE_URL` — registry DB URL (stores DB connections)
  - default: `sqlite+aiosqlite:///./data/registry.db`
- `SQL_ECHO=1` — enable SQLAlchemy echo logs

---

## 2) Run the server locally

From `server/`:

```bash
in our case: python main.py
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- Swagger UI: `http://localhost:8000/docs`
- CSV files placed or uploaded are saved under `server/data/`.
- On startup (via **lifespan** handler), tables for **registry DB** and default **graph DB** are created.

**CSV format (required headers):**
```
parent_item,child_item,sequence_no,level
```
- Delimiter auto-detected (`;` or `,`)
- Header case/whitespace/BOM normalized

---

## 3) Architecture (quick)

- **Registry DB**: stores known DB connections (`/api/db/register`, `/api/sources`).
- **Graph DB (per connection)**: stores ingested datasets:
  - `upload_file` (one row per dataset / CSV import)
  - `relationship` (edges: `parent_item`, `child_item`, `sequence_no`, `level`)
- **No in-memory global state**. Each request specifies `connection_id` and `dataset_id`.

---

## 4) Endpoints (Base prefix: `/api`)

### 4.1 List CSVs, DB connections, and datasets (optional)
`GET /api/sources?connection_id=<id>`

- Always returns CSV files present under `server/data/` and **all** registered DB connections.
- If `connection_id` is provided, also returns **datasets** already imported into that connection’s DB.

**Response example**
```json
{
  "csv_files": [
    { "name": "where_used_sample_100_lines_student_version.csv", "size": 26543, "modified_at": 1727820000 }
  ],
  "db_connections": [
    { "id": 1, "name": "local-sqlite", "url": "sqlite+aiosqlite:///./data/app.db", "created_at": "2025-10-02T08:00:00+00:00", "last_used_at": null, "has_api_key": true }
  ],
  "datasets": [
    { "dataset_id": 3, "original_name": "where_used_sample_100_lines_student_version.csv", "saved_path": "/abs/path/.../data/where_used_sample_100_lines_student_version.csv", "sha256": "78eeaa...", "rows_loaded": 107, "created_at": "2025-10-02T08:10:00+00:00" }
  ]
}
```

**cURL**
```bash
# just list sources (CSVs + all DB connections)
curl "http://localhost:8000/api/sources"

# list sources AND datasets that exist in connection 1
curl "http://localhost:8000/api/sources?connection_id=1"
```

---

### 4.2 Register a DB connection
`POST /api/db/register`

Registers a DB connection in the **registry DB** (for later use by `connection_id`). Optionally set a simple API key for selection/queries.

**Request**
```json
{
  "name": "local-sqlite",
  "url": "sqlite+aiosqlite:///./data/app.db",
  "api_key": "secret123"
}
```

**Response**
```json
{ "message": "db connection registered", "connection_id": 1 }
```

**cURL**
```bash
curl -X POST "http://localhost:8000/api/db/register" \
  -H "Content-Type: application/json" \
  -d '{"name":"local-sqlite","url":"sqlite+aiosqlite:///./data/app.db","api_key":"secret123"}'
```

---

### 4.3 Import a server CSV into a DB as a dataset
`POST /api/sources/import_csv`

Takes a CSV **already present** in `server/data/` and **ingests it into the chosen DB** (`connection_id`) as a **dataset** in SQL. Deduped by file **SHA‑256**.

**Headers (if set on connection):**
- `x-api-key: <your-connection-api-key>`

**Request**
```json
{
  "connection_id": 1,
  "filename": "where_used_sample_100_lines_student_version.csv"
}
```

**Response (new dataset)**
```json
{ "message": "dataset imported", "dataset_id": 5, "sha256": "78eeaa...", "rows": 107 }
```
**Response (already imported)**
```json
{ "message": "dataset already exists", "dataset_id": 5, "sha256": "78eeaa...", "rows": 107 }
```

**cURL**
```bash
curl -X POST "http://localhost:8000/api/sources/import_csv" \
  -H "Content-Type: application/json" \
  -H "x-api-key: secret123" \
  -d '{"connection_id":1,"filename":"where_used_sample_100_lines_student_version.csv"}'
```

> Tip: to upload a new CSV file to the server, place it under `server/data/` (e.g., via scp/docker bind).

---

### 4.4 Query root nodes (dataset-scoped)
`GET /api/root_node?connection_id=<id>&dataset_id=<id>`

Returns the **root nodes** (parents that never appear as children) for that dataset.

**Headers (if set on connection):**
- `x-api-key: <your-connection-api-key>`

**Response example**
```json
{ "message": "roots", "root_nodes": ["MAT000001", "MAT000002"], "count": 2 }
```

**cURL**
```bash
curl "http://localhost:8000/api/root_node?connection_id=1&dataset_id=5" \
  -H "x-api-key: secret123"
```

---

### 4.5 Query children (dataset-scoped)
`GET /api/child_node?connection_id=<id>&dataset_id=<id>&node_id=<id>&limit=<n>`

Returns the parent (if exists) and the ordered children of `node_id` for that dataset.

**Headers (if set on connection):**
- `x-api-key: <your-connection-api-key>`

**Response example**
```json
{
  "search_id": "MAT000001",
  "parent": null,
  "children": [
    { "id": "MAT000004", "name": "MAT000004", "sequence_no": 1, "level": 1 },
    { "id": "MAT000007", "name": "MAT000007", "sequence_no": 10, "level": 1 },
    { "id": "MAT000008", "name": "MAT000008", "sequence_no": 11, "level": 1 }
  ],
  "count_children": 3
}
```

**cURL**
```bash
curl "http://localhost:8000/api/child_node?connection_id=1&dataset_id=5&node_id=MAT000001&limit=3" \
  -H "x-api-key: secret123"
```

---

## 5) Notes

- This API is now **stateless** and **multi-user ready**; clients must pass `connection_id` and `dataset_id` on each query.
- `server/data/` is a staging area for CSV files; use `/api/sources/import_csv` to ingest into SQL as datasets.
- SQLite works for dev; for heavy concurrency, register a Postgres connection.
- If a connection was created with an `api_key`, pass it via `x-api-key` for protected endpoints.
- Tables are created automatically on startup via the **lifespan** handler in `main.py`.
