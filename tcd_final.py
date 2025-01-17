import sqlite3
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import requests
from datetime import datetime
import webbrowser  # Библиотека для открытия ссылок в браузере.

# Класс для работы с базой данных
class DatabaseManager:
    def __init__(self, db_name="finance_manager.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.add_default_categories()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                amount REAL,
                category TEXT,
                description TEXT,
                date TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
        """)
        self.conn.commit()

    def add_default_categories(self):
        # Добавляет предопределённые категории.
        default_categories = ["Еда", "Жильё", "Здоровье"]
        for category in default_categories:
            self.cursor.execute("""
                INSERT OR IGNORE INTO categories (name)
                VALUES (?)
            """, (category,))
        self.conn.commit()

    def add_transaction(self, amount, category, description, date):
        self.cursor.execute("""
            INSERT INTO transactions (amount, category, description, date)
            VALUES (?, ?, ?, ?)
        """, (amount, category, description, date))
        self.conn.commit()

    def get_transactions(self):
        self.cursor.execute("SELECT * FROM transactions")
        return self.cursor.fetchall()

    def add_category(self, name):
        self.cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
        self.conn.commit()

    def get_categories(self):
        self.cursor.execute("SELECT name FROM categories")
        return [row[0] for row in self.cursor.fetchall()]

    def close(self):
        self.conn.close()


# Класс для работы с API с курсом валют.
class APIClient:
    def __init__(self, api_url="https://api.exchangerate-api.com/v4/latest/USD"):
        self.api_url = api_url

    def get_exchange_rate(self, currency):
        try:
            response = requests.get(self.api_url)
            if response.status_code == 200:
                rates = response.json()["rates"]
                return rates.get(currency, None)
            else:
                messagebox.showerror("Ошибка", f"Не удалось получить данные от API. Код ошибки: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Ошибка", f"Ошибка при запросе к API: {e}")
            return None


# Класс для экспорта данных.
class SQLManager:
    @staticmethod # Используется для создания статических методов в классах, которые не зависят от состояния объекта или класса. 
    def export_to_csv(filename, data):
        with open(filename, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["ID", "Amount", "Category", "Description", "Date"])
            writer.writerows(data)

    @staticmethod
    def export_to_txt(filename, data):
        with open(filename, "w", encoding="utf-8") as file:
            for row in data:
                file.write("\t".join(map(str, row)) + "\n")


# Класс для основного графического интерфейса программы.
class FinanceManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Персональный финансовый менеджер by KS (TKD)")
        self.db_manager = DatabaseManager()
        self.api_client = APIClient()
        self.setup_ui()

    def setup_ui(self):
        # Этот фрейм для добавления транзакции.
        frame = ttk.LabelFrame(self.root, text="Добавить транзакцию")
        frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        ttk.Label(frame, text="Сумма:").grid(row=0, column=0, padx=5, pady=5)
        self.amount_entry = ttk.Entry(frame)
        self.amount_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Валюта:").grid(row=1, column=0, padx=5, pady=5)
        self.currency_combobox = ttk.Combobox(frame, values=["USD", "EUR", "RUB", "JPY", "GBP"])
        self.currency_combobox.set("USD")
        self.currency_combobox.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Категория:").grid(row=2, column=0, padx=5, pady=5)
        self.category_combobox = ttk.Combobox(frame, values=self.db_manager.get_categories())
        self.category_combobox.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(frame, text="Описание:").grid(row=3, column=0, padx=5, pady=5)
        self.description_entry = ttk.Entry(frame)
        self.description_entry.grid(row=3, column=1, padx=5, pady=5)

        ttk.Button(frame, text="Добавить", command=self.add_transaction).grid(row=4, column=0, columnspan=2, pady=10)

        # Это кнопка для добавления новой категории.
        ttk.Button(frame, text="Добавить категорию", command=self.add_category).grid(row=5, column=0, columnspan=2, pady=10)

        # Этот фрейм для отображения транзакций из БД.
        self.tree = ttk.Treeview(self.root, columns=("ID", "Amount", "Category", "Description", "Date"), show="headings")
        self.tree.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)

        # Это кнопки для экспорта данных.
        ttk.Button(self.root, text="Экспорт в CSV", command=self.export_to_csv).grid(row=2, column=0, padx=10, pady=10)
        ttk.Button(self.root, text="Экспорт в TXT", command=self.export_to_txt).grid(row=3, column=0, padx=10, pady=10)

        # Кнопка "О программе".
        ttk.Button(self.root, text="О программе", command=self.show_about).grid(row=4, column=0, padx=10, pady=10)

        self.update_tree()

    def add_transaction(self):
        amount = self.amount_entry.get()
        currency = self.currency_combobox.get()
        category = self.category_combobox.get()
        description = self.description_entry.get()

        if not amount or not currency or not category or not description:
            messagebox.showerror("Ошибка 405", "Все поля должны быть заполнены!")
            return

        try:
            amount = float(amount)
            # Конвертируем сумму в доллары, если выбрана другая валюта с помощью API.
            if currency != "USD":
                rate = self.api_client.get_exchange_rate(currency)
                if rate is None:
                    messagebox.showerror("Фатальная ошибка", "Не удалось получить курс валюты.")
                    return
                amount = amount / rate  # Конвертируем в USD

            date = datetime.now().strftime("%Y-%m-%d")
            if category not in self.db_manager.get_categories():
                messagebox.showerror("Ошибка 404", "Категория не существует.")
                return
            self.db_manager.add_transaction(amount, category, description, date)
            self.update_tree()
            messagebox.showinfo("Успешно", "Транзакция добавлена.")
            
            self.amount_entry.delete(0, tk.END)
            self.currency_combobox.set("USD")
            self.category_combobox.set('')
            self.description_entry.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Ошибка 808", "Введите корректную сумму.")
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка SQL", f"Ошибка при добавлении транзакции: {e}")

    def add_category(self):
        new_category = simpledialog.askstring("Новая категория", "Введите название новой категории:")
        if new_category:
            self.db_manager.add_category(new_category)
            self.category_combobox['values'] = self.db_manager.get_categories()
            self.category_combobox.set(new_category)
            messagebox.showinfo("Успешно", "Категория добавлена.")

    def export_to_csv(self):
        # Метод asksaves... используется для открытия диалогового окна, которое позволяет пользователю выбрать место для сохранения файла и указать его имя. 
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filename:
            try:
                SQLManager.export_to_csv(filename, self.db_manager.get_transactions())
                messagebox.showinfo("Успешно", "Данные экспортированы в CSV!")
            except Exception as e:
                messagebox.showerror("Ошибка 321", f"Не удалось экспортировать данные: {e}")

    def export_to_txt(self):
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if filename:
            try:
                SQLManager.export_to_txt(filename, self.db_manager.get_transactions())
                messagebox.showinfo("Успешно", "Данные экспортированы в TXT.")
            except Exception as e:
                messagebox.showerror("Ошибка 123", f"Не удалось экспортировать данные: {e}")

    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("О программе")
        about_window.geometry("300x250")
        about_window.resizable(False, False)

        ttk.Label(about_window, text="Персональный финансовый менеджер", font=("Arial", 12)).pack(pady=10)
        ttk.Label(about_window, text="by Kirill Sidorov", font=("Arial", 10)).pack(pady=10)
        ttk.Label(about_window, text="DH-center ITMO", font=("Arial", 10)).pack(pady=10)
        ttk.Label(about_window, text="Version: 0.3", font=("Arial", 10)).pack(pady=5)

        # Кликабельная ссылка на GitHub, для неё библиотека webbrowser.
        github_link = ttk.Label(about_window, text="GitHub: https://github.com/nekamsk/tkd_itmo_dh", font=("Arial", 10), cursor="hand2")
        github_link.pack(pady=5)
        github_link.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/nekamsk/tkd_itmo_dh"))

        ttk.Button(about_window, text="Закрыть", command=about_window.destroy).pack(pady=10)

    def update_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for row in self.db_manager.get_transactions():
            self.tree.insert("", "end", values=row)

    def on_close(self):
        self.db_manager.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FinanceManager(root)
    # Связывает событие закрытия окна (когда пользователь нажимает на крестик в углу окна) с закрытием базы данных.
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
