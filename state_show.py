# This file contains helper functions to display the current game state
# in a readable way for debugging and testing purposes.
# It does not modify the state, it only formats and prints it.

import state


def player_claimed_paths(game, player):
    """
    Returns a list of all paths claimed by the given player.
    """
    claimed = []

    for p in game.graph.get_paths():
        if p.get_occupation() == player.name:
            claimed.append(p)

    return claimed


def unclaimed_paths(game):
    """
    Returns a list of all unclaimed paths on the board.
    """
    free_paths = []

    for p in game.graph.get_paths():
        if p.get_occupation() is None:
            free_paths.append(p)

    return free_paths


def hand_summary(player):
    """
    Returns a dictionary with card counts by colour for the given player.
    """
    summary = {}

    for colour in state.COLOURS:
        summary[colour] = 0

    for c in player.cards:
        if hasattr(c, "get_colour"):
            colour = c.get_colour()
        else:
            colour = c.colour

        if colour not in summary:
            summary[colour] = 0

        summary[colour] += 1

    return summary


def deck_summary(deck):
    """
    Returns a dictionary with remaining card counts by colour in the deck.
    """
    summary = {}

    for colour in state.COLOURS:
        summary[colour] = deck.get_colour_count(colour)

    summary["total"] = deck.get_card_count()
    return summary


def route_summary(player):
    """
    Returns a readable ticket summary for a player.
    """
    if player.ticket is None:
        return "No destination ticket assigned"

    if isinstance(player.ticket, dict):
        return f'{player.ticket["start"]} -> {player.ticket["end"]} ({player.ticket["points"]} points)'

    if hasattr(player.ticket, "destinations") and hasattr(player.ticket, "points"):
        return f'{player.ticket.destinations} ({player.ticket.points} points)'

    return str(player.ticket)


def print_player_state(game, player):
    """
    Prints a compact breakdown of one player's current state.
    """
    claimed = player_claimed_paths(game, player)

    print(f"\n=== PLAYER: {player.name} ===")
    print(f"Score: {player.score}")
    print(f"Trains left: {player.trains}")
    print(f"Ticket: {route_summary(player)}")
    print(f"Cards on hand: {hand_summary(player)}")
    print(f"Claimed paths: {len(claimed)}")

    for p in claimed:
        print(f"  - {p.get_start_node().name} <-> {p.get_end_node().name} | "
              f"length={p.get_distance()} | colour={p.get_colour()} | id={p.get_path_id()}")


def print_board_state(game, show_unclaimed=False, max_unclaimed=15):
    """
    Prints a compact breakdown of the board state.

    Args:
        show_unclaimed: if True, also prints unclaimed paths
        max_unclaimed: maximum number of unclaimed paths to print
    """
    free_paths = unclaimed_paths(game)

    print("\n=== BOARD STATE ===")
    print(f"Total nodes: {len(game.graph.get_nodes())}")
    print(f"Total paths: {len(game.graph.get_paths())}")
    print(f"Claimed paths: {len(game.graph.get_paths()) - len(free_paths)}")
    print(f"Unclaimed paths: {len(free_paths)}")

    if show_unclaimed:
        print(f"\nFirst {min(max_unclaimed, len(free_paths))} unclaimed paths:")
        for p in free_paths[:max_unclaimed]:
            print(f"  - {p.get_start_node().name} <-> {p.get_end_node().name} | "
                  f"length={p.get_distance()} | colour={p.get_colour()} | id={p.get_path_id()}")


def print_deck_state(game):
    """
    Prints the remaining deck composition.
    """
    summary = deck_summary(game.deck)

    print("\n=== DECK STATE ===")
    print(f"Cards remaining: {summary['total']}")
    for colour in state.COLOURS:
        print(f"  {colour}: {summary[colour]}")


def print_turn_state(game):
    """
    Prints turn and round information.
    """
    current_player_name = game.players[game.current_player].name

    print("\n=== TURN STATE ===")
    print(f"Current round: {game.current_round}")
    print(f"Current player index: {game.current_player}")
    print(f"Current player: {current_player_name}")


def print_game_state(game, show_unclaimed=False, max_unclaimed=15):
    """
    Prints a full readable breakdown of the entire game state.
    """
    print("\n" + "=" * 60)
    print("FULL GAME STATE")
    print("=" * 60)

    print_turn_state(game)
    print_deck_state(game)
    print_board_state(game, show_unclaimed=show_unclaimed, max_unclaimed=max_unclaimed)

    for player in game.players:
        print_player_state(game, player)

    print("\n" + "=" * 60)