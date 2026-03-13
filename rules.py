
# 1. Implement place_trains(player, path, deck) or better claim_route(state, player_idx, path_id)
# 2. Implement draw_card(state, player_idx)
# 3. Implement legal_actions(state, player_idx)
# 4. Deprecate or thin out: player.place_trains, player.draw_card, player.claim_path so they become light wrappers (or remove once all call sites are updated)

from dataclasses import dataclass
from pyarrow import large_list_view
import state


@dataclass
class action():
    type: str # "d" or "c"
    path: path = None # None by default if d, claimed path if c

def claim(state, path):
    colour = path.colour
    train_count = path.distance

    matching_cards = [card for card in state.current_player.cards if card.colour == colour]

    if len(matching_cards) < train_count:
        print(f"not enough {colour} cards on hand")
        return False

    cards_to_remove = matching_cards[:train_count]
    for card in cards_to_remove:
        state.current_player.cards.remove(card)

    path.occupation = state.current_player.name
    state.current_player.trains -= train_count

    return path

def draw(state):
    if state.deck.cards: 
        card = state.deck.cards.pop(0) # remocves top card from deck
        state.current_player.cards.append(card)
    else: 
        return False # No cards in deck

def apply_action(action, state):
    state.current_player = state.players[state.current_round % len(state.players)]
    if action.type == "d":
        draw(state)
    elif action.type == "c":
        claim(state, action.path)
    else:
        print("ERRRRR")
        return False



