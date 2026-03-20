
import os
import csv
import random
import time

import game
import rules
import state
import evaluation

def _here_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)


def _count_hand_by_colour(cards):
    counts = {c: 0 for c in game.COLOURS}
    for card in cards:
        colour = card.colour if hasattr(card, "colour") else card.get_colour()
        if colour in counts:
            counts[colour] += 1
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
            tickets.append({"start": row["city_a"], "end": row["city_b"], "points": int(row["points"])})
    return tickets


def _deal_starting_hands(game_state, cards_each=4):
    for _ in range(cards_each):
        for p in game_state.players:
            if not game_state.deck.cards:
                game_state.terminal = True
                game_state.terminal_reason = "deck_empty"
                return
            p.cards.append(game_state.deck.cards.pop(0))


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
            print("- q: Quit / end the game now (final scoring immediately)")
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
    print(f"{ai.name} total: {breakdown['AI']['total']} (paths {breakdown['AI']['path_points']}, ticket {breakdown['AI']['ticket_points']}, longest {breakdown['AI']['longest_bonus']})")
    print(f"{opp.name} total: {breakdown['Opponent']['total']} (paths {breakdown['Opponent']['path_points']}, ticket {breakdown['Opponent']['ticket_points']}, longest {breakdown['Opponent']['longest_bonus']})")
    print("-" * 72)
    print(f"Utility U(s) = {breakdown['utility']}  (AI - Opponent)")
    if player_times:
        print("-" * 72)
        for name, total in player_times.items():
            print(f"Total decision time for {name}: {total:.2f}s")
    print("#" * 72 + "\n")


def main():

    random.seed()

    test_graph = game.graph()
    test_graph.import_graph(_here_path("ttr_europe_map_data.csv"))

    # Two-player simplified setup: one AI placeholder (random) and one human.
    player_monte = game.player("Monte Carlo", "monte_carlo")  # placeholder until MCTS
    player_ab = game.player("Alpha Beta", "alpha_beta_pruning") 
    player_human = game.player("Edda", "monte_carlo")
    # player_human2 = game.player("Human 2", "human")
    players = [player_monte, player_human] #, player_human1] # , player_human2]

    # Defensive reset: ensures a fresh start even if this file is run multiple times
    # in the same Python process / interactive session.
    for p in players:
        p.cards = []
        p.ticket = None
        p.score = 0
        p.trains = 44

    deck_of_trains = game.deck()
    deck_of_trains.shuffle()

    test_game = state.state(test_graph, players, deck_of_trains)

    # Destination tickets: 1 per player, secret (we only show current player's ticket in terminal).
    tickets = _load_tickets(_here_path("route_cards.csv"))
    random.shuffle(tickets)
    for i, p in enumerate(test_game.players):
        # Copy dict so it can't be shared/mutated across players/runs
        p.ticket = dict(tickets[i % len(tickets)])

    # Initial hands: empty (per simplified rules). Players must draw to get cards.


    player_times = {p.name: 0.0 for p in test_game.players}

    while not rules.is_terminal(test_game):
        _print_turn_header(test_game)
        actions = rules.legal_actions(test_game)
        _print_actions(test_game, actions)
        current_name = test_game.current_player.name
        t0 = time.time()
        chosen_action = rules.decide_action(test_game)
        elapsed = time.time() - t0
        player_times[current_name] += elapsed
        print(f"  [{current_name} decided in {elapsed:.2f}s]")
        rules.apply_action(test_game, chosen_action)

    _print_final_scoring(test_game, ai_index=0, player_times=player_times)


if __name__ == "__main__":
    main()
