import os
import sqlite3
from datetime import datetime

DB_NAME = "documents.db"
STORAGE_DIR = "storage"

def init_system():
    """Ініціалізація каталогу сховища та таблиці у SQLite"""
    os.makedirs(STORAGE_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Створення таблиці з полями за Варіантом 4 (Договори)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            version INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            contract_number TEXT,
            counterparty TEXT,
            amount REAL
        )
    """)
    conn.commit()
    conn.close()
    print("[INFO] Система успішно ініціалізована.")

def add_document(doc_id, title, author, status, version, content, contract_number, counterparty, amount):
    """Додавання документа з перевіркою на дублювання ID та збереженням файла"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Перевірка на існування такого ID (запобігання дублюванню)
    cursor.execute("SELECT id FROM documents WHERE id = ?", (doc_id,))
    if cursor.fetchone():
        print(f"[ПОМИЛКА] Документ з ID '{doc_id}' вже існує! Дублювання заборонено.")
        conn.close()
        return False
        
    file_path = os.path.join(STORAGE_DIR, f"{doc_id.lower()}.txt")
    
    # Запис текстової інформації у файл у папці storage/
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Безпечний параметризований SQL-запит (захист від SQL-ін'єкцій)
        cursor.execute("""
            INSERT INTO documents (
                id, type, title, author, created_at, status, version, 
                file_path, contract_number, counterparty, amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id, "contract", title, author, created_at, status, version, 
            file_path, contract_number, counterparty, amount
        ))
        conn.commit()
        print(f"[УСПІХ] Документ {doc_id} успішно додано.")
    except Exception as e:
        print(f"[ПОМИЛКА БД] {e}")
        conn.rollback()
    finally:
        conn.close()

def get_all_documents():
    """Виведення списку всіх документів"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, contract_number, counterparty, status FROM documents")
    rows = cursor.fetchall()
    conn.close()
    return rows

def search_by_id(doc_id):
    """Пошук документа за ID"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def search_by_field(field_name, value):
    """Пошук за довільним полем (наприклад: контрагент або статус)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    query = f"SELECT id, title, contract_number, counterparty, status FROM documents WHERE {field_name} = ?"
    cursor.execute(query, (value,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def read_document_content(doc_id):
    """Читання вмісту файла документа з перевіркою цілісності"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print(f"[ПОМИЛКА] Документ з ID '{doc_id}' не знайдено в базі даних.")
        return None
        
    file_path = row[0]
    
    # Перевірка наявності файла на диску
    if not os.path.exists(file_path):
        print(f"[ПОМИЛКА ЦІЛІСНОСТІ] Запис у базі є, але фізичний файл за шляхом '{file_path}' відсутній!")
        return None
        
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    # 1. Ініціалізація бази та папки сховища
    init_system()
    
    # 2. Додавання 5 обов'язкових документів
    docs_to_add = [
        ("DOC-001", "Договір поставки обладнання", "manager_1", "active", 1, "Текст договору №1: Поставка серверного обладнання.", "CTR-2026/01", "ТОВ «ТехноСвіт»", 150000.0),
        ("DOC-002", "Договір оренди приміщення", "manager_2", "draft", 1, "Текст договору №2: Оренда офісу на 1 рік.", "CTR-2026/02", "ПП «Бізнес-Плюс»", 45000.0),
        ("DOC-003", "Договір на надання послуг", "manager_1", "active", 1, "Текст договору №3: Консультаційні послуги.", "CTR-2026/03", "ТОВ «ТехноСвіт»", 20000.0),
        ("DOC-004", "Договір підряду", "manager_3", "archived", 2, "Текст договору №4: Ремонтні роботи.", "CTR-2025/15", "ФОП Ковальчук", 85000.0),
        ("DOC-005", "Договір ліцензування ПЗ", "manager_2", "active", 1, "Текст договору №5: Надання ліцензій на софт.", "CTR-2026/04", "ТОВ «СофтКорп»", 120000.0)
    ]
    
    for d in docs_to_add:
        add_document(*d)
        
    print("\n" + "="*50)
    print("СПИСОК УСІХ ДОКУМЕНТІВ У БАЗІ:")
    for doc in get_all_documents():
        print(doc)
        
    print("\n" + "="*50)
    print("ДЕМОНСТРАЦІЯ ПОШУКУ ТА СЦЕНАРІЇВ:")
    
    # Пошук за ID
    print("\n1. Пошук за ID ('DOC-002'):")
    print(search_by_id("DOC-002"))
    
    # Пошук за контрагентом
    print("\n2. Пошук за контрагентом ('ТОВ «ТехноСвіт»'):")
    for r in search_by_field("counterparty", "ТОВ «ТехноСвіт»"):
        print(r)
        
    # Пошук за статусом
    print("\n3. Пошук за статусом ('active'):")
    for r in search_by_field("status", "active"):
        print(r)
        
    # Спроба додати дубль ID
    print("\n4. Спроба додати документ із вже існуючим ID ('DOC-001'):")
    add_document("DOC-001", "Копія договору", "hacker", "active", 1, "Фейковий контент", "CTR-999", "Хтось", 0.0)
    
    # Читання вмісту файла
    print("\n5. Читання вмісту документа 'DOC-001':")
    print(f"Зміст: {read_document_content('DOC-001')}")