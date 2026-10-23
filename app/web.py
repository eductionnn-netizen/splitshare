"""Local web interface for SplitShare."""
import argparse
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import uuid
from urllib.parse import urlsplit
import importlib.resources

try:
    from .splitshare import calculate
except ImportError:
    from splitshare import calculate

MAX_AMOUNT = 100_000_000_000


def text(value, label, maximum=80):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValueError(f"{label}: введите от 1 до {maximum} символов")
    return value.strip()


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS groups (id TEXT PRIMARY KEY, data TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def list(self):
        with self.connect() as db:
            return [self.summary(json.loads(row[0])) for row in db.execute("SELECT data FROM groups ORDER BY rowid")]

    @staticmethod
    def summary(group):
        return {key: group[key] for key in ("id", "name", "members")}

    def get(self, group_id):
        with self.connect() as db:
            row = db.execute("SELECT data FROM groups WHERE id=?", (group_id,)).fetchone()
        if row is None:
            raise KeyError("Группа не найдена")
        return json.loads(row[0])

    def create(self, data):
        name = text(data.get("name"), "Название группы")
        members = data.get("members")
        if not isinstance(members, list) or not 2 <= len(members) <= 20:
            raise ValueError("Добавьте от 2 до 20 участников")
        members = [text(member, "Имя участника", 50) for member in members]
        calculate({"members": members, "expenses": []})
        group = {"id": str(uuid.uuid4()), "name": name, "members": members, "expenses": []}
        with self.connect() as db:
            db.execute("INSERT INTO groups VALUES (?, ?)", (group["id"], json.dumps(group, ensure_ascii=False)))
        return group

    def mutate(self, group_id, payload=None, expense_id=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT data FROM groups WHERE id=?", (group_id,)).fetchone()
            if row is None:
                raise KeyError("Группа не найдена")
            group = json.loads(row[0])
            if expense_id is not None:
                if not any(e["id"] == expense_id for e in group["expenses"]):
                    raise KeyError("Расход не найден")
                group["expenses"] = [e for e in group["expenses"] if e["id"] != expense_id]
            else:
                request_id = text(payload.get("id"), "Идентификатор расхода", 64)
                expense = {"id": request_id, "title": text(payload.get("title"), "Название расхода"),
                           "date": payload.get("date"), "payer": payload.get("payer"),
                           "amount_kopecks": payload.get("amount_kopecks"),
                           "participants": payload.get("participants")}
                try:
                    parsed_date = date.fromisoformat(expense["date"])
                    if parsed_date.isoformat() != expense["date"]:
                        raise ValueError()
                except (TypeError, ValueError):
                    raise ValueError("Укажите дату расхода в формате ГГГГ-ММ-ДД")
                amount = expense["amount_kopecks"]
                if type(amount) is not int or not 0 < amount <= MAX_AMOUNT:
                    raise ValueError("Сумма должна быть больше нуля и не превышать 1 млрд рублей")
                calculate({"members": group["members"], "expenses": [expense]})
                existing = next((e for e in group["expenses"] if e["id"] == request_id), None)
                if existing:
                    if existing != expense:
                        raise ValueError("Этот идентификатор уже используется другим расходом")
                    return group
                if len(group["expenses"]) >= 1000:
                    raise ValueError("В группе может быть не более 1000 расходов")
                group["expenses"].append(expense)
            db.execute("UPDATE groups SET data=? WHERE id=?", (json.dumps(group, ensure_ascii=False), group_id))
        return group


def response(group):
    return {**group, "result": calculate(group),
            "total_kopecks": sum(e["amount_kopecks"] for e in group["expenses"])}


def make_server(port=8787, database=".local-data/splitshare.sqlite3"):
    store = Store(database)
    static = importlib.resources.files("app").joinpath("static")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send(self, code, data, mime="application/json; charset=utf-8"):
            raw = json.dumps(data, ensure_ascii=False).encode() if isinstance(data, (dict, list)) else data
            self.send_response(code)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(raw)

        def handle_request(self):
            try:
                expected = f"127.0.0.1:{self.server.server_port}"
                if self.headers.get("Host") not in (expected, f"localhost:{self.server.server_port}"):
                    return self.send(403, {"error": "Недопустимый адрес сервера"})
                origin = self.headers.get("Origin")
                if origin and origin not in (f"http://{expected}", f"http://localhost:{self.server.server_port}"):
                    return self.send(403, {"error": "Запрос с другого сайта отклонён"})
                path = urlsplit(self.path).path
                if self.command == "GET" and path in ("/", "/app.js", "/style.css"):
                    filename, mime = {"/": ("index.html", "text/html; charset=utf-8"),
                                      "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                                      "/style.css": ("style.css", "text/css; charset=utf-8")}[path]
                    return self.send(200, (static / filename).read_bytes(), mime)
                data = None
                if self.command == "POST":
                    if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                        return self.send(415, {"error": "Ожидается JSON"})
                    size = int(self.headers.get("Content-Length", "0"))
                    if not 0 < size <= 65536:
                        return self.send(413, {"error": "Недопустимый размер запроса"})
                    data = json.loads(self.rfile.read(size))
                    if not isinstance(data, dict):
                        raise ValueError("Ожидается JSON-объект")
                parts = path.strip("/").split("/")
                if parts == ["api", "groups"]:
                    if self.command == "GET":
                        return self.send(200, store.list())
                    if self.command == "POST":
                        return self.send(201, response(store.create(data)))
                if len(parts) >= 3 and parts[:2] == ["api", "groups"]:
                    group_id = parts[2]
                    if len(parts) == 3 and self.command == "GET":
                        return self.send(200, response(store.get(group_id)))
                    if len(parts) == 4 and parts[3] == "expenses" and self.command == "POST":
                        return self.send(200, response(store.mutate(group_id, data)))
                    if len(parts) == 5 and parts[3] == "expenses" and self.command == "DELETE":
                        return self.send(200, response(store.mutate(group_id, expense_id=parts[4])))
                return self.send(404, {"error": "Страница не найдена"})
            except KeyError as error:
                self.send(404, {"error": error.args[0]})
            except (ValueError, UnicodeError) as error:
                self.send(400, {"error": str(error)})
            except (OSError, sqlite3.Error):
                self.send(500, {"error": "Не удалось прочитать или сохранить данные. Повторите попытку."})

        do_GET = do_POST = do_DELETE = handle_request

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description="SplitShare — приложение в браузере")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--open", action="store_true", help="Открыть интерфейс в браузере")
    parser.add_argument("--database", default=str(Path.home() / ".splitshare" / "splitshare.sqlite3"))
    args = parser.parse_args()
    server = make_server(args.port, args.database)
    print(f"SplitShare: http://127.0.0.1:{server.server_port}", flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
