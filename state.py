"""
Game state for simplified Ticket to Ride (two-player, turn-based, stochastic, partially observable).

The state holds the full underlying game: board, players (including hidden hands and tickets),
deck, discard pile, and turn information. Use observable_state_for_ai() to get only what the AI
is allowed to see. The observable view does not expose the deck object or any hidden information.
"""

from game import COLOURS, NBR_OF_CARDS_PER_COLOUR


class state:
    def __init__(self, graph, players, deck, longest_route_points=10):
        self.graph = graph
        self.players = players
        self.deck = deck
        self.longest_route_points = longest_route_points
        self.current_round = 0
        self.discard = []  # cards spent when claiming routes (visible to all; order irrelevant)
        self.endgame_triggered = False
        self.final_turns_remaining = 0

    @property
    def current_player(self):
        return self.players[self.current_round % len(self.players)]

    def current_player_index(self):
        return self.current_round % len(self.players)

    def observable_state_for_ai(self, ai_player_index=0):
        """
        Returns a view of the state with only what the AI is allowed to observe.
        Does not expose: deck object (hidden order), opponent hand, opponent destination ticket.
        """
        return _ObservableForAI(self, ai_player_index)


def _count_cards_by_colour(card_list):
    """Count cards per colour. Handles card objects with .colour or .get_colour()."""
    counts = {c: 0 for c in COLOURS}
    for card in card_list:
        colour = card.colour if hasattr(card, "colour") else card.get_colour()
        if colour in counts:
            counts[colour] += 1
    return counts


class _ObservableForAI:
    """
    AI-observable view only. No reference to the deck object; no opponent hand or ticket.
    """

    def __init__(self, full_state, ai_player_index=0):
        self.graph = full_state.graph
        self.current_round = full_state.current_round
        self.current_player_index = full_state.current_round % len(full_state.players)

        # AI's own full info (hand, ticket, score, trains)
        self.ai_player = full_state.players[ai_player_index]

        # Opponent: public info only (name, score, trains, hand size)
        opp_i = 1 - ai_player_index
        opp = full_state.players[opp_i]
        self.opponent_name = opp.name
        self.opponent_score = opp.score
        self.opponent_trains = opp.trains
        self.opponent_hand_size = len(opp.cards)
        # Opponent's cards and route are not exposed.

        # Discard: counts by colour (cards spent on claims)
        self.discard_counts = _count_cards_by_colour(full_state.discard)

        # Full deck composition (constant: 12 per colour in standard game)
        self.full_deck_counts = {c: NBR_OF_CARDS_PER_COLOUR for c in COLOURS}

        # Unknown pool: cards that must be either in the deck or in the opponent's hand.
        # Derived as: full_deck - AI hand - discard. Does NOT reveal deck-only distribution.
        ai_hand_counts = _count_cards_by_colour(full_state.players[ai_player_index].cards)
        self.unknown_counts_by_colour = {
            c: max(0, self.full_deck_counts[c] - ai_hand_counts[c] - self.discard_counts[c])
            for c in COLOURS
        }
        self.unknown_total = sum(self.unknown_counts_by_colour.values())
