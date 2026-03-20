"""
Monte Carlo Tree Search (MCTS) for the AI player.

This module implements full MCTS with UCB1 selection, expansion, simulation
(random rollout), and backpropagation. Used ONLY when the current player is
the one whose name is exactly "AI".
"""

from __future__ import annotations

import copy
import math
import random
from typing import Any, Dict, List, Optional, Tuple

import evaluation
import rules

# ── Programmer-controlled knobs ──────────────────────────────────────────────
N_SIMULATIONS: int = 1000          # Total MCTS iterations (tree walks)
EXPLORATION_CONSTANT: float = 1.41  # C in UCB1 = sqrt(2) ≈ 1.41
MAX_ROLLOUT_STEPS: int = 10_000   # Safety cap on rollout depth
# ─────────────────────────────────────────────────────────────────────────────


def clone_state(game_state):
    """Returns a deep copy of the game state for simulations."""
    return copy.deepcopy(game_state)


def get_ai_player(game_state):
    """
    Returns the player object whose name is exactly "AI".

    Raises:
        ValueError: if no such player exists in game_state.players.
    """
    for p in getattr(game_state, "players", []):
        if getattr(p, "name", None) == "AI":
            return p
    raise ValueError('No player named exactly "AI" found in game_state.players.')


def get_opponent_player(game_state):
    """
    Returns the other (non-AI) player.

    Raises:
        ValueError: if an AI player is missing, or the opponent cannot be inferred.
    """
    ai = get_ai_player(game_state)
    for p in getattr(game_state, "players", []):
        if p is not ai:
            return p
    raise ValueError("Opponent player not found (expected a 2-player game).")


def _action_key(action) -> Tuple[Any, ...]:
    """
    Stable, hashable identifier for actions.

    rules.Action is a non-frozen dataclass so we build a tuple key.
    """
    a_type = getattr(action, "type", None)
    a_path = getattr(action, "path", None)
    path_id = None
    if a_path is not None:
        if hasattr(a_path, "get_path_id"):
            try:
                path_id = a_path.get_path_id()
            except Exception:
                path_id = None
        if path_id is None and hasattr(a_path, "path_id"):
            path_id = getattr(a_path, "path_id", None)
    return (a_type, path_id, repr(action))


# ═══════════════════════════════════════════════════════════════════════════════
#  MCTS Node
# ═══════════════════════════════════════════════════════════════════════════════

class MCTSNode:
    """A single node in the MCTS tree."""

    __slots__ = (
        "state", "parent", "parent_action", "children",
        "untried_actions", "visit_count", "total_value", "player_name",
    )

    def __init__(self, state, parent: Optional["MCTSNode"] = None,
                 parent_action=None, player_name: str = "AI"):
        self.state = state
        self.parent = parent
        self.parent_action = parent_action   # action that led here from parent
        self.children: List[MCTSNode] = []
        self.visit_count: int = 0
        self.total_value: float = 0.0
        self.player_name = player_name

        # Pre-compute the untried (unexpanded) legal actions for this node.
        if rules.is_terminal(state):
            self.untried_actions: list = []
        else:
            actions = rules.legal_actions(state)
            # Filter out "quit" – that's a human-only action.
            self.untried_actions = [a for a in actions if getattr(a, "type", None) != "q"]

    # ── properties ────────────────────────────────────────────────────────

    @property
    def is_terminal(self) -> bool:
        return rules.is_terminal(self.state)

    @property
    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0

    @property
    def average_value(self) -> float:
        if self.visit_count == 0:
            return 0.0
        return self.total_value / self.visit_count

    # ── UCB1 ──────────────────────────────────────────────────────────────

    def ucb1(self, c: float = EXPLORATION_CONSTANT) -> float:
        """Upper Confidence Bound for Trees (UCT)."""
        if self.visit_count == 0:
            return float("inf")  # Always try unvisited children first.
        exploitation = self.total_value / self.visit_count
        exploration = c * math.sqrt(math.log(self.parent.visit_count) / self.visit_count)
        return exploitation + exploration

    # ── MCTS phases ───────────────────────────────────────────────────────

    def best_child(self, c: float = EXPLORATION_CONSTANT) -> "MCTSNode":
        """Select the child with the highest UCB1 score."""
        return max(self.children, key=lambda child: child.ucb1(c))

    def expand(self) -> "MCTSNode":
        """
        Expand one untried action: pop it, apply it to a cloned state,
        create a child node, and return it.
        """
        action = self.untried_actions.pop()
        child_state = clone_state(self.state)
        rules.apply_action(child_state, action)
        child_node = MCTSNode(
            state=child_state,
            parent=self,
            parent_action=action,
            player_name=self.player_name,
        )
        self.children.append(child_node)
        return child_node

    def rollout(self) -> float:
        """
        Run a random playout from this node's state to a terminal state
        and return the utility from the AI's perspective.
        """
        sim = clone_state(self.state)
        ai_player = next((p for p in sim.players if p.name == self.player_name), None)
        if ai_player is None:
            raise ValueError(f"Player '{self.player_name}' not found in simulation.")
        opponent_player = next((p for p in sim.players if p.name != self.player_name), None)

        steps = 0
        while not rules.is_terminal(sim):
            steps += 1
            if steps > MAX_ROLLOUT_STEPS:
                setattr(sim, "terminal", True)
                setattr(sim, "terminal_reason", "rollout_step_limit")
                break

            actions = rules.legal_actions(sim)
            if not actions:
                setattr(sim, "terminal", True)
                setattr(sim, "terminal_reason", "no_legal_actions")
                break

            action = random.choice(actions)
            ok = rules.apply_action(sim, action)
            if ok is False:
                setattr(sim, "terminal", True)
                setattr(sim, "terminal_reason", "apply_action_failed")
                break

        return evaluation.utility(sim, ai_player, opponent_player)

    def backpropagate(self, result: float):
        """Propagate the simulation result up to the root."""
        node = self
        while node is not None:
            node.visit_count += 1
            node.total_value += result
            node = node.parent


# ═══════════════════════════════════════════════════════════════════════════════
#  MCTS Search
# ═══════════════════════════════════════════════════════════════════════════════

def mcts_search(game_state, n_iterations: int = N_SIMULATIONS,
                exploration_constant: float = EXPLORATION_CONSTANT):
    """
    Run MCTS from the given game state and return the best action.

    The four phases per iteration:
      1. Selection  – walk down the tree picking best UCB1 children
      2. Expansion  – if the selected node is not terminal, expand one child
      3. Simulation – random rollout from the new child to a terminal state
      4. Backpropagation – propagate the result back up the tree

    Returns:
        (best_action, action_stats)
        action_stats is a list of (action, visits, avg_value) for every
        root child, useful for diagnostics.
    """
    current_player = getattr(game_state, "current_player", None)
    if current_player is None:
        return None, []
    player_name = getattr(current_player, "name", "AI")

    root = MCTSNode(state=clone_state(game_state), player_name=player_name)

    if root.is_terminal or (root.is_fully_expanded and not root.children):
        return None, []

    for _ in range(n_iterations):
        node = root

        # 1. Selection – descend while fully expanded and non-terminal
        while node.is_fully_expanded and node.children:
            node = node.best_child(exploration_constant)

        # 2. Expansion – expand one untried action (if not terminal)
        if not node.is_terminal and not node.is_fully_expanded:
            node = node.expand()

        # 3. Simulation – random rollout
        result = node.rollout()

        # 4. Backpropagation
        node.backpropagate(result)

    # Choose the root child with the most visits (robust child selection).
    if not root.children:
        return None, []

    best_child = max(root.children, key=lambda c: c.visit_count)
    best_action = best_child.parent_action

    # Collect stats for all root children.
    action_stats = []
    for child in root.children:
        avg = child.total_value / child.visit_count if child.visit_count > 0 else 0.0
        action_stats.append((child.parent_action, child.visit_count, avg))

    return best_action, action_stats


# ═══════════════════════════════════════════════════════════════════════════════
#  Public API  (backwards-compatible with old_search.py)
# ═══════════════════════════════════════════════════════════════════════════════

def choose_best_action_monte_carlo(game_state, n_simulations: int = N_SIMULATIONS):
    """
    Choose the best action using MCTS.

    Returns the same 5-tuple as the old flat Monte Carlo version so that
    callers don't need to change:
        (best_action, action_values, best_wins, best_n, action_win_stats)

    - action_values: dict mapping action_key -> average value
    - best_wins / best_n: visit count for the chosen action (wins ≈ visits
      with positive value, kept for compatibility)
    - action_win_stats: list of (action, wins, n, avg_value)
    """
    best_action, stats = mcts_search(game_state, n_iterations=n_simulations)

    action_values: Dict[Tuple[Any, ...], float] = {}
    action_win_stats = []
    best_wins = 0
    best_n = 0

    for action, visits, avg_value in stats:
        key = _action_key(action)
        action_values[key] = avg_value
        # "wins" = visits that had positive utility (approximated by avg > 0).
        wins = int(visits * max(0, avg_value) / max(abs(avg_value), 1e-9)) if visits > 0 else 0
        wins = min(wins, visits)  # clamp
        action_win_stats.append((action, wins, visits, avg_value))

        if best_action is not None and repr(action) == repr(best_action):
            best_wins = wins
            best_n = visits

    return best_action, action_values, best_wins, best_n, action_win_stats


def choose_action(observable_state, n_simulations: int = N_SIMULATIONS):
    """
    Backwards-compatible integration hook.

    If it is the AI's turn, returns the MCTS best action.
    If it is not the AI's turn, returns None.
    """
    current_player = getattr(observable_state, "current_player", None)
    if current_player is None and hasattr(observable_state, "players") and hasattr(
        observable_state, "current_player_index"
    ):
        try:
            current_player = observable_state.players[int(observable_state.current_player_index)]
        except Exception:
            current_player = None

    if getattr(current_player, "name", None) != "AI":
        return None

    if not hasattr(observable_state, "deck"):
        raise ValueError(
            "choose_action(...) requires the full state object (with .deck) for rollouts; "
            "an AI-observable view was provided."
        )

    best_action, _, _, _, _ = choose_best_action_monte_carlo(observable_state, n_simulations=n_simulations)
    return best_action
