
from dataclasses import dataclass
import random
import game
from game import path as Path


@dataclass
class Action:
    """
    Lightweight action representation.
    type: \"d\" (draw) or \"c\" (claim).
    """
    type: str
    path: Path = None  # None if draw; the path to claim if type \"c\"

def claim_route(state, path):
    player = state.current_player
    colour = path.colour
    train_count = path.distance

    matching_cards = [card for card in player.cards if card.colour == colour]

    if len(matching_cards) < train_count:
        return False

    cards_to_remove = matching_cards[:train_count]
    for card in cards_to_remove:
        player.cards.remove(card)
    state.discard.extend(cards_to_remove)

    path.occupation = player.name
    player.trains -= train_count
    # Endgame trigger: once any player hits <= 2 trains, start final-turn countdown.
    if (not state.endgame_triggered) and player.trains <= 2:
        state.endgame_triggered = True
        state.final_turns_remaining = len(state.players)

    return path

def draw_card(state):
    player = state.current_player
    if state.deck.cards: 
        card = state.deck.cards.pop(0) # remocves top card from deck
        player.cards.append(card)
    else: 
        return False # No cards in deck

def apply_action(state, action):
    """Apply one action for the current player and advance the turn counter."""
    if action.type == "d":
        draw_card(state)
    elif action.type == "c":
        claim_route(state, action.path)
    else:
        return False
    state.current_round += 1
    if state.endgame_triggered:
        state.final_turns_remaining = max(0, state.final_turns_remaining - 1)
    return True

def legal_actions(state):
    possible_actions = []

    # Draw is only legal if deck non-empty
    if state.deck.get_card_count() > 0:
        possible_actions.append(Action("d"))

    # Get all possible paths to place
    player = state.current_player
    for path in state.graph.paths:  # loop through all paths

        colour = path.colour
        train_count = path.distance 
        matching_cards = [card for card in player.cards if card.colour == colour]
        
        if path.occupation: 
            continue # occupied: exclude from possible
        if player.trains < train_count:
            continue # not enough trains left
        if len(matching_cards) < train_count: 
            continue # Not enough cards: exclude from possible
        else:
            claim_path_action = Action("c", path) # We good: add to 
            possible_actions.append(claim_path_action)
    
    return possible_actions

def human_decide_action(state):

    all_possible_actions = legal_actions(state)
    selected_path = None

    while True:
        d_or_c = input("Choose action: (d)raw or (c)laim: ").strip().lower()
        if d_or_c == "c":
            selected_path_id = input("Enter path id to claim: ").strip()
            selected_path = game.get_path_from_id(state.graph, selected_path_id)
        chosen_action = Action(d_or_c, selected_path)
        if chosen_action in all_possible_actions:
            print(f"action {chosen_action} valid")
            return chosen_action
        else:
            print("Invalid action. Type 'd' to draw or 'c' to claim.")
            print("Make sure the path you claim is available")

def decide_action(state):
    """
    Returns an action for the current player.

    For now:
    - human: interactive input
    - ai/random: random legal action placeholder (until MCTS is implemented)
    """
    player = state.current_player

    if player.type == "human":
        return human_decide_action(state)

    if player.type in ("ai", "random", "monte_carlo"):
        actions = legal_actions(state)
        return random.choice(actions) if actions else Action("d")

    # Fallback to interactive
    return human_decide_action(state)


def is_terminal(state):
    """Terminal condition for the simplified endgame scaffolding."""
    return state.endgame_triggered and state.final_turns_remaining == 0


# Backwards-compatible aliases for older names used in notebooks/experiments.
claim = claim_route
draw = draw_card
action = Action