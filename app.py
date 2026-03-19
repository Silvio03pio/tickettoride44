import os
import tempfile

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import game
import state
import evaluation
import models_P
import rules
import random
from graph_ui import create_map


st.set_page_config(page_title="Ticket to Ride AI", layout="wide")

_COLOURS = ["red", "blue", "green", "yellow", "black", "white", "orange", "pink"]


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
    # IMPORTANT: The AI player is identified by name == "AI".
    # The player type is used by rules.decide_action, but the UI controls actions directly.
    player_ai = game.player("AI", "ai")
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
    if "last_message" not in st.session_state:
        st.session_state.last_message = None


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
    summary = {c: 0 for c in _COLOURS}

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
                    "label": f'{p.get_path_id()} | {p.get_start_node().name} ↔ {p.get_end_node().name} | {p.get_colour()} | {p.get_distance()} trains',
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

    # Selected path can become claimed by another action; look up in the full graph.
    p = game.get_path_from_id(current_game.graph, str(path_id))
    if p is None:
        return None
    return {
        "id": p.get_path_id(),
        "start": p.get_start_node().name,
        "end": p.get_end_node().name,
        "colour": p.get_colour(),
        "length": p.get_distance(),
        "obj": p,
    }


def can_claim_path(player, path):
    needed = path.get_distance()
    colour = path.get_colour()
    available = count_matching_cards(player, colour)
    return available >= needed, available, needed, colour


def _set_message(text: str):
    st.session_state.last_message = text


def _append_message(text: str):
    """Append a short status line for turn-flow feedback."""
    if not text:
        return
    if st.session_state.last_message:
        st.session_state.last_message = f"{st.session_state.last_message}\n{text}"
    else:
        st.session_state.last_message = text


def deck_dataframe(deck):
    rows = [{"colour": c, "count": deck.get_colour_count(c)} for c in _COLOURS]
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

def _legal_action_types(current_game):
    """Convenience helper for UI enabling/disabling buttons."""
    return {a.type for a in rules.legal_actions(current_game)}


def _apply_action_and_rerun(current_game, action):
    """
    Apply a backend action and rerun the Streamlit app.

    IMPORTANT: We always go through rules.apply_action(...) so turn progression,
    endgame rules, discard pile, and scoring stay consistent.
    """
    ok = rules.apply_action(current_game, action)
    if ok is False:
        _set_message("That action could not be applied (illegal or failed).")
    st.rerun()


def _describe_path(path_obj):
    """Human-readable route description for UI messages."""
    try:
        a = path_obj.get_start_node().name
        b = path_obj.get_end_node().name
    except Exception:
        a, b = "?", "?"
    try:
        pid = path_obj.get_path_id()
    except Exception:
        pid = "?"
    return f"{pid} ({a} ↔ {b})"


def execute_ai_turn(current_game, n_rollouts: int):
    """
    Execute exactly one AI turn automatically.

    Preference:
      - Monte Carlo from search.py (if available and stable)
      - fallback: random legal action
    """
    if current_game.terminal:
        return
    if current_game.current_player.name != "AI":
        return

    _append_message("AI is thinking…")

    action = None
    policy_used = None
    # Try Monte Carlo first
    try:
        import search

        action, _values = search.choose_best_action_monte_carlo(current_game, n_simulations=int(n_rollouts))
        if action is not None:
            policy_used = "Monte Carlo"
    except Exception:
        action = None

    # Fallback policy: random legal action (excluding quit).
    if action is None:
        actions = [a for a in rules.legal_actions(current_game) if getattr(a, "type", None) != "q"]
        action = random.choice(actions) if actions else None
        if action is not None:
            policy_used = "random"

    if action is None:
        _append_message("AI has no legal actions.")
        return

    # Compose a clear message BEFORE applying, so we know what was intended/spent.
    if action.type == "d":
        msg = "AI drew 1 card."
    elif action.type == "c" and action.path is not None:
        colour = action.path.get_colour()
        needed = int(action.path.get_distance())
        msg = f"AI claimed {_describe_path(action.path)} using {needed} {colour} card(s)."
    else:
        msg = f"AI played action: {getattr(action, 'type', '?')}"

    ok = rules.apply_action(current_game, action)
    if ok is False:
        _append_message("AI action failed (unexpected illegal move).")
        return

    if policy_used:
        _append_message(f"AI policy: {policy_used}.")
    _append_message(msg)


def _apply_claim_and_rerun(current_game, active_player, path_obj):
    """
    Apply a claim action with a clear "cards spent" UI message.

    We compute the message from the state BEFORE applying the action, then rely on the
    backend to actually remove cards and put them into state.discard.
    """
    ok = rules.apply_action(current_game, rules.Action("c", path_obj))
    if ok is False:
        _set_message("Claim failed (not enough cards/trains, or route already claimed).")
        st.rerun()

    # If claim succeeded, the backend consumed exactly `needed` cards of that colour.
    colour = path_obj.get_colour()
    needed = int(path_obj.get_distance())
    _set_message(f"Claim successful: {needed} {colour} card(s) were used and discarded.")
    st.session_state.selected_path_id = None
    st.rerun()

ensure_session_state()
current_game = st.session_state.current_game
active_player = get_active_player(current_game)
other_player = get_other_player(current_game)

human = current_game.players[0]
ai = current_game.players[1]


# ---------- Global styling (dark, game-like) ----------
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.25rem; padding-bottom: 1.5rem; }
      div[data-testid="stMetricValue"] { font-size: 1.6rem; }
      div[data-testid="stMetricLabel"] { opacity: 0.85; }
      .ttr-badge {
        display: inline-block;
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.85rem;
        border: 1px solid rgba(148, 163, 184, 0.25);
        background: rgba(15, 23, 42, 0.55);
        color: #e5e7eb;
      }
      .ttr-badge-ai { border-color: rgba(239, 68, 68, 0.45); }
      .ttr-badge-human { border-color: rgba(34, 197, 94, 0.45); }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar
st.sidebar.header("Controls")

if st.sidebar.button("New Game"):
    st.session_state.current_game = create_new_game()
    st.session_state.selected_path_id = None
    st.session_state.last_message = None
    st.rerun()

show_debug = st.sidebar.checkbox("Show debug panels", value=True)
rollouts = st.sidebar.slider("AI rollouts per move", 10, 200, 50, 10)

st.sidebar.divider()
st.sidebar.caption("Tip: click a route in the dropdown to highlight it on the map.")

# ---------- Header ----------
header = st.container()
with header:
    c_title, c_status = st.columns([1.4, 1.0])
    with c_title:
        st.title("Ticket to Ride (Simplified) — Human vs AI")
        st.caption("Dark-theme demo UI with an interactive board map.")
    with c_status:
        turn_badge = (
            f'<span class="ttr-badge ttr-badge-ai">AI turn</span>'
            if active_player.name == "AI"
            else f'<span class="ttr-badge ttr-badge-human">Human turn</span>'
        )
        st.markdown(turn_badge, unsafe_allow_html=True)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Turn / ply", current_game.current_round)
    m2.metric("Active player", active_player.name)
    m3.metric("Deck cards left", current_game.deck.get_card_count())
    m4.metric("Unclaimed routes", sum(1 for p in current_game.graph.get_paths() if p.get_occupation() is None))
    m5.metric("Terminal", "Yes" if current_game.terminal else "No")

    if current_game.terminal_reason:
        st.info(f"Game ended: {current_game.terminal_reason}")
    if st.session_state.last_message:
        st.warning(st.session_state.last_message)

# Main layout
left, center, right = st.columns([1.05, 1.9, 1.05], gap="large")

with left:
    st.subheader("Human")
    st.metric("Score", human.score)
    st.metric("Trains Left", human.trains)
    st.write("Ticket:", route_text(human))
    st.write("Cards in hand:", len(human.cards))
    st.write("Hand summary:", hand_summary(human))

    with st.expander("Hand", expanded=True):
        st.write(f"Cards in hand: **{len(human.cards)}**")
        st.dataframe(
            pd.DataFrame([hand_summary(human)]).T.rename(columns={0: "count"}),
            use_container_width=True,
            height=285,
        )

    with st.expander("Claimed routes", expanded=False):
        rows = claimed_paths_for_player(current_game, human)
        st.write(f"Claimed: **{len(rows)}**")
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with center:
    st.subheader("Board")
    st.caption("Edge labels show required trains. Hover a route for full details.")

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
            "Highlight a route",
            options=labels,
            index=labels.index(current_label) if current_label in labels else 0,
        )
        chosen = next(item for item in free_paths if item["label"] == selected_label)
        st.session_state.selected_path_id = chosen["id"]
    else:
        st.info("No unclaimed routes left.")

    render_map(current_game)

with right:
    st.subheader("AI")
    st.metric("Score", ai.score)
    st.metric("Trains Left", ai.trains)
    st.write("Ticket:", route_text(ai))
    st.write("Cards in hand:", len(ai.cards))
    st.write("Hand summary:", hand_summary(ai))

    with st.expander("AI hand (visible in this simplified demo)", expanded=True):
        st.write(f"Cards in hand: **{len(ai.cards)}**")
        st.dataframe(
            pd.DataFrame([hand_summary(ai)]).T.rename(columns={0: "count"}),
            use_container_width=True,
            height=285,
        )

    with st.expander("Claimed routes", expanded=False):
        rows = claimed_paths_for_player(current_game, ai)
        st.write(f"Claimed: **{len(rows)}**")
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# Selected path panel
st.divider()
st.subheader("Selected Route")

selected = selected_path_data(current_game)
if selected is not None:
    selected_path = selected["obj"]
    claimable, available, needed, colour = can_claim_path(active_player, selected_path)
    owner = selected_path.get_occupation()

    c1, c2, c3, c4, c5, c6 = st.columns([1.1, 1.1, 1.0, 1.0, 1.1, 1.3])
    c1.metric("Route id", selected["id"])
    c2.metric("Cities", f'{selected["start"]} ↔ {selected["end"]}')
    c3.metric("Colour", str(selected["colour"]))
    c4.metric("Trains", int(selected["length"]))
    c5.metric("Owner", owner if owner is not None else "unclaimed")
    c6.metric("Your cards", f"{available} / {needed}")

    if claimable:
        st.success(f"{active_player.name} can claim this path now.")
    else:
        st.warning(f"{active_player.name} cannot claim this path yet. Need {needed} {colour} cards, currently has {available}.")
else:
    st.info("Select a path to inspect its details.")

# Actions
st.divider()
st.subheader("Actions")

legal_types = _legal_action_types(current_game)
a1, a2, a3 = st.columns([1.4, 1.3, 1.3])

with a1:
    st.write(f"Active player: **{active_player.name}**")
    if active_player.name == "Human":
        st.caption("Choose exactly one action. AI will respond automatically.")
    else:
        st.caption("Please wait: AI is taking its turn.")

with a2:
    draw_disabled = (
        ("d" not in legal_types) or current_game.terminal or (active_player.name != "Human")
    )
    if st.button("Draw", disabled=draw_disabled, use_container_width=True):
        st.session_state.last_message = None
        ok = rules.apply_action(current_game, rules.Action("d"))
        if ok is False:
            _set_message("Draw failed (deck empty).")
            st.rerun()
        _append_message("Human drew 1 card.")
        # After a valid human action, the AI immediately plays.
        execute_ai_turn(current_game, n_rollouts=int(rollouts))
        st.rerun()

with a3:
    claim_disabled = True
    if selected is not None and not current_game.terminal:
        claimable_now, _, _, _ = can_claim_path(active_player, selected["obj"])
        if claimable_now and active_player.name == "Human":
            claim_disabled = False
    if st.button("Claim", disabled=claim_disabled, use_container_width=True):
        st.session_state.last_message = None
        # Apply claim for human (consumes cards via backend) + message.
        path_obj = selected["obj"]
        colour = path_obj.get_colour()
        needed = int(path_obj.get_distance())
        ok = rules.apply_action(current_game, rules.Action("c", path_obj))
        if ok is False:
            _set_message("Claim failed (not enough cards/trains, or route already claimed).")
            st.rerun()
        _append_message(f"Human claimed {_describe_path(path_obj)} using {needed} {colour} card(s).")
        st.session_state.selected_path_id = None
        # After a valid human action, the AI immediately plays.
        execute_ai_turn(current_game, n_rollouts=int(rollouts))
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

# If the UI loads during an AI turn (e.g., after refresh), execute the AI once automatically.
# We guard with `ai_last_executed_round` to prevent double-executing on Streamlit reruns.
if active_player.name == "AI" and not current_game.terminal:
    last = st.session_state.get("ai_last_executed_round", None)
    if last != current_game.current_round:
        st.session_state.ai_last_executed_round = current_game.current_round
        execute_ai_turn(current_game, n_rollouts=int(rollouts))
        st.rerun()