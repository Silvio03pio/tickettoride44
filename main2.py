import os
import csv
import random
import time
import sys

import game
import rules
import state
import evaluation
from streamlit.web import cli as stcli


def _here_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)


def _count_hand_by_colour(cards):
    counts = {c: 0 for c in game.COLOURS}
    for card in cards:
        colour = card.colour if hasattr(card, "colour") else card.get_colour()
        if colour in counts:
            counts[colour] += 1
    return counts


def hand_summary(player):
    counts = {c: 0 for c in game.COLOURS}
    for c in player.cards:
        colour = c.get_colour() if hasattr(c, "get_colour") else c.colour
        counts[colour] = counts.get(colour, 0) + 1
    return counts


def _format_hand(cards):
    counts = _count_hand_by_colour(cards)
    parts = [f"{c}:{n}" for c, n in counts.items() if n > 0]
    return "  ".join(parts) if parts else "(empty)"


def _load_tickets(csv_path):
    tickets = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "city_a" in row and "city_b" in row:
                tickets.append(
                    {
                        "start": row["city_a"],
                        "end": row["city_b"],
                        "points": int(row["points"]),
                    }
                )
            else:
                tickets.append(
                    {
                        "start": row["start"],
                        "end": row["end"],
                        "points": int(row["points"]),
                    }
                )
    return tickets


def create_new_game(
    player_specs=None,
    map_filename="ttr_europe_map_data.csv",
    tickets_filename="route_cards.csv",
):
    if player_specs is None:
        player_specs = [("Human", "human"), ("AI", "ai")]

    test_graph = game.graph()
    test_graph.import_graph(_here_path(map_filename))

    players = [game.player(name, ptype) for name, ptype in player_specs]

    for p in players:
        p.cards = []
        p.ticket = None
        p.score = 0
        p.trains = 44

    deck_of_trains = game.deck()
    deck_of_trains.shuffle()

    current_game = state.state(test_graph, players, deck_of_trains)

    tickets = _load_tickets(_here_path(tickets_filename))
    random.shuffle(tickets)

    for i, p in enumerate(current_game.players):
        if i < len(tickets):
            p.ticket = dict(tickets[i])

    return current_game


def execute_ai_turn(current_game, n_rollouts=1000):
    messages = []

    if current_game.terminal:
        return messages
    if current_game.current_player.name != "AI":
        return messages

    messages.append("AI is thinking…")

    action = None
    policy_used = None

    try:
        import search

        action, _values = search.choose_best_action_monte_carlo(
            current_game,
            n_simulations=int(n_rollouts),
        )
        if action is not None:
            policy_used = "Monte Carlo"
    except Exception as exc:
        messages.append(f"Monte Carlo unavailable, fallback to random policy. ({exc})")
        action = None

    if action is None:
        actions = [a for a in rules.legal_actions(current_game) if getattr(a, "type", None) != "q"]
        action = random.choice(actions) if actions else None
        if action is not None:
            policy_used = "random"

    if action is None:
        messages.append("AI has no legal actions.")
        return messages

    if action.type == "d":
        msg = "AI drew 1 card."
    elif action.type == "c" and action.path is not None:
        start = action.path.get_start_node().name
        end = action.path.get_end_node().name
        colour = action.path.get_colour()
        needed = int(action.path.get_distance())
        msg = f"AI claimed {action.path.get_path_id()} ({start} ↔ {end}) using {needed} {colour} card(s)."
    else:
        msg = f"AI played action: {getattr(action, 'type', '?')}"

    ok = rules.apply_action(current_game, action)
    if ok is False:
        messages.append("AI action failed (unexpected illegal move).")
        return messages

    if policy_used:
        messages.append(f"AI policy: {policy_used}.")
    messages.append(msg)
    return messages


def _print_turn_header(game_state):
    p = game_state.current_player
    print("\n" + "=" * 72)
    print(f"Turn {game_state.current_round} | Current player: {p.name} ({p.type})")
    print("-" * 72)
    print(f"Score: {p.score} | Trains left: {p.trains}")
    if p.ticket is not None:
        print(f"Ticket: {p.ticket['start']} -> {p.ticket['end']} ({p.ticket['points']} pts)")
    else:
        print("Ticket: (none)")
    print(f"Hand: {_format_hand(p.cards)}")
    print("=" * 72)


def _print_actions(game_state, actions):
    print("Available actions:")
    for a in actions:
        if a.type == "q":
            print("- q: Quit / end the game now")
        elif a.type == "d":
            print("- d: Draw 1 train card from the deck")
        elif a.type == "c" and a.path is not None:
            path = a.path
            start = path.get_start_node().name
            end = path.get_end_node().name
            print(f"- c: Claim path {path.path_id} | {start} <-> {end} | len {path.distance} | {path.colour}")


def _print_final_scoring(game_state, ai_index=0, player_times=None):
    ai = game_state.players[ai_index]
    opp = game_state.players[1 - ai_index]
    breakdown = evaluation.utility_breakdown(game_state, ai, opp, longest_bonus=game_state.longest_path_points)

    print("\n" + "#" * 72)
    print("FINAL SCORING")
    print(f"Terminal reason: {game_state.terminal_reason}")
    print("-" * 72)
    print(f"{ai.name} total: {breakdown['AI']['total']}")
    print(f"{opp.name} total: {breakdown['Opponent']['total']}")
    print(f"Utility U(s) = {breakdown['utility']}")
    if player_times:
        for name, total in player_times.items():
            print(f"Total decision time for {name}: {total:.2f}s")
    print("#" * 72 + "\n")




def main():
    app_path = os.path.join(os.path.dirname(__file__), "app3.py")
    sys.argv = ["streamlit", "run", app_path]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()