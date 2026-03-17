
# 1. Implement place_trains(player, path, deck) or better claim_route(state, player_idx, path_id)
# 2. Implement draw_card(state, player_idx)
# 3. Implement legal_actions(state, player_idx)
# 4. Deprecate or thin out: player.place_trains, player.draw_card, player.claim_path so they become light wrappers (or remove once all call sites are updated)

from dataclasses import dataclass
import state
import game


@dataclass
class action():
    type: str  # "d" = draw, "c" = claim
    path: path = None  # None if draw; the path to claim if type "c"

def claim(state, path):
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
    if player.trains <= 2: player.end_game = True

    return path

def draw(state):
    player = state.current_player
    if state.deck.cards: 
        card = state.deck.cards.pop(0) # remocves top card from deck
        player.cards.append(card)
    else: 
        return False # No cards in deck

def apply_action(state, action):
    if action.type == "d":
        draw(state)
    elif action.type == "c":
        claim(state, action.path)
    else:
        print("ERRRRR")
        return False
    state.current_round += 1

def get_all_possible_actions(state):
    possible_actions = []

    # Always possible to draw card
    draw_card = action("d")
    possible_actions.append(draw_card)

    # Get all possible paths to place
    for path in state.graph.paths: # loop through all paths

        colour = path.colour
        train_count = path.distance 
        matching_cards = [card for card in state.current_player.cards if card.colour == colour]
        
        if path.occupation: 
            continue # occupied: exclude from possible
        if len(matching_cards) < train_count: 
            continue # Not enough cards: exclude from possible
        else:
            claim_path_action = action("c", path) # We good: add to 
            possible_actions.append(claim_path_action)
    
    return possible_actions

def human_decide_action(state):

    all_possible_actions = get_all_possible_actions(state)
    selected_path = None

    while True:
        d_or_c = input("Choose action: (d)raw or (c)laim: ").strip().lower()
        if d_or_c == "c":
            selected_path_id = input("Enter path id to claim: ").strip()
            selected_path = game.get_path_from_id(state.graph, selected_path_id)
        chosen_action = action(d_or_c, selected_path)
        if chosen_action in all_possible_actions:
            print(f"action {chosen_action} valid")
            return chosen_action
        else:
            print("Invalid action. Type 'd' to draw or 'c' to claim.")
            print("Make sure the path you claim is available")

# def monte_carlo_decide_action(state):

def decide_action(state):

    player = state.current_player

    if player.type == "human":
        return human_decide_action(state)
    """
    if player.type == "monte_carlo":
        return monte_carlo_decide_action(state)
    """