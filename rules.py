
from dataclasses import dataclass
import copy
import random
import game
from game import path as Path
import evaluation

# ── Programmer-controlled knob ────────────────────────────────────────────────
# Maximum search depth for Alpha-Beta Pruning. At depth 0 (leaf not yet terminal)
# the heuristic E_s is used instead of a full rollout.
AB_DEPTH: int = 1
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Action:
    """
    Lightweight action representation.
    type: \"d\" (draw), \"c\" (claim), or \"q\" (quit/end early).
    """
    type: str
    path: Path = None   # None if draw; the path to claim if type "c"
    colour: str = None  # explicit colour choice when claiming a grey path

def claim_path(state, path, chosen_colour=None):
    player = state.current_player
    train_count = path.distance

    # Always look up the path inside THIS state's graph so that deep-copied simulation
    # states never accidentally mutate path objects that belong to the original state.
    real_path = None
    for p in state.graph.paths:
        if p.get_path_id() == path.get_path_id():
            real_path = p
            break
    if real_path is None:
        return False

    # Safety guard: do not allow (or score) claiming an already-occupied path.
    if real_path.occupation:
        return False

    colour = real_path.colour

    # Grey paths accept any single colour.
    # Use the explicitly chosen colour if provided; otherwise auto-pick the colour
    # the player has the most of (consistent with what the UI displays).
    if colour == "gray":
        if chosen_colour is not None:
            # Validate the caller's choice
            if sum(1 for card in player.cards if card.colour == chosen_colour) >= train_count:
                colour = chosen_colour
            else:
                return False
        else:
            best_colour, best_count = None, 0
            for c in game.COLOURS:
                cnt = sum(1 for card in player.cards if card.colour == c)
                if cnt >= train_count and cnt > best_count:
                    best_count, best_colour = cnt, c
            if best_colour is None:
                return False
            colour = best_colour

    matching_cards = [card for card in player.cards if card.colour == colour]

    if len(matching_cards) < train_count:
        return False

    cards_to_remove = matching_cards[:train_count]
    for card in cards_to_remove:
        player.cards.remove(card)
    state.discard.extend(cards_to_remove)

    real_path.occupation = player.name
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

def _draw_one_card(state):
    """Draw a single card for the current player. Returns True if a card was drawn."""
    player = state.current_player
    # Recycle discard pile into deck when deck runs out
    if (not state.deck.cards) and state.discard:
        state.deck.cards.extend(state.discard)
        state.deck.shuffle()
        state.discard.clear()
    if state.deck.cards:
        card = state.deck.cards.pop(0)
        player.cards.append(card)
        return True
    return False


def draw_card(state):
    """Draw 1 card for the current player.
    Returns True if a card was drawn, False if deck and discard are both empty."""
    return _draw_one_card(state)

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
        chosen_colour = getattr(action, "colour", None)
        result = claim_path(state, action.path, chosen_colour=chosen_colour)
        if result is False:
            return False  # claim failed — do NOT advance turn
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

        if path.occupation:
            continue  # occupied: exclude from possible
        if player.trains < train_count:
            continue  # not enough trains left

        # Grey paths accept any single colour — check if the player has enough of any colour.
        if colour == "gray":
            has_enough = any(
                sum(1 for c in player.cards if c.colour == col) >= train_count
                for col in game.COLOURS
            )
            if not has_enough:
                continue
        else:
            matching_cards = [card for card in player.cards if card.colour == colour]
            if len(matching_cards) < train_count:
                continue  # Not enough cards: exclude from possible

        claim_path_action = Action("c", path)
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

def monte_carlo_decide_action(state):
    """
    Use Monte Carlo rollouts to pick the best legal action for the current player.

    The number of rollouts per action is controlled by search.N_SIMULATIONS.
    Returns an Action object.
    """
    import search  # imported here to avoid circular imports at module load time
    best_action, _, wins, n, action_win_stats = search.choose_best_action_monte_carlo(
        state, n_simulations=search.N_SIMULATIONS
    )
    if action_win_stats:
        print("  MCTS results:")
        for a, w, sims, avg in action_win_stats:
            label = a.type
            if a.type == "c" and a.path is not None:
                label = f"claim {a.path.path_id}"
            marker = " <-- chosen" if a is best_action else ""
            print(f"    {label}: visits={sims}  avg_utility={avg:.2f}{marker}")
    # Fallback: if search returns nothing (e.g. no actions), draw a card.
    return best_action if best_action is not None else Action("d")

def _opponent_legal_actions(state):
    """
    Legal actions for the opponent assuming they have all possible cards.
    Only train count and path occupation are checked — card constraints are ignored.
    This implements imperfect information: the AI does not see the opponent's hand
    and instead assumes the opponent can make the best move with any cards available.
    """
    possible_actions = []
    player = state.current_player

    can_draw = (state.deck.get_card_count() > 0) or (len(state.discard) > 0)
    if can_draw:
        possible_actions.append(Action("d"))

    for path in state.graph.paths:
        if path.occupation:
            continue
        if player.trains < path.distance:
            continue
        # No card check — assume opponent has whatever cards they need.
        possible_actions.append(Action("c", path))

    return possible_actions


def _opponent_claim_path(state, path, chosen_colour=None):
    """
    Claim a path for the opponent without requiring cards in hand.
    The opponent is assumed to have all possible cards, so we skip the
    card-matching check and just deduct trains and mark occupation.
    """
    player = state.current_player
    train_count = path.distance

    real_path = None
    for p in state.graph.paths:
        if p.get_path_id() == path.get_path_id():
            real_path = p
            break
    if real_path is None:
        return False
    if real_path.occupation:
        return False

    real_path.occupation = player.name
    player.trains -= train_count
    player.score += evaluation.points_for_path_length(train_count)

    if (not state.endgame_triggered) and player.trains <= 2:
        state.endgame_triggered = True
        state.final_turns_remaining = max(0, len(state.players) - 1)

    return path


def _opponent_apply_action(state, action):
    """Apply an action for the opponent (no card check on claims)."""
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
        result = _opponent_claim_path(state, action.path)
        if result is False:
            return False
    else:
        return False
    state.current_round += 1
    if state.endgame_triggered and endgame_was_triggered:
        state.final_turns_remaining = max(0, state.final_turns_remaining - 1)
        if state.final_turns_remaining == 0:
            state.terminal = True
            state.terminal_reason = "endgame"
    return True


def _ab_search(sim_state, depth, alpha, beta, maximizing, our_name, opp_name):
    """
    Recursive Alpha-Beta search with imperfect information.

    our_name  : name of the player we are maximising for.
    opp_name  : name of the opponent.
    maximizing: True when it is our_name's turn in this node.

    The opponent's hand is hidden. On opponent turns, we assume they can
    claim any route they have enough trains for (regardless of cards held).

    Returns a scalar value (higher = better for our_name).
    """
    # Leaf cases ──────────────────────────────────────────────────────────────
    if is_terminal(sim_state):
        our  = next(p for p in sim_state.players if p.name == our_name)
        opp  = next(p for p in sim_state.players if p.name == opp_name)
        return evaluation.utility(sim_state, our, opp)

    if depth == 0:
        our  = next(p for p in sim_state.players if p.name == our_name)
        return evaluation.E_s(sim_state, our)

    # Generate children ───────────────────────────────────────────────────────
    if maximizing:
        actions = [a for a in legal_actions(sim_state) if a.type != "q"]
    else:
        actions = [a for a in _opponent_legal_actions(sim_state) if a.type != "q"]

    if not actions:
        # No moves left — treat as terminal.
        our  = next(p for p in sim_state.players if p.name == our_name)
        opp  = next(p for p in sim_state.players if p.name == opp_name)
        return evaluation.utility(sim_state, our, opp)

    if maximizing:
        value = float("-inf")
        for action in actions:
            child = copy.deepcopy(sim_state)
            apply_action(child, action)
            child_max = (child.current_player.name == our_name)
            v = _ab_search(child, depth - 1, alpha, beta, child_max, our_name, opp_name)
            value = max(value, v)
            alpha = max(alpha, v)
            if beta <= alpha:
                break  # beta cut-off
        return value
    else:
        value = float("inf")
        for action in actions:
            child = copy.deepcopy(sim_state)
            _opponent_apply_action(child, action)
            child_max = (child.current_player.name == our_name)
            v = _ab_search(child, depth - 1, alpha, beta, child_max, our_name, opp_name)
            value = min(value, v)
            beta = min(beta, v)
            if beta <= alpha:
                break  # alpha cut-off
        return value


def alpha_beta_pruning_decide_action(state):
    """
    Choose the best legal action for the current player using Alpha-Beta Pruning.

    Search depth is controlled by AB_DEPTH (module-level constant).
    Terminal nodes are scored with evaluation.utility; depth-limit nodes with E_s.
    Returns an Action object.
    """
    our_name = state.current_player.name
    opp_name = next(p.name for p in state.players if p.name != our_name)

    actions = [a for a in legal_actions(state) if a.type != "q"]
    if not actions:
        return Action("d")

    best_action = None
    best_value  = float("-inf")
    alpha       = float("-inf")
    beta        = float("inf")

    for action in actions:
        child = copy.deepcopy(state)
        apply_action(child, action)
        child_max = (child.current_player.name == our_name)
        v = _ab_search(child, AB_DEPTH - 1, alpha, beta, child_max, our_name, opp_name)
        if v > best_value:
            best_value  = v
            best_action = action
        alpha = max(alpha, v)

    print(f"  Alpha-Beta: evaluation value of chosen action = {best_value}")
    return best_action if best_action is not None else Action("d")


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

    if player.type == "random":
        actions = legal_actions(state)
        return random.choice(actions) if actions else Action("d")
    
    if player.type == "monte_carlo":
        action = monte_carlo_decide_action(state)
        print("Action chosen by MCTS: ", action)
        return action
    
    if player.type == "alpha_beta_pruning":
        action = alpha_beta_pruning_decide_action(state)
        print("Action chosen by Alpha Beta Pruning: ", action)
        return action

    # Fallback to interactive
    return human_decide_action(state)


def is_terminal(state):
    """Terminal condition for the simplified endgame scaffolding."""
    return bool(state.terminal)


# Backwards-compatible aliases for older names used in notebooks/experiments.
claim = claim_path
draw = draw_card
action = Action