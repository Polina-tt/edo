import json
import os
from datetime import datetime

class ElectronicDocument:
    # Правила переходів для Варіанта 1 (Заява студента)
    ALLOWED_TRANSITIONS = {
        "draft": ["submitted"],
        "submitted": ["review"],
        "review": ["approved", "rejected"],
        "approved": ["archived"],
        "rejected": ["draft"],  # Повернення у draft для виправлення
        "archived": []          # Кінцевий стан
    }

    def __init__(self, data: dict):
        self.id = data.get("id")
        self.type = data.get("type", "student_application")
        self.title = data.get("title")
        self.author = data.get("author")
        self.created_at = data.get("created_at", datetime.now().strftime("%Y-%m-%d"))
        self.status = data.get("status", "draft")
        self.version = data.get("version", 1)
        self.content = data.get("content", "")
        self.history = data.get("history", [])

    @classmethod
    def load_from_json(cls, filename: str):
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data)

    def save_to_json(self, filename: str):
        data = {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "author": self.author,
            "created_at": self.created_at,
            "status": self.status,
            "version": self.version,
            "content": self.content,
            "history": self.history
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"[Збережено] Зміни записано у файл {filename}")

    def change_status(self, new_status: str, author: str = "system"):
        if self.status == "archived":
            raise PermissionError("Помилка: документ в архіві, зміна статусу неможлива.")

        allowed_next = self.ALLOWED_TRANSITIONS.get(self.status, [])
        if new_status not in allowed_next:
            raise ValueError(f"Заборонений перехід: з '{self.status}' у '{new_status}'. Дозволено: {allowed_next}")

        old_status = self.status
        self.status = new_status
        
        # Запис в історію з міткою часу
        self.history.append({
            "from_status": old_status,
            "to_status": new_status,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "author": author
        })
        print(f"[Статус] Успішно змінено: {old_status} ➔ {new_status}")

    def update_content(self, new_content: str):
        if self.status == "archived":
            raise PermissionError("Редагування заборонено: документ в архіві.")

        if new_content != self.content:
            self.content = new_content
            self.version += 1
            print(f"[Версія] Вміст змінено. Номер версії збільшено до: v{self.version}")
        else:
            print("[Інформація] Змін у змісті немає, версія не змінилася.")

    def display_info(self):
        print(f"\n--- ДОКУМЕНТ: {self.id} | Статус: [{self.status.upper()}] | Версія: v{self.version} ---")
        print(f"Назва: {self.title}")
        print(f"Зміст: {self.content}")
        print("Історія змін:")
        if not self.history:
            print("  (історія порожня)")
        for idx, h in enumerate(self.history, 1):
            print(f"  {idx}. [{h['timestamp']}] {h['from_status']} ➔ {h['to_status']} (Користувач: {h['author']})")
        print("-" * 60)


if __name__ == "__main__":
    filename = "document.json"

    # 1. Завантажуємо документ із файлу
    doc = ElectronicDocument.load_from_json(filename)
    doc.display_info()

    # 2. Перевіряємо коректний перехід
    doc.change_status("submitted", author="student_ivan")

    # 3. Перевіряємо блокування забороненого переходу
    try:
        doc.change_status("approved", author="dean_office")
    except ValueError as e:
        print(f"\n[Захист спрацював]: {e}\n")

    # 4. Редагуємо зміст (має збільшитися версія)
    doc.update_content("Оновлений текст заяви після консультації.")

    # 5. Продовжуємо життєвий цикл
    doc.change_status("review", author="dean_office")
    doc.change_status("rejected", author="dean_office")
    doc.change_status("draft", author="student_ivan") # Повернення у draft

    # 6. Зберігаємо результати назад у JSON-файл
    doc.save_to_json(filename)
    
    # Виводимо фінальний стан
    doc.display_info()