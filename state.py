# state.py

from dataclasses import dataclass, field
from typing import List, Optional, Literal

import classes  # uses graph, player, deck, route_card as defined there


# -------------------------
# Action representation
# -------------------------

ActionType = Literal["draw_card", "claim_route"]


@dataclass(frozen=True)
class Action:
    """
    Generic action in the simplified Ticket to Ride game.

    - type = "draw_card": no extra data needed (always draw top of deck).
    - type = "claim_route": path_id identifies which path to claim.
    """
    type: ActionType
    path_id: Optional[int] = None

    @staticmethod
    def draw_card() -> "Action":
        return Action(type="draw_card")

    @staticmethod
    def claim_route(path_id: int) -> "Action":
        return Action(type="claim_route", path_id=path_id)


# -------------------------
# Player state
# -------------------------

@dataclass
class PlayerState:
    """
    Wraps the existing classes.player but adds explicit fields we care about
    for search and evaluation.

    For now we keep a reference to the underlying classes.player instance
    to avoid breaking existing code.
    """
    # Underlying domain object
    obj: classes.player

    # Convenience mirrors (kept in sync with obj where needed)
    name: str
    score: int = 0
    trains: int = 44
    # cards: list of classes.card or colour strings (you already use both)
    cards: list = field(default_factory=list)
    # route: destination ticket; for now keep your dict shape
    # {"start": str, "end": str, "points": int}
    route: Optional[dict] = None

    def sync_from_obj(self) -> None:
        """
        Synchronise from the underlying classes.player to this PlayerState.
        Call this if legacy code mutates classes.player directly.
        """
        self.name = self.obj.name
        self.score = self.obj.score
        self.cards = list(self.obj.cards)
        self.trains = self.obj.trains
        self.route = self.obj.route

    def sync_to_obj(self) -> None:
        """
        Synchronise this PlayerState back into the underlying classes.player.
        Call this after rules/engine functions update PlayerState.
        """
        self.obj.score = self.score
        self.obj.cards = list(self.cards)
        self.obj.trains = self.trains
        self.obj.route = self.route


# -------------------------
# Game state
# -------------------------

@dataclass
class GameState:
    """
    Full game state for the simplified Ticket to Ride model.

    This is the object that:
      - rules.py will read/modify
      - evaluation (U_s, E_s) will inspect
      - search.py will copy and traverse
    """
    graph: classes.graph                 # static board (cities + paths)
    players: List[PlayerState]           # two players: [human, AI] (by convention)
    deck: classes.deck                   # remaining train cards

    # Turn / phase
    current_player_index: int = 0        # index into players
    turn_number: int = 0                 # counts full turns or actions, as you prefer

    # Endgame bookkeeping
    endgame_triggered: bool = False
    endgame_trigger_player_index: Optional[int] = None
    final_turns_remaining: int = 0       # e.g. 0 until endgame triggered

    # Optional: cache for longest-path computations, etc.
    longest_route_points: int = 10       # matches classes.game default

    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def other_player(self) -> PlayerState:
        # two-player game; the other is 1 - current
        return self.players[1 - self.current_player_index]

    def copy_shallow(self) -> "GameState":
        """
        Shallow-ish copy suitable for search if you are careful not to
        mutate shared objects in place. For a fully safe search you may
        want a deeper copy strategy later.
        """
        return GameState(
            graph=self.graph,                     # shared; board is mostly static
            players=[p for p in self.players],    # shallow copy of list
            deck=self.deck,                       # shared; rules must be careful
            current_player_index=self.current_player_index,
            turn_number=self.turn_number,
            endgame_triggered=self.endgame_triggered,
            endgame_trigger_player_index=self.endgame_trigger_player_index,
            final_turns_remaining=self.final_turns_remaining,
            longest_route_points=self.longest_route_points,
        )