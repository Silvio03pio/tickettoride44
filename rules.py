
from dataclasses import dataclass
import random
import game
from game import path as Path
import evaluation


@dataclass
class Action:
    """
    Lightweight action representation.
    type: \"d\" (draw), \"c\" (claim), or \"q\" (quit/end early).
    """
    type: str
    path: Path = None  # None if draw; the path to claim if type \"c\"

def claim_path(state, path):
    player = state.current_player
    colour = path.colour
    train_count = path.distance

    # Safety guard: do not allow (or score) claiming an already-occupied path.
    # legal_actions(...) should already filter these out, but this prevents double-counting
    # if claim_route(...) is called directly from somewhere else.
    if path.occupation:
        return False

    matching_cards = [card for card in player.cards if card.colour == colour]

    if len(matching_cards) < train_count:
        return False

    cards_to_remove = matching_cards[:train_count]
    for card in cards_to_remove:
        player.cards.remove(card)
    state.discard.extend(cards_to_remove)

    path.occupation = player.name
    player.trains -= train_count

    # Immediately award standard Ticket to Ride route points for this claim.
    # We reuse the scoring table already defined in evaluation.py.
    player.score += evaluation.points_for_path_length(train_count)
    # Endgame trigger: once any player hits <= 2 trains, every other player gets one final turn.
    # (Closest to standard Ticket to Ride, and avoids giving the trigger player an extra turn.)
    if (not state.endgame_triggered) and player.trains <= 2:
        state.endgame_triggered = True
        state.final_turns_remaining = max(0, len(state.players) - 1)

    return path

def draw_card(state):
    player = state.current_player
    # If the deck is empty, recycle the discard pile back into the deck.
    # This keeps the game going as long as any cards have been spent on claims.
    if (not state.deck.cards) and state.discard:
        state.deck.cards.extend(state.discard)
        state.deck.shuffle()
        state.discard.clear()

    if state.deck.cards:
        card = state.deck.cards.pop(0)  # removes top card from deck
        player.cards.append(card)
        return True

    return False  # No cards anywhere (deck and discard are both empty)

def apply_action(state, action):
    """Apply one action for the current player and advance the turn counter."""
    endgame_was_triggered = state.endgame_triggered
    if action.type == "q":
        state.terminal = True
        state.terminal_reason = "quit"
        return True
    if action.type == "d":
        ok = draw_card(state)
        if ok is False:
            state.terminal = True
            state.terminal_reason = "deck_empty"
    elif action.type == "c":
        claim_path(state, action.path)
    else:
        return False
    state.current_round += 1
    # If endgame was just triggered by *this* action, do not decrement yet.
    # Decrement only for the subsequent players' turns.
    if state.endgame_triggered and endgame_was_triggered:
        state.final_turns_remaining = max(0, state.final_turns_remaining - 1)
        if state.final_turns_remaining == 0:
            state.terminal = True
            state.terminal_reason = "endgame"
    return True

def legal_actions(state):
    possible_actions = []

    # Draw is legal if there is a card available in the deck, or if the discard pile
    # can be reshuffled back into the deck.
    can_draw = (state.deck.get_card_count() > 0) or (len(state.discard) > 0)
    if can_draw:
        possible_actions.append(Action("d"))

    # Get all possible paths to place
    player = state.current_player
    can_claim_any = False
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
            can_claim_any = True

    # Allow manual early-ending only for a human player.
    # If the deck (and discard) are empty, force the player to claim if possible.
    if state.current_player.type == "human" and (can_draw or (not can_claim_any)):
        possible_actions.append(Action("q"))
    
    return possible_actions

def human_decide_action(state):

    all_possible_actions = legal_actions(state)
    claimable = [a for a in all_possible_actions if a.type == "c" and a.path is not None]

    while True:
        choice = input("Choose action: (d)raw, (c)laim, or (q)uit: ").strip().lower()

        if choice == "d":
            if any(a.type == "d" for a in all_possible_actions):
                return Action("d")
            print("You cannot draw (deck is empty).")
            continue

        if choice == "q":
            if any(a.type == "q" for a in all_possible_actions):
                return Action("q")
            print("Quit is not available.")
            continue

        if choice == "c":
            if not claimable:
                print("You cannot claim any route right now (need enough cards and trains).")
                continue

            print("Claimable paths:")
            for a in claimable:
                p = a.path
                start = p.get_start_node().name
                end = p.get_end_node().name
                print(f"- {p.path_id}: {start} <-> {end} | len {p.distance} | {p.colour}")

            selected_path_id = input("Enter path id to claim (e.g. R015): ").strip()
            selected_path = game.get_path_from_id(state.graph, selected_path_id.upper())
            if selected_path is None:
                print("Unknown path id. Try again.")
                continue

            # Validate against currently claimable set (avoids object-equality surprises)
            if any(a.path is selected_path for a in claimable):
                return Action("c", selected_path)

            print("That path is not currently claimable (occupied or insufficient cards/trains).")
            continue

        print("Invalid input. Please type d, c, or q.")

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
    return bool(state.terminal)


# Backwards-compatible aliases for older names used in notebooks/experiments.
claim = claim_path
draw = draw_card
action = Action