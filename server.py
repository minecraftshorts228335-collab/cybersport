import http.server
import socketserver
import urllib.parse
import os
import csv
import json
import logging
from models import TournamentManager, Player, Team, TournamentError

# Настройка логирования ключевых событий (требование надежности)
logging.basicConfig(
    filename="tournament.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TournamentApp")

PORT = 8000
manager = TournamentManager()

DATA_CSV = "data/participants.csv"
DATA_JSON = "data/tournament.json"

def init_storage():
    os.makedirs("data", exist_ok=True)
    # Создадим начальный CSV, если его нет
    if not os.path.exists(DATA_CSV):
        with open(DATA_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "type", "name", "game", "rating", "members_count"])
            writer.writerow([1, "player", "ShadowFiend", "Dota 2", "1450", ""])
            writer.writerow([2, "team", "NaVi", "CS2", "1600", "5"])
            writer.writerow([3, "player", "Simple", "CS2", "1850", ""])

    # Чтение из CSV при старте
    try:
        with open(DATA_CSV, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                p_id = int(row['id'])
                p_type = row['type'].strip().lower()
                name = row['name'].strip()
                game = row['game'].strip()
                rating = int(row.get('rating', 1000))

                if p_type == 'player':
                    p = Player(id=p_id, nickname=name, game=game, rating=rating)
                else:
                    members = int(row.get('members_count', 5))
                    p = Team(id=p_id, name=name, game=game, rating=rating, members_count=members)
                
                try:
                    manager.add_participant(p)
                except TournamentError:
                    pass
        logger.info("Данные успешно импортированы из CSV при запуске.")
    except Exception as e:
        logger.error(f"Ошибка загрузки CSV: {e}")

def save_to_json():
    """Сохранение состояния в JSON (требование курса)."""
    try:
        data = {
            "participants": [
                {
                    "id": p.id,
                    "type": "player" if isinstance(p, Player) else "team",
                    "name": getattr(p, 'nickname', None) or getattr(p, 'name', ''),
                    "game": p.game,
                    "rating": p.rating
                } for p in manager.participants
            ],
            "matches": [
                {"team_a": m.team_a, "team_b": m.team_b, "status": m.status} 
                for m in manager.match_queue
            ]
        }
        with open(DATA_JSON, mode='w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info("Состояние успешно сохранено в JSON.")
    except Exception as e:
        logger.error(f"Ошибка сохранения JSON: {e}")

init_storage()
# Добавим дефолтный матч для демонстрации очереди deque
if not manager.match_queue:
    manager.add_match("NaVi", "Team Spirit")

class TournamentHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = urllib.parse.parse_qs(parsed_path.query)

        if path == "/" or path == "/index.html":
            search_query = query_params.get("search", [""])[0].strip()
            sort_type = query_params.get("sort", ["none"])[0]

            participants = manager.search_participants_by_query(search_query)
            if sort_type == "rating":
                participants = manager.sort_participants_by_rating(reverse=True)

            top_list = list(manager.generate_top_participants(3))

            html = f"""<!DOCTYPE html>
            <html lang="ru">
            <head>
                <meta charset="UTF-8">
                <title>Киберспортивный Турнир | Dashboard</title>
                <link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
                <style>
                    :root {{
                        --bg-color: #0f172a;
                        --card-bg: #1e293b;
                        --accent-color: #38bdf8;
                        --accent-hover: #0ea5e9;
                        --text-main: #f8fafc;
                        --text-muted: #94a3b8;
                        --border-color: #334155;
                        --success-color: #10b981;
                        --danger-color: #ef4444;
                    }}
                    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                    body {{
                        font-family: 'Inter', sans-serif;
                        background-color: var(--bg-color);
                        color: var(--text-main);
                        padding: 40px 20px;
                    }}
                    .container {{ max-width: 950px; margin: 0 auto; }}
                    header {{ text-align: center; margin-bottom: 30px; }}
                    h1 {{
                        font-family: 'Rajdhani', sans-serif;
                        font-size: 2.5rem;
                        font-weight: 700;
                        color: var(--text-main);
                        text-transform: uppercase;
                        text-shadow: 0 0 20px rgba(56, 189, 248, 0.3);
                    }}
                    h1 span {{ color: var(--accent-color); }}
                    .card {{
                        background-color: var(--card-bg);
                        border: 1px solid var(--border-color);
                        border-radius: 12px;
                        padding: 24px;
                        margin-bottom: 24px;
                        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                    }}
                    h2 {{
                        font-family: 'Rajdhani', sans-serif;
                        font-size: 1.4rem;
                        font-weight: 600;
                        margin-bottom: 16px;
                        color: var(--accent-color);
                        text-transform: uppercase;
                    }}
                    .top-list ul {{ list-style: none; }}
                    .top-list li {{
                        padding: 10px 14px;
                        background: rgba(15, 23, 42, 0.6);
                        border-left: 4px solid var(--success-color);
                        margin-bottom: 8px;
                        border-radius: 4px;
                        font-size: 0.95rem;
                    }}
                    .filter-form {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }}
                    input, select {{
                        background: var(--bg-color);
                        border: 1px solid var(--border-color);
                        color: var(--text-main);
                        padding: 10px 14px;
                        border-radius: 8px;
                        font-size: 0.95rem;
                        outline: none;
                        flex: 1;
                        min-width: 200px;
                    }}
                    input:focus, select:focus {{ border-color: var(--accent-color); }}
                    button, .btn {{
                        background-color: var(--accent-color);
                        color: #0f172a;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 8px;
                        font-weight: 600;
                        cursor: pointer;
                        text-decoration: none;
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        transition: 0.2s;
                    }}
                    button:hover, .btn:hover {{ background-color: var(--accent-hover); }}
                    .btn-secondary {{
                        background-color: transparent;
                        border: 1px solid var(--border-color);
                        color: var(--text-muted);
                    }}
                    .btn-danger {{
                        background-color: var(--danger-color);
                        color: white;
                        padding: 6px 12px;
                        font-size: 0.85rem;
                    }}
                    .btn-danger:hover {{ background-color: #dc2626; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                    th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border-color); font-size: 0.95rem; }}
                    th {{
                        background-color: rgba(15, 23, 42, 0.4);
                        font-family: 'Rajdhani', sans-serif;
                        font-size: 1.1rem;
                        color: var(--text-muted);
                        text-transform: uppercase;
                    }}
                    tr:hover td {{ background-color: rgba(56, 189, 248, 0.03); }}
                    .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }}
                    .badge-player {{ background: rgba(56, 189, 248, 0.15); color: var(--accent-color); }}
                    .badge-team {{ background: rgba(16, 185, 129, 0.15); color: var(--success-color); }}
                    .add-form {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
                    .add-form .full-width {{ grid-column: span 2; }}
                    .queue-box {{ display: flex; gap: 10px; flex-wrap: wrap; }}
                    .match-card {{
                        background: rgba(15, 23, 42, 0.5);
                        border: 1px solid var(--border-color);
                        padding: 12px 16px;
                        border-radius: 8px;
                        font-size: 0.9rem;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <header>
                        <h1>Киберспортивный <span>Турнир</span></h1>
                        <p style="color: var(--text-muted); margin-top: 5px;">Итоговый проект Python & CS (CSV, JSON, ООП, Deque, Логирование)</p>
                    </header>

                    <div class="card">
                        <h2>🏆 Топ-3 участника (Генератор)</h2>
                        <div class="top-list">
                            <ul>
                                {"".join([f"<li>⚡ {p.get_info()}</li>" for p in top_list])}
                            </ul>
                        </div>
                    </div>

                    <div class="card">
                        <h2>⚔️ Очередь матчей (Структура данных Deque)</h2>
                        <div class="queue-box" style="margin-bottom: 15px;">
                            {"".join([f"<div class='match-card'>🔥 <strong>{m.team_a}</strong> vs <strong>{m.team_b}</strong><br><span style='color: var(--text-muted); font-size: 0.8rem;'>Статус: {m.status}</span></div>" for m in manager.match_queue]) if manager.match_queue else "<p style='color: var(--text-muted);'>Очередь матчей пуста.</p>"}
                        </div>
                        <form method="POST" action="/match-action" style="display: flex; gap: 10px; align-items: center;">
                            <input type="text" name="team_a" placeholder="Команда А" required style="max-width: 200px;">
                            <input type="text" name="team_b" placeholder="Команда Б" required style="max-width: 200px;">
                            <button type="submit" name="action" value="add">Добавить матч в очередь</button>
                            <button type="submit" name="action" value="pop" class="btn-secondary">Провести первый матч (Popleft)</button>
                        </form>
                    </div>

                    <div class="card">
                        <h2>🔍 Поиск и Сортировка записей</h2>
                        <form class="filter-form" method="GET" action="/">
                            <input type="text" name="search" placeholder="Поиск по никнейму или команде..." value="{search_query}">
                            <button type="submit">Найти</button>
                            <a href="/" class="btn btn-secondary">Сбросить</a>
                            <a href="/?sort=rating" class="btn" style="background-color: #f59e0b; color: #0f172a;">Сортировать по рейтингу (Bubble Sort)</a>
                        </form>

                        <div style="overflow-x: auto;">
                            <table>
                                <tr>
                                    <th>ID</th>
                                    <th>Тип</th>
                                    <th>Имя / Никнейм</th>
                                    <th>Дисциплина</th>
                                    <th>Рейтинг</th>
                                    <th>Информация</th>
                                    <th>Действие</th>
                                </tr>
                                {"".join([f"<tr><td>#{p.id}</td><td><span class='badge {'badge-player' if isinstance(p, Player) else 'badge-team'}'>{'Игрок' if isinstance(p, Player) else 'Команда'}</span></td><td><strong>{getattr(p, 'nickname', None) or getattr(p, 'name', '')}</strong></td><td>{p.game}</td><td><span style='color: #f59e0b; font-weight: 600;'>{p.rating}</span></td><td style='color: var(--text-muted);'>{p.get_info()}</td><td><a href='/delete?id={p.id}' class='btn btn-danger'>Удалить</a></td></tr>" for p in participants])}
                            </table>
                        </div>
                    </div>

                    <div class="card">
                        <h2>➕ Добавить нового участника</h2>
                        <form class="add-form" method="POST" action="/add">
                            <input type="number" name="id" placeholder="ID (число, например 4)" required>
                            <select name="type">
                                <option value="player">Игрок</option>
                                <option value="team">Команда</option>
                            </select>
                            <input type="text" name="name" placeholder="Имя / Никнейм" required>
                            <input type="text" name="game" placeholder="Дисциплина (например, CS2)" required>
                            <input class="full-width" type="number" name="rating" placeholder="Рейтинг (по умолчанию 1000)" value="1000" required>
                            <button class="full-width" type="submit">Добавить в базу и сохранить в JSON</button>
                        </form>
                    </div>
                </div>
            </body>
            </html>"""

            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif path == "/delete":
            try:
                p_id = int(query_params.get("id", [0])[0])
                manager.delete_participant(p_id)
                save_to_json()
                logger.info(f"Участник с ID {p_id} удален.")
            except Exception as e:
                logger.error(f"Ошибка удаления участника: {e}")

            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        params = urllib.parse.parse_qs(post_data)

        if self.path == "/add":
            try:
                p_id = int(params.get("id", [0])[0])
                p_type = params.get("type", ["player"])[0]
                name = params.get("name", [""])[0]
                game = params.get("game", [""])[0]
                rating = int(params.get("rating", [1000])[0])

                if p_type == "player":
                    p = Player(id=p_id, nickname=name, game=game, rating=rating)
                else:
                    p = Team(id=p_id, name=name, game=game, rating=rating)

                manager.add_participant(p)
                save_to_json()
                logger.info(f"Добавлен участник: {name} (ID: {p_id})")
            except Exception as e:
                logger.error(f"Ошибка добавления участника: {e}")

        elif self.path == "/match-action":
            action = params.get("action", [""])[0]
            if action == "add":
                team_a = params.get("team_a", [""])[0]
                team_b = params.get("team_b", [""])[0]
                if team_a and team_b:
                    manager.add_match(team_a, team_b)
                    save_to_json()
                    logger.info(f"Добавлен матч в очередь: {team_a} vs {team_b}")
            elif action == "pop":
                manager.pop_match()
                save_to_json()
                logger.info("Проведен первый матч из очереди (popleft).")

        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), TournamentHandler) as httpd:
        print(f"Сайт запущен! Откройте в браузере: http://localhost:{PORT}")
        httpd.serve_forever()