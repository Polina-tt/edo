import json
from pathlib import Path

# 1. Визначаємо список обов'язкових загальних полів згідно з вимогами лабораторної
GENERAL_FIELDS = [
    "id", "type", "title", "author", "created_at", "status", "version"
]

# 2. Визначаємо специфічні поля для нашого варіанта (Рахунок)
VARIANT_FIELDS = [
    "invoice_number", "customer", "amount", "currency", "due_date"
]

# Об'єднуємо їх у єдиний список для перевірки
ALL_REQUIRED_FIELDS = GENERAL_FIELDS + VARIANT_FIELDS

def main():
    # Вказуємо шлях до каталогу з документами
    docs_dir = Path("documents")
    
    # Перевіряємо, чи існує така папка взагалі
    if not docs_dir.exists() or not docs_dir.is_dir():
        print(f"Помилка: каталог '{docs_dir}' не знайдено.")
        return

    # АВТОМАТИЧНИЙ ПОШУК: метод glob знаходить усі файли з розширенням .json у папці
    # Це відповідає вимозі, щоб ми не прописували назви файлів вручну в коді!
    json_files = list(docs_dir.glob("*.json"))
    
    if not json_files:
        print(f"У каталозі '{docs_dir}' не знайдено жодного файлу .json")
        return

    print(f"Знайдено файлів для перевірки: {len(json_files)}\n" + "=" * 50)

    loaded_documents = []
    seen_ids = set()       # Множина для збереження вже знайдених ID (потрібна для перевірки унікальності)
    duplicate_ids = set()  # Множина для виявлених дублікатів ID

    # ЕТАП 1: Читання файлів та збір ID
    for file_path in json_files:
        try:
            # Відкриваємо кожен файл у кодуванні utf-8
            with open(file_path, "r", encoding="utf-8") as f:
                # json.load перетворює текст JSON у словник Python
                doc_data = json.load(f)
                
                # Перевіряємо, чи є вміст файлу словником (об'єктом)
                if not isinstance(doc_data, dict):
                    print(f"[ПОМИЛКА] Файл {file_path.name}: вміст не є об'єктом JSON.")
                    continue
                
                # Зберігаємо ім'я файлу всередині словника для зручності виведення
                doc_data["_filename"] = file_path.name
                loaded_documents.append(doc_data)
                
                # ПЕРЕВІРКА УНІКАЛЬНОСТІ ID:
                doc_id = doc_data.get("id")
                if doc_id:
                    if doc_id in seen_ids:
                        duplicate_ids.add(doc_id)  # Якщо ID вже зустрічався — додаємо до дублікатів
                    else:
                        seen_ids.add(doc_id)     # Інакше запам'ятовуємо його
                        
        except json.JSONDecodeError as e:
            # Обробка синтаксичних помилок у JSON (наприклад, пропущена кома чи лапка)
            print(f"[ПОМИЛКА] Файл {file_path.name}: синтаксична помилка JSON ({e})")
        except Exception as e:
            print(f"[ПОМИЛКА] Файл {file_path.name}: {e}")

    print("Результати перевірки та валідації документів:\n" + "-" * 50)

    # ЕТАП 2: Перевірка структури (наявність обов'язкових полів) та виведення результатів
    for doc in loaded_documents:
        filename = doc.get("_filename")
        doc_id = doc.get("id", "НЕВІДОМИЙ")
        errors = []

        # Шукаємо, яких обов'язкових полів не вистачає у поточному документі
        missing_fields = [field for field in ALL_REQUIRED_FIELDS if field not in doc]
        if missing_fields:
            errors.append(f"відсутні обов'язкові поля: {', '.join(missing_fields)}")

        # Перевіряємо, чи повторюється ID цього документа в інших файлах
        if doc_id in duplicate_ids:
            errors.append(f"ідентифікатор '{doc_id}' дублюється в іншому документі!")

        # Виводимо результат залежно від наявності помилок
        if errors:
            print(f" Файл: documents/{filename} (ID: {doc_id}) — ПОМИЛКА")
            for err in errors:
                print(f"   ↳ {err}")
            print()
        else:
            print(f" Файл: documents/{filename} — УСПІШНО")
            print(f"   • ID: {doc['id']} | Номер: {doc['invoice_number']}")
            print(f"   • Назва: {doc['title']}")
            print(f"   • Клієнт: {doc['customer']} | Сума: {doc['amount']} {doc['currency']}")
            print(f"   • Автор: {doc['author']} | Створено: {doc['created_at']}")
            print(f"   • Термін оплати: {doc['due_date']} | Статус: {doc['status']} (Версія: {doc['version']})")
            print()

if __name__ == "__main__":
    main()