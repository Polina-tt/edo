import hashlib
from datetime import datetime

# Користувачі та їх ролі
USERS = {
    "user_01": {"role": "employee", "name": "Працівник"},
    "manager_01": {"role": "manager", "name": "Менеджер"},
    "administrator": {"role": "administrator", "name": "Адмін"}
}

# Матриця дозволів (RBAC)
ROLES_PERMISSIONS = {
    "employee": {"create", "read_own", "edit_own"},
    "manager": {"read_all", "approve", "reject"},
    "administrator": {"read_all", "archive", "view_audit"}
}

def log_audit(user, role, action, document_id, result):
    """Записує подію до файлу audit.log"""
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} | user:{user} | role:{role} | action:{action} | doc:{document_id} | result:{result}\n"
    with open("audit.log", "a", encoding="utf-8") as f:
        f.write(log_entry)

def check_permission_and_log(username, action, document=None):
    """Перевіряє доступ на основі RBAC та власника (ownership)"""
    if username not in USERS:
        log_audit(username, "unknown", action, document.get("id", "N/A") if document else "N/A", "denied")
        print(f"[-] Користувач {username} не знайдений.")
        return False

    user = USERS[username]
    role = user["role"]
    doc_id = document.get("id", "N/A") if document else "N/A"
    allowed = False

    if role == "employee":
        if action == "create":
            allowed = True
        elif action in {"read", "edit"} and document and document.get("author") == username:
            allowed = True
    else:
        if action in {"read", "approve", "reject", "archive", "view_audit"}:
            allowed = True

    result = "success" if allowed else "denied"
    log_audit(username, role, action, doc_id, result)

    if allowed:
        print(f"[+] ДОЗВОЛЕНО: {username} ({role}) виконав '{action}' над {doc_id}")
    else:
        print(f"[!] ЗАБОРОНЕНО: {username} ({role}) намагався виконати '{action}' над {doc_id}")

    return allowed

def calculate_file_hash(file_path):
    """Обчислює SHA-256 хеш файлу"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except FileNotFoundError:
        print(f"[-] Файл {file_path} не знайдено.")
        return None

def verify_integrity(document_id, file_path, reference_hash):
    """Перевіряє цілісність файлу за SHA-256"""
    current_hash = calculate_file_hash(file_path)
    if current_hash is None:
        return False

    if current_hash == reference_hash:
        print(f"[OK] Цілісність файлу для {document_id} не порушена.")
        return True
    else:
        print(f"[ALARM!] УВАГА! Файл {document_id} було змінено!")
        return False

if __name__ == "__main__":
    print("=== ЗАПУСК ЛАБОРАТОРНОЇ РОБОТИ №5 ===")
    
    target_file = "storage/doc-001.txt"
    doc_sample = {"id": "doc-001", "author": "user_01", "file_path": target_file}

    # 1. Фіксуємо еталонний хеш
    ref_hash = calculate_file_hash(target_file)
    print(f"Еталонний SHA-256: {ref_hash}")

    # 2. Тест дозволеної операції
    print("\n--- Тест 1 ---")
    check_permission_and_log("user_01", "edit", doc_sample)

    # 3. Тест забороненої операції
    print("\n--- Тест 2 ---")
    check_permission_and_log("user_01", "approve", doc_sample)

    # 4. Перевірка цілісності до змін
    print("\n--- Тест 3 ---")
    verify_integrity("doc-001", target_file, ref_hash)

    # 5. Змінюємо файл вручну та перевіряємо знову
    print("\n--- Тест 4 (Змінюємо файл) ---")
    with open(target_file, "a", encoding="utf-8") as f:
        f.write("\nДодано несанкціонований рядок!")
    
    verify_integrity("doc-001", target_file, ref_hash)