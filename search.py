"""
search.py - Поиск файлов на Python с Tkinter GUI и CLI
Поддерживает: рекурсивный поиск, фильтры по имени, расширению, размеру, дате, содержимому.
"""

import os
import sys
import fnmatch
import threading
import time
import csv
import json
import argparse
from datetime import datetime
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox

class FileSearchApp:
    def __init__(self, root=None):
        self.root = root
        self.results = []
        self.stop_search = False
        self.search_thread = None
        if root:
            self.setup_gui()
    
    def setup_gui(self):
        self.root.title("🔍 Поиск файлов Pro")
        self.root.geometry("900x650")
        self.root.resizable(True, True)
        
        # Панель параметров
        param_frame = LabelFrame(self.root, text="Параметры поиска", padx=10, pady=10)
        param_frame.pack(fill=X, padx=10, pady=5)
        
        # Папка
        row = Frame(param_frame)
        row.pack(fill=X, pady=2)
        Label(row, text="Папка:").pack(side=LEFT)
        self.path_var = StringVar(value=os.getcwd())
        Entry(row, textvariable=self.path_var, width=50).pack(side=LEFT, padx=5)
        Button(row, text="Обзор", command=self.browse_folder).pack(side=LEFT)
        
        # Имя
        row = Frame(param_frame)
        row.pack(fill=X, pady=2)
        Label(row, text="Имя (маска):").pack(side=LEFT)
        self.name_var = StringVar(value="*")
        Entry(row, textvariable=self.name_var, width=30).pack(side=LEFT, padx=5)
        Label(row, text="(например *.txt)").pack(side=LEFT)
        
        # Расширения и размер
        row = Frame(param_frame)
        row.pack(fill=X, pady=2)
        Label(row, text="Расширения (через запятую):").pack(side=LEFT)
        self.ext_var = StringVar()
        Entry(row, textvariable=self.ext_var, width=20).pack(side=LEFT, padx=5)
        Label(row, text="Мин. размер (байт):").pack(side=LEFT, padx=(10,0))
        self.min_size_var = StringVar()
        Entry(row, textvariable=self.min_size_var, width=8).pack(side=LEFT, padx=5)
        Label(row, text="Макс. размер:").pack(side=LEFT)
        self.max_size_var = StringVar()
        Entry(row, textvariable=self.max_size_var, width=8).pack(side=LEFT, padx=5)
        
        # Поиск в содержимом
        row = Frame(param_frame)
        row.pack(fill=X, pady=2)
        self.search_content = BooleanVar()
        Checkbutton(row, text="Поиск в содержимом", variable=self.search_content, command=self.toggle_content).pack(side=LEFT)
        self.content_var = StringVar()
        self.content_entry = Entry(row, textvariable=self.content_var, width=40, state='disabled')
        self.content_entry.pack(side=LEFT, padx=5)
        
        # Кнопки управления
        btn_frame = Frame(self.root)
        btn_frame.pack(fill=X, padx=10, pady=5)
        self.search_btn = Button(btn_frame, text="🔍 Найти", command=self.start_search, bg="#3498db", fg="white")
        self.search_btn.pack(side=LEFT, padx=5)
        self.stop_btn = Button(btn_frame, text="⏹️ Остановить", command=self.stop_search_cmd, state=DISABLED, bg="#e74c3c", fg="white")
        self.stop_btn.pack(side=LEFT, padx=5)
        Button(btn_frame, text="💾 Сохранить CSV", command=self.save_csv).pack(side=LEFT, padx=5)
        Button(btn_frame, text="📋 Очистить", command=self.clear_results).pack(side=LEFT, padx=5)
        
        # Прогресс
        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(fill=X, padx=10, pady=5)
        self.status_label = Label(self.root, text="Готов", anchor=W)
        self.status_label.pack(fill=X, padx=10)
        
        # Таблица результатов
        frame_results = Frame(self.root)
        frame_results.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.tree = ttk.Treeview(frame_results, columns=("name", "path", "size", "modified"), show="headings")
        self.tree.heading("name", text="Имя")
        self.tree.heading("path", text="Путь")
        self.tree.heading("size", text="Размер (байт)")
        self.tree.heading("modified", text="Изменён")
        self.tree.column("name", width=200)
        self.tree.column("path", width=400)
        self.tree.column("size", width=100)
        self.tree.column("modified", width=150)
        scrollbar = Scrollbar(frame_results, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.tree.bind("<Double-1>", self.open_file)
        
        self.results = []
    
    def toggle_content(self):
        if self.search_content.get():
            self.content_entry.config(state='normal')
        else:
            self.content_entry.config(state='disabled')
    
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)
    
    def start_search(self):
        if self.search_thread and self.search_thread.is_alive():
            messagebox.showwarning("Внимание", "Поиск уже выполняется")
            return
        path = self.path_var.get()
        if not os.path.exists(path):
            messagebox.showerror("Ошибка", "Папка не существует")
            return
        self.clear_results()
        self.stop_search = False
        self.search_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.progress.start()
        self.status_label.config(text="Поиск...")
        self.search_thread = threading.Thread(target=self.search_files, args=(path,))
        self.search_thread.start()
        self.monitor_thread()
    
    def search_files(self, path):
        pattern = self.name_var.get().strip()
        extensions = [ext.strip() for ext in self.ext_var.get().split(',') if ext.strip()]
        min_size = self.parse_size(self.min_size_var.get())
        max_size = self.parse_size(self.max_size_var.get())
        search_text = self.content_var.get().strip() if self.search_content.get() else None
        
        for root, dirs, files in os.walk(path):
            if self.stop_search:
                break
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('node_modules', '__pycache__', 'venv')]
            for file in files:
                if self.stop_search:
                    break
                filepath = os.path.join(root, file)
                # Фильтр по имени
                if not fnmatch.fnmatch(file, pattern):
                    continue
                # Фильтр по расширению
                if extensions:
                    ext = os.path.splitext(file)[1].lstrip('.').lower()
                    if ext not in extensions:
                        continue
                try:
                    stat = os.stat(filepath)
                    size = stat.st_size
                    if min_size is not None and size < min_size:
                        continue
                    if max_size is not None and size > max_size:
                        continue
                    mtime = stat.st_mtime
                except OSError:
                    continue
                # Поиск внутри файла
                if search_text:
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if search_text.lower() not in content.lower():
                                continue
                    except:
                        continue
                self.results.append({
                    'name': file,
                    'path': filepath,
                    'size': size,
                    'modified': datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
                self.root.after(0, self.add_result, file, filepath, size, self.results[-1]['modified'])
        self.root.after(0, self.search_finished)
    
    def add_result(self, name, path, size, modified):
        self.tree.insert("", END, values=(name, path, size, modified))
    
    def monitor_thread(self):
        if self.search_thread and self.search_thread.is_alive():
            self.root.after(100, self.monitor_thread)
        else:
            if not self.stop_search:
                self.search_finished()
    
    def search_finished(self):
        self.progress.stop()
        self.search_btn.config(state=NORMAL)
        self.stop_btn.config(state=DISABLED)
        self.status_label.config(text=f"Найдено файлов: {len(self.results)}")
    
    def stop_search_cmd(self):
        self.stop_search = True
        self.status_label.config(text="Остановка...")
    
    def clear_results(self):
        self.tree.delete(*self.tree.get_children())
        self.results.clear()
        self.status_label.config(text="Готов")
    
    def save_csv(self):
        if not self.results:
            messagebox.showwarning("Нет данных", "Нет результатов для сохранения")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filepath:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'path', 'size', 'modified'])
                writer.writeheader()
                writer.writerows(self.results)
            messagebox.showinfo("Сохранено", f"Сохранено {len(self.results)} записей")
    
    def open_file(self, event):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            path = item['values'][1]
            if os.name == 'nt':
                os.startfile(path)
            else:
                os.system(f'xdg-open "{path}"')
    
    @staticmethod
    def parse_size(s):
        if s.strip():
            try:
                return int(s)
            except:
                return None
        return None

def cli_mode():
    parser = argparse.ArgumentParser(description="Поиск файлов в CLI")
    parser.add_argument("path", help="Корневая папка для поиска")
    parser.add_argument("-name", default="*", help="Маска имени файла")
    parser.add_argument("-ext", help="Расширения через запятую")
    parser.add_argument("-min-size", type=int, help="Минимальный размер в байтах")
    parser.add_argument("-max-size", type=int, help="Максимальный размер в байтах")
    parser.add_argument("-content", help="Текст для поиска внутри файлов")
    parser.add_argument("-exclude-dirs", help="Папки для исключения через запятую", default=".git,node_modules,__pycache__,venv")
    args = parser.parse_args()
    
    exclude = set(args.exclude_dirs.split(','))
    pattern = args.name
    extensions = args.ext.split(',') if args.ext else []
    min_size = args.min_size
    max_size = args.max_size
    search_text = args.content
    
    results = []
    for root, dirs, files in os.walk(args.path):
        dirs[:] = [d for d in dirs if d not in exclude and not d.startswith('.')]
        for file in files:
            if not fnmatch.fnmatch(file, pattern):
                continue
            if extensions:
                ext = os.path.splitext(file)[1].lstrip('.').lower()
                if ext not in extensions:
                    continue
            filepath = os.path.join(root, file)
            try:
                stat = os.stat(filepath)
                size = stat.st_size
                if min_size and size < min_size:
                    continue
                if max_size and size > max_size:
                    continue
                mtime = stat.st_mtime
            except OSError:
                continue
            if search_text:
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        if search_text.lower() not in f.read().lower():
                            continue
                except:
                    continue
            results.append((filepath, size, datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")))
    for path, size, mod in results:
        print(f"{path}  ({size} байт, {mod})")
    print(f"\n✅ Найдено файлов: {len(results)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli_mode()
    else:
        root = Tk()
        app = FileSearchApp(root)
        root.mainloop()
