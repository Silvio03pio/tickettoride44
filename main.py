import time

import rules
import evaluation
from main2 import (
    create_new_game,
    hand_summary,
    execute_ai_turn,
    _format_hand,
    _print_turn_header,
    _print_final_scoring,
)


_COLOURS = ["red", "blue", "green", "yellow", "black", "white", "orange", "pink"]

DEFAULT_ROLLOUTS = 50


def route_text(player):
    if player.ticket is None:
        return "No ticket assigned"
    if isinstance(player.ticket, dict):
        return f'{player.ticket["start"]} -> {player.ticket["end"]} ({player.ticket["points"]} pts)'
    return str(player.ticket)


def print_scoreboard(current_game):
    human = current_game.players[0]
    ai = current_game.players[1]
    print()
    print("-" * 50)
    print(f"  Human  | Score: {human.score:>3}  Trains: {human.trains:>2}  Cards: {len(human.cards):>2}")
    print(f"  AI     | Score: {ai.score:>3}  Trains: {ai.trains:>2}  Cards: {len(ai.cards):>2}")
    print(f"  Deck   | {current_game.deck.get_card_count()} cards left")
    unclaimed = sum(1 for p in current_game.graph.get_paths() if p.get_occupation() is None)
    print(f"  Routes | {unclaimed} unclaimed")
    print("-" * 50)


def print_hand(player):
    counts = hand_summary(player)
    parts = [f"  {c}: {n}" for c, n in counts.items() if n > 0]
    if parts:
        print("Your hand:")
        for part in parts:
            print(part)
    else:
        print("Your hand: (empty)")


def print_claimed_routes(current_game, player):
    rows = []
    for p in current_game.graph.get_paths():
        if p.get_occupation() == player.name:
            rows.append(p)
    if not rows:
        print(f"  {player.name} has no claimed routes yet.")
        return
    print(f"  {player.name}'s claimed routes:")
    for p in rows:
        print(f"    {p.get_path_id()}: {p.get_start_node().name} <-> {p.get_end_node().name} "
              f"| {p.get_colour()} | len {p.get_distance()}")


def human_turn(current_game, rollouts):
    player = current_game.current_player
    _print_turn_header(current_game)
    print_hand(player)
    print(f"  Ticket: {route_text(player)}")
    print()

    actions = rules.legal_actions(current_game)
    claimable = [a for a in actions if a.type == "c" and a.path is not None]

    while True:
        choice = input("Choose action: (d)raw, (c)laim, (q)uit, (h)and, (s)core, (r)outes: ").strip().lower()

        if choice == "d":
            if any(a.type == "d" for a in actions):
                ok = rules.apply_action(current_game, rules.Action("d"))
                if ok is False:
                    print("Draw failed (deck empty).")
                    continue
                print("You drew 1 card.")
                return
            print("Cannot draw (deck is empty).")
            continue

        if choice == "q":
            if any(a.type == "q" for a in actions):
                rules.apply_action(current_game, rules.Action("q"))
                return
            print("Quit is not available right now.")
            continue

        if choice == "c":
            if not claimable:
                print("No claimable routes (need enough matching cards and trains).")
                continue

            print("\nClaimable routes:")
            for a in claimable:
                p = a.path
                start = p.get_start_node().name
                end = p.get_end_node().name
                print(f"  {p.path_id}: {start} <-> {end} | {p.colour} | len {p.distance}")

            path_id = input("Enter path id to claim (e.g. R015): ").strip().upper()
            import game
            selected_path = game.get_path_from_id(current_game.graph, path_id)
            if selected_path is None:
                print("Unknown path id.")
                continue
            if not any(a.path is selected_path for a in claimable):
                print("That path is not claimable right now.")
                continue

            ok = rules.apply_action(current_game, rules.Action("c", selected_path))
            if ok is False:
                print("Claim failed.")
                continue
            print(f"Claimed {path_id} ({selected_path.get_start_node().name} <-> {selected_path.get_end_node().name})!")
            return

        if choice == "h":
            print_hand(player)
            continue

        if choice == "s":
            print_scoreboard(current_game)
            continue

        if choice == "r":
            print_claimed_routes(current_game, current_game.players[0])
            print_claimed_routes(current_game, current_game.players[1])
            continue

        print("Invalid input. Type d, c, q, h, s, or r.")


def ai_turn(current_game, rollouts):
    _print_turn_header(current_game)
    messages = execute_ai_turn(current_game, n_rollouts=rollouts)
    for msg in messages:
        print(f"  {msg}")


def main():
    print("=" * 60)
    print("  TICKET TO RIDE — Human vs AI  (Terminal Mode)")
    print("=" * 60)

    current_game = create_new_game()
    human = current_game.players[0]
    ai = current_game.players[1]

    print(f"\nHuman ticket: {route_text(human)}")
    print(f"AI ticket:    {route_text(ai)}")
    print_scoreboard(current_game)

    rollouts = DEFAULT_ROLLOUTS

    while not current_game.terminal:
        active = current_game.current_player

        if active.name == "Human":
            human_turn(current_game, rollouts)
        else:
            ai_turn(current_game, rollouts)

        print_scoreboard(current_game)

        if getattr(current_game, "terminal_reason", None):
            print(f"\n*** Game ended: {current_game.terminal_reason} ***")

    # Final scoring
    _print_final_scoring(current_game, ai_index=1)


if __name__ == "__main__":
    main()
