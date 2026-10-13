from dataclasses import dataclass
from collections import deque
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class TournamentError(Exception):
    pass

class BaseParticipant(ABC):
    @abstractmethod
    def get_info(self) -> str:
        pass

@dataclass
class Player(BaseParticipant):
    id: int
    nickname: str
    game: str
    rating: int = 1000

    def get_info(self) -> str:
        return f"Игрок: {self.nickname} [Игра: {self.game}, Рейтинг: {self.rating}]"

@dataclass
class Team(BaseParticipant):
    id: int
    name: str
    game: str
    rating: int = 1000
    members_count: int = 5

    def get_info(self) -> str:
        return f"Команда: {self.name} [Игра: {self.game}, Участников: {self.members_count}, Рейтинг: {self.rating}]"

@dataclass
class Match:
    team_a: str
    team_b: str
    status: str = "Запланирован"

class TournamentManager:
    """Менеджер, использующий композицию (хранит список, словарь участников и deque для очереди матчей)."""
    def __init__(self):
        self.participants: List[BaseParticipant] = []
        self.participants_dict: Dict[int, BaseParticipant] = {}
        # Использование deque для очереди матчей (требование курса)
        self.match_queue: deque = deque()

    def add_participant(self, participant: BaseParticipant) -> None:
        if participant.id in self.participants_dict:
            raise TournamentError(f"Участник с ID {participant.id} уже существует.")
        self.participants.append(participant)
        self.participants_dict[participant.id] = participant

    def delete_participant(self, p_id: int) -> None:
        if p_id not in self.participants_dict:
            raise TournamentError(f"Участник с ID {p_id} не найден.")
        participant = self.participants_dict.pop(p_id)
        self.participants = [p for p in self.participants if p.id != p_id]

    def add_match(self, team_a: str, team_b: str) -> None:
        self.match_queue.append(Match(team_a=team_a, team_b=team_b))

    def pop_match(self) -> None:
        if self.match_queue:
            self.match_queue.popleft()

    # Собственный линейный поиск O(N)
    def search_participants_by_query(self, query: str) -> List[BaseParticipant]:
        if not query:
            return self.participants
        query_lower = query.lower()
        return [
            p for p in self.participants 
            if query_lower in (getattr(p, 'nickname', None) or getattr(p, 'name', '')).lower()
        ]

    # Собственная сортировка Bubble Sort O(N^2)
    def sort_participants_by_rating(self, reverse: bool = True) -> List[BaseParticipant]:
        arr = list(self.participants)
        n = len(arr)
        for i in range(n):
            swapped = False
            for j in range(0, n - i - 1):
                if (arr[j].rating < arr[j + 1].rating) if reverse else (arr[j].rating > arr[j + 1].rating):
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                    swapped = True
            if not swapped:
                break
        return arr

    # Генератор для ленивой обработки записей (требование курса)
    def generate_top_participants(self, limit: int = 3):
        sorted_list = self.sort_participants_by_rating(reverse=True)
        for participant in sorted_list[:limit]:
            yield participant