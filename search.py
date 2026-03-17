"""
Monte Carlo rollout search for the AI player.

This module implements a simple, readable Monte Carlo search (NOT MCTS) that is
used ONLY when the current player is the one whose name is exactly "AI".
"""

from __future__ import annotations

import copy
import random
from typing import Any, Dict, Optional, Tuple

import evaluation
import rules


def clone_state(game_state):
    """
    Returns a deep copy of the game state for simulations.

    We use deepcopy to ensure simulations never mutate the real game state.
    """
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

    Note: rules.Action is a non-frozen dataclass, so it is typically unhashable.
    We therefore keep action-values in a dict keyed by a tuple.
    """
    a_type = getattr(action, "type", None)
    a_path = getattr(action, "path", None)
    # Prefer an explicit path id if available, else fall back to repr.
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


def random_rollout(sim_state):
    """
    Starting from a simulation state, play random legal actions until terminal.

    During rollouts, BOTH players may act randomly. The terminal score is always
    evaluated from the AI perspective using evaluation.utility(...).
    """
    # Resolve the AI/opponent objects *inside the simulation state* (deepcopied objects).
    ai_player = get_ai_player(sim_state)
    opponent_player = get_opponent_player(sim_state)

    # Safety valve in case a bug creates non-terminating dynamics.
    max_steps = 10_000
    steps = 0

    while not rules.is_terminal(sim_state):
        steps += 1
        if steps > max_steps:
            # Mark terminal to avoid infinite loops in rollout.
            setattr(sim_state, "terminal", True)
            setattr(sim_state, "terminal_reason", "rollout_step_limit")
            break

        actions = rules.legal_actions(sim_state)
        if not actions:
            # If there are no legal actions, end the rollout safely.
            setattr(sim_state, "terminal", True)
            setattr(sim_state, "terminal_reason", "no_legal_actions")
            break

        # Choose a random legal action and apply it.
        action = random.choice(actions)
        ok = rules.apply_action(sim_state, action)
        if ok is False:
            # If apply_action refuses the action, terminate to avoid stalling.
            setattr(sim_state, "terminal", True)
            setattr(sim_state, "terminal_reason", "apply_action_failed")
            break

    return evaluation.utility(sim_state, ai_player, opponent_player)


def monte_carlo_action_value(game_state, action, n_simulations: int = 50):
    """
    Estimate the value of one candidate action using random rollouts.

    Procedure:
      - clone the state
      - apply the candidate action once
      - run n_simulations independent random rollouts from that resulting state
      - return the average terminal utility
    """
    if n_simulations <= 0:
        raise ValueError("n_simulations must be >= 1")

    base = clone_state(game_state)
    ok = rules.apply_action(base, action)
    if ok is False:
        # Illegal or failed application: treat as extremely bad.
        return float("-inf")

    total = 0.0
    for _ in range(n_simulations):
        sim = clone_state(base)
        total += float(random_rollout(sim))

    return total / float(n_simulations)


def choose_best_action_monte_carlo(game_state, n_simulations: int = 50):
    """
    Choose the best action for the AI using plain Monte Carlo rollout evaluation.

    Returns:
      - best_action: the selected action object (or None if no legal actions exist)
      - action_values: dict mapping action_key -> average rollout utility

    Raises:
        ValueError: if called when it is not the AI's turn.
    """
    current_player = getattr(game_state, "current_player", None)
    current_name = getattr(current_player, "name", None)
    if current_name != "AI":
        raise ValueError(
            f'Monte Carlo search is only allowed on AI turn (current player is "{current_name}").'
        )

    actions = rules.legal_actions(game_state)
    if not actions:
        return None, {}

    # The rules module intends early-quit to be human-only.
    # Some UIs may accidentally mark the AI as type="human", which would make "q" appear.
    # We explicitly remove quit for the AI to keep rollouts meaningful.
    actions = [a for a in actions if getattr(a, "type", None) != "q"]
    if not actions:
        return None, {}

    action_values: Dict[Tuple[Any, ...], float] = {}
    best_action = None
    best_value = float("-inf")

    for a in actions:
        v = monte_carlo_action_value(game_state, a, n_simulations=n_simulations)
        action_values[_action_key(a)] = float(v)
        if v > best_value:
            best_value = float(v)
            best_action = a

    return best_action, action_values


def choose_action(observable_state, n_simulations: int = 50):
    """
    Backwards-compatible integration hook.

    If it is the AI's turn, returns the Monte Carlo best action.
    If it is not the AI's turn, returns None (human is not controlled here).
    """
    # Support both:
    # - full state: .current_player property
    # - AI-observable view: .players + .current_player_index integer
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

    # Note: rules.legal_actions/apply_action require the FULL underlying state (deck, hands, etc).
    # If an observable-only view is passed in, fail loudly with a clear message.
    if not hasattr(observable_state, "deck"):
        raise ValueError(
            "choose_action(...) requires the full state object (with .deck) for rollouts; "
            "an AI-observable view was provided."
        )

    best_action, _ = choose_best_action_monte_carlo(observable_state, n_simulations=n_simulations)
    return best_action


# --- Usage example (e.g., in main.py) ---
#
# import rules
# import search
#
# # game_state is your full state.state(...) instance
# if game_state.current_player.name == "AI":
#     action, values = search.choose_best_action_monte_carlo(game_state, n_simulations=50)
#     if action is not None:
#         rules.apply_action(game_state, action)
# else:
#     # Human turn: choose action via UI / input, NOT Monte Carlo.
#     pass
