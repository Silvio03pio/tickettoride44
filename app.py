import os
import tempfile

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import game
import state
import evaluation
import models_P
from graph_ui import create_map


st.set_page_config(page_title="Ticket to Ride AI", layout="wide")


def create_new_game():
    """
    Creates a fresh game state.
    """
    here = os.path.dirname(__file__)
    map_path = os.path.join(here, "ttr_europe_map_data.csv")

    # Graph / map
    game_graph = game.graph()
    game_graph.import_graph(map_path)

    # Players
    player_human = game.player("Human", "human")
    player_ai = game.player("AI", "human")
    players = [player_human, player_ai]

    # Deck
    deck_of_trains = game.deck()
    deck_of_trains.shuffle()

    # Global state
    current_game = state.state(game_graph, players, deck_of_trains)

    # Give each player one destination ticket
    for p in current_game.players:
        p.give_ticket()

    return current_game


def ensure_session_state():
    if "current_game" not in st.session_state:
        st.session_state.current_game = create_new_game()
    if "selected_path_id" not in st.session_state:
        st.session_state.selected_path_id = None


def get_active_player(current_game):
    return current_game.current_player


def get_other_player(current_game):
    for p in current_game.players:
        if p != current_game.current_player:
            return p
    return None


def route_text(player):
    if player.ticket is None:
        return "No ticket assigned"
    if isinstance(player.ticket, dict):
        return f'{player.ticket["start"]} -> {player.ticket["end"]} ({player.ticket["points"]} pts)'
    return str(player.ticket)


def hand_summary(player):
    colours = ["red", "blue", "green", "yellow", "black", "white", "orange", "pink"]
    summary = {c: 0 for c in colours}

    for c in player.cards:
        colour = c.get_colour() if hasattr(c, "get_colour") else c.colour
        summary[colour] = summary.get(colour, 0) + 1

    return summary


def claimed_paths_for_player(current_game, player):
    rows = []
    for p in current_game.graph.get_paths():
        if p.get_occupation() == player.name:
            rows.append(
                {
                    "id": p.get_path_id(),
                    "start": p.get_start_node().name,
                    "end": p.get_end_node().name,
                    "colour": p.get_colour(),
                    "length": p.get_distance(),
                }
            )
    return rows


def unclaimed_paths(current_game):
    rows = []
    for p in current_game.graph.get_paths():
        if p.get_occupation() is None:
            rows.append(
                {
                    "id": p.get_path_id(),
                    "start": p.get_start_node().name,
                    "end": p.get_end_node().name,
                    "colour": p.get_colour(),
                    "length": p.get_distance(),
                    "obj": p,
                    "label": f'{p.get_path_id()} | {p.get_start_node().name} <-> {p.get_end_node().name} | {p.get_colour()} | {p.get_distance()}',
                }
            )
    return rows


def count_matching_cards(player, colour):
    count = 0
    for c in player.cards:
        card_colour = c.get_colour() if hasattr(c, "get_colour") else c.colour
        if card_colour == colour:
            count += 1
    return count


def selected_path_data(current_game):
    path_id = st.session_state.selected_path_id
    if path_id is None:
        return None

    for item in unclaimed_paths(current_game):
        if str(item["id"]) == str(path_id):
            return item
    return None


def can_claim_path(player, path):
    needed = path.get_distance()
    colour = path.get_colour()
    available = count_matching_cards(player, colour)
    return available >= needed, available, needed, colour


def advance_turn(current_game):
    current_index = current_game.players.index(current_game.current_player)
    next_index = (current_index + 1) % len(current_game.players)
    current_game.current_player = current_game.players[next_index]

    if next_index == 0:
        current_game.current_round += 1


def deck_dataframe(deck):
    colours = ["red", "blue", "green", "yellow", "black", "white", "orange", "pink"]
    rows = [{"colour": c, "count": deck.get_colour_count(c)} for c in colours]
    return pd.DataFrame(rows)


def render_map(current_game):
    net = create_map(current_game.graph, st.session_state.selected_path_id)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        temp_path = tmp.name

    net.save_graph(temp_path)

    with open(temp_path, "r", encoding="utf-8") as f:
        html = f.read()

    components.html(html, height=680, scrolling=False)
    os.unlink(temp_path)


def draw_one_card(player, deck):
    """
    Draw one card from the deck and add it to the player's hand.
    Returns the drawn card, or None if the deck is empty.
    """
    if deck.cards:
        drawn_card = deck.cards.pop(0)
        player.add_card_to_hand(drawn_card)
        return drawn_card
    return None

ensure_session_state()
current_game = st.session_state.current_game
active_player = get_active_player(current_game)
other_player = get_other_player(current_game)

human = current_game.players[0]
ai = current_game.players[1]


st.title("Ticket to Ride AI")
st.caption("Turn-based UI v1 with interactive map, card draw, and path claiming")

# Sidebar
st.sidebar.header("Controls")

if st.sidebar.button("New Game"):
    st.session_state.current_game = create_new_game()
    st.session_state.selected_path_id = None
    st.rerun()

show_debug = st.sidebar.checkbox("Show debug panels", value=True)

# Header metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Round", current_game.current_round)
m2.metric("Current Player", active_player.name)
m3.metric("Deck Cards Left", current_game.deck.get_card_count())
m4.metric("Total Paths", len(current_game.graph.get_paths()))

# Main layout
left, center, right = st.columns([1.1, 1.6, 1.1])

with left:
    st.subheader("Human Player")
    st.metric("Score", human.score)
    st.metric("Trains Left", human.trains)
    st.write("Ticket:", route_text(human))
    st.write("Cards in hand:", len(human.cards))
    st.write("Hand summary:", hand_summary(human))

    human_claimed = claimed_paths_for_player(current_game, human)
    st.write(f"Claimed paths: {len(human_claimed)}")
    if human_claimed:
        st.dataframe(pd.DataFrame(human_claimed), use_container_width=True, hide_index=True)

with center:
    st.subheader("Map")
    render_map(current_game)

    free_paths = unclaimed_paths(current_game)
    if free_paths:
        labels = [item["label"] for item in free_paths]
        current_label = None

        if st.session_state.selected_path_id is not None:
            for item in free_paths:
                if str(item["id"]) == str(st.session_state.selected_path_id):
                    current_label = item["label"]
                    break

        selected_label = st.selectbox(
            "Select an unclaimed path",
            options=labels,
            index=labels.index(current_label) if current_label in labels else 0,
        )

        chosen = next(item for item in free_paths if item["label"] == selected_label)
        st.session_state.selected_path_id = chosen["id"]
    else:
        st.info("No unclaimed paths left.")

with right:
    st.subheader("AI Player")
    st.metric("Score", ai.score)
    st.metric("Trains Left", ai.trains)
    st.write("Ticket:", route_text(ai))
    st.write("Cards in hand:", len(ai.cards))
    st.write("Hand summary:", hand_summary(ai))

    ai_claimed = claimed_paths_for_player(current_game, ai)
    st.write(f"Claimed paths: {len(ai_claimed)}")
    if ai_claimed:
        st.dataframe(pd.DataFrame(ai_claimed), use_container_width=True, hide_index=True)

# Selected path panel
st.divider()
st.subheader("Selected Path")

selected = selected_path_data(current_game)
if selected is not None:
    selected_path = selected["obj"]
    claimable, available, needed, colour = can_claim_path(active_player, selected_path)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.write(f"**Start:** {selected['start']}")
    c2.write(f"**End:** {selected['end']}")
    c3.write(f"**Colour:** {selected['colour']}")
    c4.write(f"**Length:** {selected['length']}")
    c5.write(f"**Cards in hand:** {available} / {needed}")

    if claimable:
        st.success(f"{active_player.name} can claim this path now.")
    else:
        st.warning(f"{active_player.name} cannot claim this path yet. Need {needed} {colour} cards, currently has {available}.")
else:
    st.info("Select a path to inspect its details.")

# Actions
st.divider()
st.subheader("Actions")

a1, a2, a3 = st.columns(3)

with a1:
    st.write(f"Active player: **{active_player.name}**")
    if st.button("Draw 1 card"):
        drawn_card = draw_one_card(active_player, current_game.deck)
        if drawn_card is not None:
            advance_turn(current_game)
        st.rerun()

with a2:
    if selected is not None:
        claimable, _, _, _ = can_claim_path(active_player, selected["obj"])
        claim_disabled = not claimable
        if st.button("Claim selected path", disabled=claim_disabled):
            result = active_player.place_trains(selected["obj"])
            if result is not False:
                advance_turn(current_game)
                st.session_state.selected_path_id = None
                st.rerun()
    else:
        st.button("Claim selected path", disabled=True)

with a3:
    if st.button("End turn"):
        advance_turn(current_game)
        st.rerun()

# Evaluation panel
st.divider()
st.subheader("Evaluation")

try:
    breakdown = evaluation.utility_breakdown(current_game, ai, human)

    e1, e2, e3 = st.columns(3)

    with e1:
        st.write("**AI**")
        st.write("Total:", breakdown["AI"]["total"])
        st.write("Path points:", breakdown["AI"]["path_points"])
        st.write("Ticket points:", breakdown["AI"]["ticket_points"])
        st.write("Longest bonus:", breakdown["AI"]["longest_bonus"])

    with e2:
        st.write("**Human**")
        st.write("Total:", breakdown["Opponent"]["total"])
        st.write("Path points:", breakdown["Opponent"]["path_points"])
        st.write("Ticket points:", breakdown["Opponent"]["ticket_points"])
        st.write("Longest bonus:", breakdown["Opponent"]["longest_bonus"])

    with e3:
        st.metric("Utility U(s)", breakdown["utility"])

except Exception as exc:
    st.warning(f"Utility breakdown not available yet: {exc}")

# AI / probabilities panel
st.divider()
st.subheader("AI / Probability Panel")

p1, p2, p3 = st.columns(3)

with p1:
    try:
        st.write("P_L(AI):", models_P.P_L(current_game, ai))
    except Exception as exc:
        st.write("P_L unavailable:", exc)

with p2:
    try:
        st.write("P_colour(blue):", models_P.P_colour(current_game.deck, "blue"))
    except Exception as exc:
        st.write("P_colour unavailable:", exc)

with p3:
    st.info("Monte Carlo panel placeholder")

# Debug
if show_debug:
    st.divider()
    st.subheader("Debug")

    with st.expander("Deck composition"):
        st.dataframe(deck_dataframe(current_game.deck), use_container_width=True, hide_index=True)

    with st.expander("Unclaimed paths"):
        free_paths = unclaimed_paths(current_game)
        if free_paths:
            df = pd.DataFrame(
                [
                    {
                        "id": x["id"],
                        "start": x["start"],
                        "end": x["end"],
                        "colour": x["colour"],
                        "length": x["length"],
                    }
                    for x in free_paths
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.write("No unclaimed paths.")