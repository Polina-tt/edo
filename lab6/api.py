import os
import sqlite3
import hashlib
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Query, status
from pydantic import BaseModel

app = FastAPI(
    title="СЕД REST API — Варіант 1 (Заяви студентів)",
    description="ЛР №6 на базі напрацювань попередніх лабораторних робіт (SQLite, RBAC, SHA-256, audit.log)"
)

DB_NAME = "documents.db"
STORAGE_DIR = "storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

# --- 1. Користувачі та RBAC (інтегровано з ЛР №5) ---
USERS = {
    "user_01": {"role": "employee", "name": "Працівник / Студент"},
    "manager_01": {"role": "manager", "name": "Менеджер / Деканат"},
    "administrator": {"role": "administrator", "name": "Адмін"}
}


def log_audit(user: str, role: str, action: str, document_id: str, result: str):
    """Записує подію у твій існуючий файл audit.log"""
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} | user:{user} | role:{role} | action:{action} | doc:{document_id} | result:{result}\n"
    with open("audit.log", "a", encoding="utf-8") as f:
        f.write(log_entry)


def check_permission(username: str, action: str, document: dict = None):
    """Перевіряє доступ на основі RBAC та власника (з ЛР №5)"""
    if username not in USERS:
        log_audit(username, "unknown", action, document["id"] if document else "N/A", "denied (unknown user)")
        raise HTTPException(status_code=403, detail=f"Користувач '{username}' не знайдений")

    role = USERS[username]["role"]
    doc_id = document["id"] if document else "N/A"
    allowed = False

    if role == "employee":
        if action in {"create", "submit"}:
            allowed = True
        elif action in {"read", "edit"} and document and document.get("author") == username:
            allowed = True
    elif role == "manager":
        if action in {"read", "approve", "reject"}:
            allowed = True
    elif role == "administrator":
        allowed = True

    if not allowed:
        log_audit(username, role, action, doc_id, "denied (403 Forbidden)")
        raise HTTPException(
            status_code=403,
            detail=f"Користувач '{username}' ({role}) не має прав на дію '{action}'"
        )
    return role


# --- 2. Робота з файлами у storage/ та хешування SHA-256 (з ЛР №5) ---
def save_file_and_hash(doc_id: str, title: str, content: str) -> tuple[str, str]:
    file_path = os.path.join(STORAGE_DIR, f"{doc_id}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Заголовок: {title}\n\n{content}")

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return file_path, sha256_hash.hexdigest()


# --- 3. База даних SQLite (documents.db) ---
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS student_applications (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author TEXT NOT NULL,
                student_group TEXT NOT NULL,
                status TEXT NOT NULL,
                version INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                sha256_hash TEXT NOT NULL
            )
        """)


init_db()


# --- 4. Моделі запитів (Pydantic) для Варіанта 1 ---
class ApplicationCreate(BaseModel):
    id: str
    title: str
    content: str
    student_group: str


class ApplicationUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    student_group: Optional[str] = None


# --- 5. Логіка Workflow (submit -> approve / reject) ---
WORKFLOW_TRANSITIONS = {
    "submit": ("draft", "submitted"),
    "approve": ("submitted", "approved"),
    "reject": ("submitted", "rejected"),
}


def execute_workflow(doc_id: str, action: str, username: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM student_applications WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            log_audit(username, USERS.get(username, {}).get("role", "unknown"), action, doc_id, "404 Not Found")
            raise HTTPException(status_code=404, detail="Документ не знайдено")

        doc = dict(row)
        role = check_permission(username, action, doc)

        expected_status, new_status = WORKFLOW_TRANSITIONS[action]
        if doc["status"] != expected_status:
            log_audit(username, role, action, doc_id, f"409 Conflict (current={doc['status']})")
            raise HTTPException(
                status_code=409,
                detail=f"Неможливо виконати '{action}' у статусі '{doc['status']}'. Очікується статус '{expected_status}'."
            )

        conn.execute("UPDATE student_applications SET status = ? WHERE id = ?", (new_status, doc_id))
        updated = dict(conn.execute("SELECT * FROM student_applications WHERE id = ?", (doc_id,)).fetchone())

    log_audit(username, role, action, doc_id, f"success -> {new_status}")
    return updated


# --- 6. Endpoints Варіанта 1 ---

@app.post("/documents", status_code=status.HTTP_201_CREATED)
def create_application(
    app_data: ApplicationCreate,
    x_user: str = Header(default="user_01", description="Користувач: user_01, manager_01 або administrator")
):
    role = check_permission(x_user, "create")

    with get_db() as conn:
        existing = conn.execute("SELECT id FROM student_applications WHERE id = ?", (app_data.id,)).fetchone()
        if existing:
            log_audit(x_user, role, "create", app_data.id, "409 Conflict (Duplicate ID)")
            raise HTTPException(status_code=409, detail=f"Документ з ID '{app_data.id}' вже існує")

        file_path, file_hash = save_file_and_hash(app_data.id, app_data.title, app_data.content)

        conn.execute("""
            INSERT INTO student_applications 
            (id, type, title, content, author, student_group, status, version, file_path, sha256_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            app_data.id, "student_application", app_data.title, app_data.content,
            x_user, app_data.student_group, "draft", 1, file_path, file_hash
        ))
        created = dict(conn.execute("SELECT * FROM student_applications WHERE id = ?", (app_data.id,)).fetchone())

    log_audit(x_user, role, "create", app_data.id, "201 Created")
    return created


@app.get("/documents")
def list_applications(
    student_group: Optional[str] = Query(default=None, description="Фільтр за групою (напр. CS-21)"),
    status: Optional[str] = Query(default=None, description="Фільтр за статусом (draft, submitted, approved, rejected)")
):
    query = "SELECT * FROM student_applications WHERE 1=1"
    params = []

    if student_group:
        query += " AND student_group = ?"
        params.append(student_group)
    if status:
        query += " AND status = ?"
        params.append(status)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


@app.get("/documents/{id}")
def get_application(id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM student_applications WHERE id = ?", (id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Документ '{id}' не знайдено")
    return dict(row)


@app.patch("/documents/{id}")
def update_application(
    id: str,
    updates: ApplicationUpdate,
    x_user: str = Header(default="user_01", description="Користувач: user_01, manager_01 або administrator")
):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM student_applications WHERE id = ?", (id,)).fetchone()
        if not row:
            log_audit(x_user, USERS.get(x_user, {}).get("role", "unknown"), "edit", id, "404 Not Found")
            raise HTTPException(status_code=404, detail="Документ не знайдено")

        doc = dict(row)
        role = check_permission(x_user, "edit", doc)

        if doc["status"] != "draft":
            log_audit(x_user, role, "edit", id, "409 Conflict (Not draft)")
            raise HTTPException(status_code=409, detail="Редагування дозволено лише у статусі 'draft'")

        new_title = updates.title if updates.title is not None else doc["title"]
        new_content = updates.content if updates.content is not None else doc["content"]
        new_group = updates.student_group if updates.student_group is not None else doc["student_group"]
        new_version = doc["version"] + 1

        file_path, new_hash = save_file_and_hash(id, new_title, new_content)

        conn.execute("""
            UPDATE student_applications 
            SET title = ?, content = ?, student_group = ?, version = ?, sha256_hash = ?
            WHERE id = ?
        """, (new_title, new_content, new_group, new_version, new_hash, id))
        updated = dict(conn.execute("SELECT * FROM student_applications WHERE id = ?", (id,)).fetchone())

    log_audit(x_user, role, "edit", id, "200 OK")
    return updated


@app.post("/documents/{id}/submit")
def submit_application(
    id: str,
    x_user: str = Header(default="user_01", description="Автор заяви (user_01)")
):
    return execute_workflow(id, "submit", x_user)


@app.post("/documents/{id}/approve")
def approve_application(
    id: str,
    x_user: str = Header(default="manager_01", description="Менеджер / Деканат (manager_01)")
):
    return execute_workflow(id, "approve", x_user)


@app.post("/documents/{id}/reject")
def reject_application(
    id: str,
    x_user: str = Header(default="manager_01", description="Менеджер / Деканат (manager_01)")
):
    return execute_workflow(id, "reject", x_user)