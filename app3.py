import os
import tempfile

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import evaluation
import game
import rules
from graph_ui import create_map

from main2 import create_new_game, hand_summary, execute_ai_turn


st.set_page_config(page_title="Ticket to Ride AI", layout="wide")

_COLOURS = ["red", "blue", "green", "yellow", "black", "white", "orange", "pink"]


def ensure_session_state():
    if "current_game" not in st.session_state:
        st.session_state.current_game = create_new_game()
    if "selected_path_id" not in st.session_state:
        st.session_state.selected_path_id = None
    if "last_message" not in st.session_state:
        st.session_state.last_message = None
    if "rollouts" not in st.session_state:
        st.session_state.rollouts = 50
    if "ai_algorithm" not in st.session_state:
        st.session_state.ai_algorithm = "mcts"
    if "ab_depth" not in st.session_state:
        st.session_state.ab_depth = 3
    if "show_debug" not in st.session_state:
        st.session_state.show_debug = False
    if "ai_last_executed_round" not in st.session_state:
        st.session_state.ai_last_executed_round = None
    if "show_only_claimable_routes" not in st.session_state:
        st.session_state.show_only_claimable_routes = True


def reset_game_state():
    st.session_state.current_game = create_new_game()
    st.session_state.selected_path_id = None
    st.session_state.last_message = None
    st.session_state.ai_last_executed_round = None


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
        return f'{player.ticket["start"]} → {player.ticket["end"]} ({player.ticket["points"]} pts)'
    return str(player.ticket)


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
                    "label": (
                        f'{p.get_path_id()} | {p.get_start_node().name} ↔ {p.get_end_node().name} | '
                        f'{p.get_colour()} | {p.get_distance()} trains'
                    ),
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


def can_claim_path(player, path):
    needed = path.get_distance()
    colour = path.get_colour()

    # Grey paths accept any single colour — find the best one the player has.
    if colour == "gray":
        best_colour, best_count = None, 0
        for c in _COLOURS:
            cnt = count_matching_cards(player, c)
            if cnt >= needed and cnt > best_count:
                best_count, best_colour = cnt, c
        if best_colour is not None:
            return True, best_count, needed, best_colour
        # Not enough of any single colour
        best_available = max(count_matching_cards(player, c) for c in _COLOURS)
        return False, best_available, needed, "gray"

    available = count_matching_cards(player, colour)
    return available >= needed, available, needed, colour


def claimable_paths(current_game, player):
    rows = []
    for item in unclaimed_paths(current_game):
        can_claim, available, needed, colour = can_claim_path(player, item["obj"])
        if can_claim:
            enriched = dict(item)
            enriched["available"] = available
            enriched["needed"] = needed
            enriched["claim_colour"] = colour
            rows.append(enriched)
    return rows


def selected_path_data(current_game):
    path_id = st.session_state.selected_path_id
    if path_id is None:
        return None

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


def _set_message(text: str):
    st.session_state.last_message = text


def _append_message(text: str):
    if not text:
        return
    if st.session_state.last_message:
        st.session_state.last_message = f"{st.session_state.last_message}\n{text}"
    else:
        st.session_state.last_message = text


def _append_messages(messages):
    for msg in messages:
        _append_message(msg)


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
    return {a.type for a in rules.legal_actions(current_game)}


def _describe_path(path_obj):
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


ensure_session_state()
current_game = st.session_state.current_game
active_player = get_active_player(current_game)
other_player = get_other_player(current_game)

human = current_game.players[0]
ai = current_game.players[1]

with st.sidebar:
    st.markdown("## 🎮 Controls")
    st.caption("Manage the current Ticket to Ride match")

    if st.button("New Game", use_container_width=True):
        reset_game_state()
        st.rerun()

    st.markdown("---")
    st.markdown("### AI Settings")

    algo_options = ["MCTS (Monte Carlo Tree Search)", "Alpha-Beta Pruning"]
    algo_index = 0 if st.session_state.ai_algorithm == "mcts" else 1
    algo_choice = st.selectbox("AI Algorithm", algo_options, index=algo_index)
    st.session_state.ai_algorithm = "mcts" if algo_choice == algo_options[0] else "alphabeta"

    if st.session_state.ai_algorithm == "mcts":
        st.session_state.rollouts = st.number_input(
            "MCTS Rollouts", min_value=1, max_value=10000,
            value=st.session_state.rollouts, step=10,
        )
    else:
        st.session_state.ab_depth = st.number_input(
            "Alpha-Beta Depth", min_value=1, max_value=20,
            value=st.session_state.ab_depth, step=1,
        )

    show_debug = st.session_state.show_debug
    rollouts = st.session_state.rollouts
    ai_algorithm = st.session_state.ai_algorithm
    ab_depth = st.session_state.ab_depth

st.markdown(
    """
    <style>
      .block-container {
        padding-top: 1.1rem;
        padding-bottom: 1.8rem;
        padding-left: 1.2rem;
        padding-right: 1.2rem;
        max-width: 1450px;
      }

      .stApp {
        background:
          radial-gradient(circle at top left, rgba(59, 130, 246, 0.08), transparent 24%),
          radial-gradient(circle at top right, rgba(251, 191, 36, 0.08), transparent 20%),
          linear-gradient(180deg, #0b1220 0%, #111827 45%, #0f172a 100%);
        color: #f8fafc;
      }

      html, body, [class*="css"] {
        color: #f8fafc;
      }

      h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
      }

      p, li, label {
        color: #e5e7eb !important;
      }

      section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
        border-right: 1px solid rgba(148, 163, 184, 0.18);
      }

      section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
      }

      div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.88));
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 16px;
        padding: 0.95rem 1rem;
      }

      div[data-testid="stMetric"] * {
        color: #f8fafc !important;
      }

      div[data-testid="stMetricLabel"] {
        color: #cbd5e1 !important;
        opacity: 1 !important;
      }

      div[data-testid="stMetricValue"] {
        color: #ffffff !important;
      }

      .stButton > button {
        width: 100%;
        border-radius: 12px;
        border: 1px solid rgba(251, 191, 36, 0.32);
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        color: #ffffff !important;
        font-weight: 800;
      }

      .stButton > button:hover {
        border-color: rgba(251, 191, 36, 0.72);
        box-shadow: 0 8px 18px rgba(0, 0, 0, 0.24);
      }

      .stTextInput label,
      .stSelectbox label,
      .stSlider label,
      .stCheckbox label {
        color: #ffffff !important;
        font-weight: 800 !important;
        letter-spacing: 0.2px;
      }

      .stTextInput input {
        background: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        border-radius: 12px !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
      }

      .stTextInput input:focus {
        border: 1px solid rgba(251, 191, 36, 0.75) !important;
        box-shadow:
          0 0 0 1px rgba(251, 191, 36, 0.35),
          0 0 0 4px rgba(251, 191, 36, 0.12) !important;
      }

      .stTextInput input::placeholder {
        color: #cbd5e1 !important;
        opacity: 1 !important;
      }

      /* Closed select */
      .stSelectbox > div[data-baseweb="select"] > div {
        background: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid rgba(148, 163, 184, 0.3) !important;
        border-radius: 12px !important;
        min-height: 46px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      }

      .stSelectbox > div[data-baseweb="select"] > div:hover {
        border: 1px solid rgba(251, 191, 36, 0.6) !important;
      }

      .stSelectbox > div[data-baseweb="select"] span {
        color: #f8fafc !important;
        font-weight: 600 !important;
      }

      .stSelectbox > div[data-baseweb="select"] input {
        color: #f8fafc !important;
      }

      .stSelectbox > div[data-baseweb="select"] svg {
        fill: #f8fafc !important;
      }

      /* Open dropdown — BaseWeb popover */
      [data-baseweb="popover"],
      [data-baseweb="popover"] > div,
      [data-baseweb="menu"],
      div[role="listbox"],
      ul[role="listbox"] {
        background: #0f172a !important;
        background-color: #0f172a !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
        border-radius: 12px !important;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.5) !important;
        padding: 6px !important;
      }

      [data-baseweb="popover"] li,
      [data-baseweb="menu"] li,
      div[role="option"],
      li[role="option"] {
        background: #0f172a !important;
        background-color: #0f172a !important;
        color: #f8fafc !important;
        border-radius: 8px !important;
        margin: 2px 0 !important;
        padding: 10px 12px !important;
        font-weight: 600 !important;
      }

      [data-baseweb="popover"] li *,
      [data-baseweb="menu"] li *,
      div[role="option"] *,
      li[role="option"] * {
        background: transparent !important;
        background-color: transparent !important;
        color: #f8fafc !important;
        font-weight: 600 !important;
      }

      [data-baseweb="popover"] li:hover,
      [data-baseweb="menu"] li:hover,
      div[role="option"]:hover,
      li[role="option"]:hover {
        background: #1e293b !important;
        background-color: #1e293b !important;
        color: #ffffff !important;
      }

      [data-baseweb="popover"] li[aria-selected="true"],
      [data-baseweb="menu"] li[aria-selected="true"],
      div[aria-selected="true"],
      li[aria-selected="true"] {
        background: rgba(251, 191, 36, 0.2) !important;
        background-color: rgba(251, 191, 36, 0.2) !important;
        color: #fbbf24 !important;
        font-weight: 800 !important;
      }

      [data-baseweb="popover"] li[aria-selected="true"] *,
      div[aria-selected="true"] *,
      li[aria-selected="true"] * {
        color: #fbbf24 !important;
      }

      div[data-testid="stDataFrame"] * {
        color: #f8fafc !important;
      }

      details * {
        color: #f8fafc !important;
      }

      .ttr-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.7rem;
        border-radius: 999px;
        font-weight: 800;
        font-size: 0.84rem;
        border: 1px solid rgba(148, 163, 184, 0.24);
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.85));
        color: #ffffff !important;
      }

      .ttr-badge-ai {
        border-color: rgba(239, 68, 68, 0.52);
        color: #ffe4e6 !important;
      }

      .ttr-badge-human {
        border-color: rgba(34, 197, 94, 0.52);
        color: #dcfce7 !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

header = st.container()
with header:
    c_title, c_status = st.columns([1.4, 1.0])

    with c_title:
        st.title("Ticket to Ride — Human vs AI")

    with c_status:
        turn_badge = (
            '<span class="ttr-badge ttr-badge-ai">AI turn</span>'
            if active_player.name == "AI"
            else '<span class="ttr-badge ttr-badge-human">Human turn</span>'
        )
        st.markdown(turn_badge, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Turn", current_game.current_round)
    m2.metric("Active player", active_player.name)
    m3.metric("Deck cards left", current_game.deck.get_card_count())
    m4.metric(
        "Unclaimed routes",
        sum(1 for p in current_game.graph.get_paths() if p.get_occupation() is None),
    )

    if getattr(current_game, "terminal_reason", None):
        st.info(f"Game ended: {current_game.terminal_reason}")

    if st.session_state.last_message:
        st.warning(st.session_state.last_message)

left, center, right = st.columns([1.05, 1.9, 1.05], gap="large")

with left:
    st.markdown('<h3 style="color:#3b82f6 !important;">Human <span style="font-size:0.7em;">(blue on map)</span></h3>', unsafe_allow_html=True)
    st.metric("Score", human.score)
    st.metric("Trains Left", human.trains)
    st.write("Ticket:", route_text(human))
    st.write("Cards in hand:", len(human.cards))

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
        else:
            st.caption("No routes claimed yet.")

with center:
    st.subheader("Board")
    st.caption("Edge labels show required trains. Hover a route for full details.")
    st.markdown(
        '<span style="color:#3b82f6; font-weight:700;">&#9632; Human (blue)</span>'
        ' &nbsp;&nbsp; '
        '<span style="color:#ef4444; font-weight:700;">&#9632; AI (red)</span>',
        unsafe_allow_html=True,
    )

    show_only_claimable = st.session_state.show_only_claimable_routes
    if show_only_claimable:
        base_paths = claimable_paths(current_game, active_player)
    else:
        base_paths = unclaimed_paths(current_game)

    if base_paths:
        s1, s2 = st.columns([1.1, 2.2])

        with s1:
            route_id_input = st.text_input(
                "Jump to route ID",
                value="",
                placeholder="e.g. 12",
                key="route_id_jump",
            ).strip()

        with s2:
            search_query = st.text_input(
                "Search route by id, city or colour",
                value="",
                placeholder="Example: Paris, blue, 12",
                key="route_search_box",
            ).strip().lower()

        if route_id_input:
            matched = next(
                (item for item in base_paths if str(item["id"]) == route_id_input),
                None
            )
            if matched is not None:
                st.session_state.selected_path_id = matched["id"]

        filtered_paths = base_paths
        if search_query:
            filtered_paths = [
                item for item in base_paths
                if search_query in str(item["id"]).lower()
                or search_query in item["start"].lower()
                or search_query in item["end"].lower()
                or search_query in item["colour"].lower()
                or search_query in item["label"].lower()
            ]

        if not filtered_paths:
            st.warning("No routes match your search.")
        else:
            caption_prefix = "claimable" if show_only_claimable else "available"
            st.caption(
                f"Showing {len(filtered_paths)} {caption_prefix} route(s) out of {len(base_paths)}."
            )

            labels = [item["label"] for item in filtered_paths]
            current_label = None

            if st.session_state.selected_path_id is not None:
                for item in filtered_paths:
                    if str(item["id"]) == str(st.session_state.selected_path_id):
                        current_label = item["label"]
                        break

            selected_label = st.selectbox(
                "Highlight a route",
                options=labels,
                index=labels.index(current_label) if current_label in labels else 0,
                key="route_selectbox",
            )

            chosen = next(item for item in filtered_paths if item["label"] == selected_label)
            st.session_state.selected_path_id = chosen["id"]
    else:
        if show_only_claimable:
            st.info("No claimable routes available for the active player right now.")
        else:
            st.info("No unclaimed routes left.")

    render_map(current_game)

with right:
    st.markdown('<h3 style="color:#ef4444 !important;">AI <span style="font-size:0.7em;">(red on map)</span></h3>', unsafe_allow_html=True)
    st.metric("Score", ai.score)
    st.metric("Trains Left", ai.trains)
    st.write("Ticket:", route_text(ai))
    st.write("Cards in hand:", len(ai.cards))

    with st.expander("AI hand / debug", expanded=show_debug):
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
        else:
            st.caption("No routes claimed yet.")

st.divider()
st.subheader("Selected Route")

selected = selected_path_data(current_game)
if selected is not None:
    selected_path = selected["obj"]
    claimable, available, needed, colour = can_claim_path(active_player, selected_path)
    owner = selected_path.get_occupation()

    c1, c2, c3, c4, c5, c6 = st.columns([1.0, 1.5, 1.0, 1.0, 1.1, 1.1])
    c1.metric("Route id", selected["id"])
    c2.metric("Cities", f'{selected["start"]} ↔ {selected["end"]}')
    c3.metric("Colour", str(selected["colour"]))
    c4.metric("Trains", int(selected["length"]))
    c5.metric("Owner", owner if owner is not None else "unclaimed")
    c6.metric("Your cards", f"{available} / {needed}")

    if owner is not None:
        st.info(f"This route is already owned by {owner}.")
    elif claimable:
        st.success(f"{active_player.name} can claim this path now.")
    else:
        st.warning(
            f"{active_player.name} cannot claim this path yet. Need {needed} {colour} cards, currently has {available}."
        )
else:
    st.info("Select a path to inspect its details.")

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
        ("d" not in legal_types)
        or current_game.terminal
        or (active_player.name != "Human")
    )

    if st.button("Draw", disabled=draw_disabled, use_container_width=True):
        st.session_state.last_message = None

        ok = rules.apply_action(current_game, rules.Action("d"))
        if ok is False:
            _set_message("Draw failed (deck empty).")
            st.rerun()

        _append_message("Human drew 1 card.")
        ai_messages = execute_ai_turn(current_game, n_rollouts=int(rollouts), algorithm=ai_algorithm, ab_depth=int(ab_depth))
        _append_messages(ai_messages)
        st.rerun()

with a3:
    claim_disabled = True
    if selected is not None and not current_game.terminal:
        claimable_now, _, _, _ = can_claim_path(active_player, selected["obj"])
        if claimable_now and active_player.name == "Human" and selected["obj"].get_occupation() is None:
            claim_disabled = False

    if st.button("Claim", disabled=claim_disabled, use_container_width=True):
        st.session_state.last_message = None

        path_obj = selected["obj"]
        _, _, needed, colour = can_claim_path(active_player, path_obj)
        needed = int(needed)

        # For grey paths, pass the chosen colour so the right cards are spent.
        claim_colour = colour if path_obj.get_colour() == "gray" else None
        ok = rules.apply_action(current_game, rules.Action("c", path_obj, colour=claim_colour))
        if ok is False:
            _set_message("Claim failed (not enough cards/trains, or route already claimed).")
            st.rerun()

        _append_message(f"Human claimed {_describe_path(path_obj)} using {needed} {colour} card(s).")
        st.session_state.selected_path_id = None
        ai_messages = execute_ai_turn(current_game, n_rollouts=int(rollouts), algorithm=ai_algorithm, ab_depth=int(ab_depth))
        _append_messages(ai_messages)
        st.rerun()

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

if show_debug:
    st.divider()
    st.subheader("Debug Panels")

    d1, d2 = st.columns(2)
    with d1:
        st.write("**Deck composition**")
        st.dataframe(deck_dataframe(current_game.deck), use_container_width=True, hide_index=True)

    with d2:
        st.write("**Internal status**")
        st.write("Current round:", current_game.current_round)
        st.write("Terminal:", getattr(current_game, "terminal", False))
        st.write("Active player:", current_game.current_player.name)

if active_player.name == "AI" and not current_game.terminal:
    last = st.session_state.get("ai_last_executed_round", None)
    if last != current_game.current_round:
        st.session_state.ai_last_executed_round = current_game.current_round
        ai_messages = execute_ai_turn(current_game, n_rollouts=int(rollouts), algorithm=ai_algorithm, ab_depth=int(ab_depth))
        _append_messages(ai_messages)
        st.rerun()