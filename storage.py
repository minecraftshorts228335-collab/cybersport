import csv
import json
import logging
from models import Player, Team, TournamentError

logging.basicConfig(
    filename="tournament.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TournamentStorage")

class StorageHandler:
    @staticmethod
    def import_from_csv(file_path: str, manager) -> None:
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    p_id = int(row['id'])
                    p_type = row['type'].strip().lower()
                    name = row['name'].strip()
                    game = row['game'].strip()
                    rating = int(row.get('rating', 1000))

                    if p_type == 'player':
                        participant = Player(id=p_id, nickname=name, game=game, rating=rating)
                    elif p_type == 'team':
                        members = int(row.get('members_count', 5))
                        participant = Team(id=p_id, name=name, game=game, rating=rating, members_count=members)
                    else:
                        continue
                    
                    try:
                        manager.add_participant(participant)
                    except TournamentError:
                        pass
            logger.info(f"Данные успешно импортированы из {file_path}")
        except Exception as e:
            logger.error(f"Ошибка при чтении CSV файла: {e}")
            raise TournamentError(f"Не удалось импортировать CSV: {e}")

    @staticmethod
    def save_to_json(file_path: str, manager) -> None:
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
                ]
            }
            with open(file_path, mode='w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logger.info(f"Состояние сохранено в JSON: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка сохранения JSON: {e}")
            raise TournamentError(f"Не удалось сохранить JSON: {e}")