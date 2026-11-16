import json
import os
from datetime import datetime

# Шляхи до файлів
STORAGE_DIR = "storage"
DOCUMENT_FILE = "document.json"


def load_document():
    """Завантажує поточний стан документа з файлу або створює базовий, якщо його немає."""
    if os.path.exists(DOCUMENT_FILE):
        with open(DOCUMENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    # Базовий документ за замовчуванням (Варіант 1: Заява студента)
    default_doc = {
        "id": "doc-001",
        "title": "Заява на перездачу академічної різниці",
        "author": "student_01",
        "status": "draft",
        "history": [],
    }
    save_document(default_doc)
    return default_doc


def save_document(doc):
    """Зберігає актуальний стан документа у файл."""
    with open(DOCUMENT_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=4)


# Визначення правил workflow для Варіанта 1 (Погодження заяви студента)
# Словник ключів: (поточний_статус, роль, дія) -> новий_статус
WORKFLOW_RULES = {
    ("draft", "student", "submit"): "curator_review",
    ("curator_review", "curator", "approve"): "dean_review",
    ("curator_review", "curator", "reject"): "draft",
    ("dean_review", "dean", "approve"): "completed",
    ("dean_review", "dean", "reject"): "draft",
}


def print_workflow_info():
    print("=" * 60)
    print("ЛАБОРАТОРНА РОБОТА №4: Workflow погодження електронного документа")
    print("Варіант 1: Погодження заяви студента (Ролі: student, curator, dean)")
    print("=" * 60)


def show_available_actions(status, role):
    """Виводить список доступних дій для конкретного статусу та ролі."""
    actions = []
    for (s, r, a), _ in WORKFLOW_RULES.items():
        if s == status and r == role:
            actions.append(a)
    return actions


def main():
    doc = load_document()
    print_workflow_info()

    while True:
        print(f"\nПоточний документ ID: {doc['id']}")
        print(f"Назва: {doc['title']}")
        print(f"Поточний статус: {doc['status']}")
        print("-" * 40)

        print("Оберіть вашу роль у системі:")
        print("  1. student (Студент)")
        print("  2. curator (Куратор)")
        print("  3. dean (Декан)")
        print("  4. Переглянути історію документа")
        print("  0. Вихід")

        role_choice = input("\nВведіть роль або номер (student/curator/dean/history/exit): ").strip().lower()

        if role_choice == "0" or role_choice == "exit":
            print("Роботу завершено.")
            break

        if role_choice == "4" or role_choice == "history":
            print("\n--- ІСТОРІЯ ПРОХОДЖЕННЯ ДОКУМЕНТА ---")
            if not doc["history"]:
                print("Історія порожня.")
            else:
                for record in doc["history"]:
                    print(
                        f"[{record['timestamp']}] Роль: {record['role']} | "
                        f"Дія: {record['action']} | "
                        f"Статус: {record['from_status']} -> {record['to_status']}"
                    )
                    if record.get("comment"):
                        print(f"   Коментар: {record['comment']}")
            continue

        role_map = {"1": "student", "2": "curator", "3": "dean"}
        role = role_map.get(role_choice, role_choice)

        if role not in ["student", "curator", "dean"]:
            print("Помилка: Невідома роль. Спробуйте ще раз.")
            continue

        current_status = doc["status"]
        allowed_actions = show_available_actions(current_status, role)

        print(f"\nВаша роль: {role}")
        print(f"Доступні дії для статусу '{current_status}': {allowed_actions if allowed_actions else 'немає доступних дій'}")

        if not allowed_actions:
            print("Помилка: У вас немає доступних дій для поточного стану документа або помилкова роль.")
            continue

        action = input("Введіть дію, яку хочете виконати (або 'back' для повернення в меню): ").strip().lower()
        if action == "back":
            continue

        transition_key = (current_status, role, action)

        if transition_key in WORKFLOW_RULES:
            next_status = WORKFLOW_RULES[transition_key]
            comment = input("Введіть коментар до дії (необов'язково): ").strip()

            history_record = {
                "role": role,
                "action": action,
                "from_status": current_status,
                "to_status": next_status,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "comment": comment if comment else None,
            }

            doc["history"].append(history_record)
            doc["status"] = next_status
            save_document(doc)

            print(f"\nУспішно! Статус документа змінено: {current_status} -> {next_status}")
        else:
            print(f"\nПомилка: Дія '{action}' для ролі '{role}' у статусі '{current_status}' заборонена правилами workflow.")


if __name__ == "__main__":
    main()
    