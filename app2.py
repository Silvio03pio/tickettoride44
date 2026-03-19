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


st.set_page_config(page_title="The Cartographer's Ledger", layout="wide")

_COLOURS = ["red", "blue", "green", "yellow", "black", "white", "orange", "pink"]

_CARD_COLOURS = {
    "red":    ("#b91c1c", "#ffffff"),
    "blue":   ("#1d4ed8", "#ffffff"),
    "green":  ("#15803d", "#ffffff"),
    "yellow": ("#ca8a04", "#ffffff"),
    "black":  ("#1e293b", "#ffffff"),
    "white":  ("#f1f5f9", "#1f1c0b"),
    "orange": ("#ea580c", "#ffffff"),
    "pink":   ("#db2777", "#ffffff"),
}


# ─────────────────────────── Game helpers ────────────────────────────────────

def create_new_game():
    here = os.path.dirname(__file__)
    map_path = os.path.join(here, "ttr_europe_map_data.csv")
    game_graph = game.graph()
    game_graph.import_graph(map_path)
    player_human = game.player("Human", "human")
    player_ai = game.player("AI", "ai")
    players = [player_human, player_ai]
    deck_of_trains = game.deck()
    deck_of_trains.shuffle()
    current_game = state.state(game_graph, players, deck_of_trains)
    for p in current_game.players:
        p.give_ticket()
    # Deal 4 starting cards to each player (standard Ticket to Ride)
    for _ in range(4):
        for p in current_game.players:
            if current_game.deck.cards:
                p.cards.append(current_game.deck.cards.pop(0))
    return current_game


def ensure_session_state():
    if "current_game" not in st.session_state:
        st.session_state.current_game = create_new_game()
    if "selected_path_id" not in st.session_state:
        st.session_state.selected_path_id = None
    if "last_message" not in st.session_state:
        st.session_state.last_message = None
    if "grey_colour_choice" not in st.session_state:
        st.session_state.grey_colour_choice = None


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


def ticket_cities(player):
    if player.ticket is None:
        return ("—", "—", "?")
    if isinstance(player.ticket, dict):
        return (player.ticket["start"], player.ticket["end"], player.ticket["points"])
    return ("—", "—", "?")


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
            rows.append({
                "id": p.get_path_id(),
                "start": p.get_start_node().name,
                "end": p.get_end_node().name,
                "colour": p.get_colour(),
                "length": p.get_distance(),
            })
    return rows


def unclaimed_paths(current_game):
    rows = []
    for p in current_game.graph.get_paths():
        if p.get_occupation() is None:
            rows.append({
                "id": p.get_path_id(),
                "start": p.get_start_node().name,
                "end": p.get_end_node().name,
                "colour": p.get_colour(),
                "length": p.get_distance(),
                "obj": p,
                "label": f'{p.get_path_id()} | {p.get_start_node().name} ↔ {p.get_end_node().name} | {p.get_colour()} | {p.get_distance()} trains',
            })
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
    if colour == "gray":
        best_colour, best_count = None, 0
        for c in _COLOURS:
            cnt = count_matching_cards(player, c)
            if cnt > best_count:
                best_count, best_colour = cnt, c
        available = best_count
        display_colour = best_colour or "any colour"
        return available >= needed, available, needed, display_colour
    available = count_matching_cards(player, colour)
    return available >= needed, available, needed, colour


def _set_message(text: str):
    st.session_state.last_message = text


def _append_message(text: str):
    if not text:
        return
    if st.session_state.last_message:
        st.session_state.last_message = f"{st.session_state.last_message}\n{text}"
    else:
        st.session_state.last_message = text


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


def execute_ai_turn(current_game, n_rollouts: int):
    if current_game.terminal:
        return
    if current_game.current_player.name != "AI":
        return
    _append_message("AI is thinking…")
    action = None
    policy_used = None
    try:
        import search
        action, _values = search.choose_best_action_monte_carlo(current_game, n_simulations=int(n_rollouts))
        if action is not None:
            policy_used = "Monte Carlo"
    except Exception:
        action = None
    if action is None:
        actions = [a for a in rules.legal_actions(current_game) if getattr(a, "type", None) != "q"]
        action = random.choice(actions) if actions else None
        if action is not None:
            policy_used = "random"
    if action is None:
        _append_message("AI has no legal actions.")
        return
    if action.type == "d":
        msg = "AI drew 2 cards."
    elif action.type == "c" and action.path is not None:
        colour = action.path.get_colour()
        needed = int(action.path.get_distance())
        if colour == "gray":
            msg = f"AI claimed {_describe_path(action.path)} using {needed} cards of a single colour."
        else:
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


def render_map(current_game):
    net = create_map(current_game.graph, st.session_state.selected_path_id)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        temp_path = tmp.name
    net.save_graph(temp_path)
    with open(temp_path, "r", encoding="utf-8") as f:
        html = f.read()
    components.html(html, height=620, scrolling=False)
    os.unlink(temp_path)


def render_hand_cards(player):
    summary = hand_summary(player)
    cards_html = ""
    for colour in _COLOURS:
        count = summary.get(colour, 0)
        bg, fg = _CARD_COLOURS.get(colour, ("#888", "#fff"))
        opacity = "1.0" if count > 0 else "0.25"
        cards_html += f"""
        <div style="display:flex;flex-direction:column;align-items:center;gap:4px;opacity:{opacity}">
          <div style="width:44px;height:62px;background:{bg};border-radius:3px;
                      box-shadow:0 4px 8px rgba(31,28,11,0.15);border:2px solid rgba(255,255,255,0.18);
                      display:flex;align-items:center;justify-content:center;">
            <span style="color:{fg};font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.1rem">{count}</span>
          </div>
          <span style="font-family:'Space Grotesk',sans-serif;font-size:9px;text-transform:uppercase;
                       letter-spacing:0.08em;color:#43474d">{colour}</span>
        </div>"""
    return f"""
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,700;1,6..72,400&display=swap" rel="stylesheet"/>
    <div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;">{cards_html}</div>"""


def render_ticket_card(player, rotate_deg=0):
    start, end, pts = ticket_cities(player)
    return f"""
    <div style="width:140px;min-height:200px;background:#ffffff;border-radius:10px 10px 3px 3px;
                box-shadow:0 12px 32px rgba(31,28,11,0.12);border:1px solid rgba(195,198,206,0.3);
                padding:14px;display:flex;flex-direction:column;justify-content:space-between;
                transform:rotate({rotate_deg}deg);flex-shrink:0;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <span style="font-size:18px">🎫</span>
        <span style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:1.25rem;color:#142d4f">{pts}</span>
      </div>
      <div style="text-align:center;">
        <p style="font-family:'Newsreader',serif;font-size:1.1rem;font-weight:700;color:#1f1c0b;margin:0">{start}</p>
        <div style="height:1px;background:rgba(195,198,206,0.4);margin:6px 0"></div>
        <p style="font-family:'Newsreader',serif;font-size:1.1rem;font-weight:700;color:#1f1c0b;margin:0">{end}</p>
      </div>
      <div style="text-align:center;">
        <span style="font-family:'Space Grotesk',sans-serif;font-size:8px;text-transform:uppercase;
                     letter-spacing:0.1em;opacity:0.35;color:#1f1c0b">Victory Points</span>
      </div>
    </div>"""


# ──────────────────────────── App ────────────────────────────────────────────

ensure_session_state()
current_game = st.session_state.current_game
active_player = get_active_player(current_game)
other_player = get_other_player(current_game)
human = current_game.players[0]
ai = current_game.players[1]

# ── Global CSS ──
st.html("""
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,700;1,6..72,400&family=Space+Grotesk:wght@300;400;500;700&family=Work+Sans:wght@300;400;500;600&display=swap" rel="stylesheet"/>
<style>
  /* Parchment base */
  html, body, [data-testid="stAppViewContainer"] {
    background-color: #fff9ed !important;
    color: #1f1c0b;
    font-family: "Work Sans", sans-serif;
  }
  [data-testid="stSidebar"] {
    background-color: #f2ebd9 !important;
  }
  [data-testid="stSidebar"] * { color: #1f1c0b; }

  /* Hide Streamlit default header */
  [data-testid="stHeader"] { display: none !important; }
  .block-container { padding-top: 1rem !important; padding-bottom: 1.5rem; }

  /* Metric styling */
  div[data-testid="stMetricValue"] {
    font-family: "Space Grotesk", sans-serif !important;
    font-size: 1.5rem !important;
    color: #142d4f !important;
  }
  div[data-testid="stMetricLabel"] {
    font-family: "Space Grotesk", sans-serif !important;
    font-size: 0.65rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.6;
  }

  /* Section headers */
  h1, h2, h3 {
    font-family: "Newsreader", serif !important;
    color: #142d4f !important;
  }

  /* Buttons */
  [data-testid="stButton"] > button {
    background: #142d4f !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 2px !important;
    font-family: "Space Grotesk", sans-serif !important;
    font-size: 0.7rem !important;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 600;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.12);
    transition: opacity 0.15s;
  }
  [data-testid="stButton"] > button:hover:not(:disabled) { opacity: 0.88; }
  [data-testid="stButton"] > button:disabled {
    background: rgba(20,45,79,0.3) !important;
    color: rgba(255,255,255,0.5) !important;
  }

  /* Secondary/claim button override via class */
  .claim-btn [data-testid="stButton"] > button {
    background: #9b4338 !important;
  }

  /* Panels */
  .ledger-panel {
    background: #fcf3d8;
    border-radius: 3px;
    padding: 1rem;
    box-shadow: 0 12px 32px rgba(31,28,11,0.07);
  }
  .ledger-panel-glass {
    background: rgba(255,249,237,0.82);
    backdrop-filter: blur(12px);
    border-radius: 3px;
    padding: 1rem;
    box-shadow: 0 12px 32px rgba(31,28,11,0.09);
  }

  /* Dividers → vertical gap, no line */
  hr { display: none !important; }

  /* Selectbox */
  [data-testid="stSelectbox"] label {
    font-family: "Space Grotesk", sans-serif !important;
    font-size: 0.65rem !important;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    opacity: 0.6;
  }

  /* Warning / info / success boxes */
  [data-testid="stAlert"] {
    border-radius: 3px !important;
    font-family: "Work Sans", sans-serif !important;
    background-color: #f7eed2 !important;
    border-left: 4px solid #9b4338 !important;
    color: #1f1c0b !important;
  }

  .ttr-turn-badge {
    display: inline-block;
    padding: 0.2rem 0.75rem;
    border-radius: 2px;
    font-family: "Space Grotesk", sans-serif;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-weight: 700;
  }
  .ttr-turn-human {
    background: rgba(20,45,79,0.12);
    color: #142d4f;
    border: 1px solid rgba(20,45,79,0.25);
  }
  .ttr-turn-ai {
    background: rgba(155,67,56,0.12);
    color: #9b4338;
    border: 1px solid rgba(155,67,56,0.3);
  }

  .section-label {
    font-family: "Space Grotesk", sans-serif;
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    opacity: 0.5;
    color: #1f1c0b;
    margin-bottom: 0.25rem;
  }
</style>
""")

# ── Sidebar: AI Rollout Panel ──
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom:1.5rem">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
        <span style="font-size:28px">🧠</span>
        <div>
          <h2 style="margin:0;font-family:'Newsreader',serif;color:#142d4f;font-size:1.1rem;line-height:1.1">AI Rollout</h2>
          <p style="margin:0;font-family:'Space Grotesk',sans-serif;font-size:9px;text-transform:uppercase;
                    letter-spacing:0.08em;opacity:0.55;color:#1f1c0b">Monte Carlo Engine</p>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:space-between;
                background:rgba(255,249,237,0.8);padding:10px 12px;border-radius:2px;
                box-shadow:0 2px 6px rgba(31,28,11,0.07);margin-bottom:1rem">
      <div style="display:flex;align-items:center;gap:8px">
        <span style="font-size:16px">📊</span>
        <span style="font-family:'Space Grotesk',sans-serif;font-size:10px;text-transform:uppercase;
                     letter-spacing:0.1em;color:#142d4f">Diagnostics</span>
      </div>
      <span style="font-family:'Space Grotesk',sans-serif;font-size:10px;font-weight:700;color:#142d4f">ONLINE</span>
    </div>
    """, unsafe_allow_html=True)

    rollouts = st.slider("Rollouts per move", 10, 200, 50, 10)

    st.markdown(f"""
    <div style="margin-top:1.25rem;space-y:1rem">
      <p class="section-label" style="font-family:'Space Grotesk',sans-serif;font-size:9px;
                                       text-transform:uppercase;letter-spacing:0.1em;opacity:0.5;color:#1f1c0b">Live Rollouts</p>
      <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:1rem">
        <span style="font-family:'Space Grotesk',sans-serif;font-size:1.6rem;font-weight:700;color:#142d4f">{rollouts}</span>
        <span style="font-family:'Space Grotesk',sans-serif;font-size:9px;opacity:0.4;color:#1f1c0b">cycles/move</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Monte Carlo log = last_message
    log_lines = ""
    if st.session_state.last_message:
        for line in st.session_state.last_message.strip().split("\n"):
            color = "#9b4338" if "AI" in line or "failed" in line.lower() else "rgba(20,45,79,0.7)"
            log_lines += f'<p style="margin:2px 0;color:{color}">&gt; {line}</p>'
    else:
        log_lines = '<p style="margin:0;opacity:0.4;color:#1f1c0b">&gt; Awaiting first move...</p>'

    st.markdown(f"""
    <div style="margin-top:0.5rem">
      <p style="font-family:\'Space Grotesk\',sans-serif;font-size:9px;text-transform:uppercase;
                letter-spacing:0.1em;opacity:0.5;color:#1f1c0b;margin-bottom:6px">Monte Carlo Log</p>
      <div style="background:rgba(226,218,191,0.4);padding:10px;border-radius:2px;
                  max-height:180px;overflow-y:auto;font-family:monospace;font-size:9px;line-height:1.6">
        {log_lines}
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    if st.button("New Game", use_container_width=True):
        st.session_state.current_game = create_new_game()
        st.session_state.selected_path_id = None
        st.session_state.last_message = None
        st.session_state.grey_colour_choice = None
        st.rerun()

    # Claimed routes expanders
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    with st.expander("Human — claimed routes"):
        rows = claimed_paths_for_player(current_game, human)
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=150)
        else:
            st.caption("None yet.")
    with st.expander("AI — claimed routes"):
        rows = claimed_paths_for_player(current_game, ai)
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=150)
        else:
            st.caption("None yet.")

# ── Header ──
turn_is_ai = active_player.name == "AI"
turn_badge_cls = "ttr-turn-ai" if turn_is_ai else "ttr-turn-human"
turn_badge_text = "AI Strategist's Turn" if turn_is_ai else "Your Turn"

st.markdown(f"""
<div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:0.25rem">
  <span style="font-family:'Newsreader',serif;font-style:italic;font-size:1.65rem;
               color:#142d4f;letter-spacing:-0.01em">The Cartographer's Ledger</span>
  <span class="ttr-turn-badge {turn_badge_cls}">{turn_badge_text}</span>
</div>
""", unsafe_allow_html=True)

# Score row
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Human — Score", human.score)
m2.metric("Human — Trains", human.trains)
m3.metric("AI — Score", ai.score)
m4.metric("AI — Trains", ai.trains)
m5.metric("Deck left", current_game.deck.get_card_count())

if current_game.terminal:
    if current_game.terminal_reason:
        st.info(f"Game ended: {current_game.terminal_reason}")
    else:
        st.info("Game over.")

# ── Map + Route Selector ──
st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

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
        "Highlight a route on the map",
        options=labels,
        index=labels.index(current_label) if current_label in labels else 0,
    )
    chosen = next(item for item in free_paths if item["label"] == selected_label)
    st.session_state.selected_path_id = chosen["id"]
else:
    st.info("No unclaimed routes left.")

render_map(current_game)

# ── Bottom panel: Tickets + Hand ──
st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

hand_col, ticket_col = st.columns([1.6, 1.0], gap="large")

with hand_col:
    st.markdown("""
    <p style="font-family:'Space Grotesk',sans-serif;font-size:9px;text-transform:uppercase;
              letter-spacing:0.12em;opacity:0.5;color:#1f1c0b;margin-bottom:8px">
      Your Hand — Train Cards
    </p>""", unsafe_allow_html=True)
    components.html(render_hand_cards(human), height=100)

with ticket_col:
    st.markdown("""
    <p style="font-family:'Space Grotesk',sans-serif;font-size:9px;text-transform:uppercase;
              letter-spacing:0.12em;opacity:0.5;color:#1f1c0b;margin-bottom:8px">
      Active Destination Tickets
    </p>""", unsafe_allow_html=True)
    ticket_html = f"""
    <link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,700&family=Space+Grotesk:wght@700&display=swap" rel="stylesheet"/>
    <div style="display:flex;gap:-32px;align-items:flex-end;">
      {render_ticket_card(human, rotate_deg=-2)}
    </div>"""
    components.html(ticket_html, height=220)

# ── Selected Route Panel ──
st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

selected = selected_path_data(current_game)
grey_colour_choice = None  # will be set below for grey paths
if selected is not None:
    selected_path = selected["obj"]
    claimable, available, needed, colour = can_claim_path(active_player, selected_path)
    owner = selected_path.get_occupation()

    st.markdown(f"""
    <div class="ledger-panel" style="background:#fcf3d8;padding:1rem 1.25rem;border-radius:3px;
                                      box-shadow:0 12px 32px rgba(31,28,11,0.07);margin-bottom:0.75rem;
                                      border-left:4px solid #9b4338;">
      <p style="font-family:'Space Grotesk',sans-serif;font-size:9px;text-transform:uppercase;
                letter-spacing:0.12em;opacity:0.5;color:#1f1c0b;margin:0 0 6px 0">Current Objective</p>
      <h3 style="font-family:'Newsreader',serif;font-size:1.15rem;color:#142d4f;margin:0 0 4px 0">
        {selected["start"]} → {selected["end"]}
      </h3>
      <div style="display:flex;gap:1.5rem;margin-top:8px;font-family:'Space Grotesk',sans-serif;font-size:11px;color:#43474d">
        <span><b>Colour:</b> {selected["colour"]}</span>
        <span><b>Trains:</b> {int(selected["length"])}</span>
        <span><b>Owner:</b> {owner if owner else "unclaimed"}</span>
        <span><b>Your cards:</b> {available} / {needed}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # For grey paths, let the human choose which colour cards to spend
    if selected["colour"] == "gray" and active_player.name == "Human":
        hand_summary_data = hand_summary(active_player)
        eligible_colours = [c for c in _COLOURS if hand_summary_data.get(c, 0) >= needed]
        if eligible_colours:
            saved = st.session_state.grey_colour_choice
            default_idx = eligible_colours.index(saved) if saved in eligible_colours else 0
            grey_colour_choice = st.selectbox(
                f"Choose colour to spend ({needed} needed for this grey route)",
                options=eligible_colours,
                index=default_idx,
                key="grey_colour_selector",
            )
            st.session_state.grey_colour_choice = grey_colour_choice
            st.caption(f"Will spend {needed} × {grey_colour_choice} card(s) from your hand.")
        else:
            grey_colour_choice = None

    if claimable:
        st.success(f"{active_player.name} can claim this route.")
    else:
        st.warning(f"Need {needed} {colour} cards — you have {available}.")
else:
    st.markdown("""
    <div style="background:#f7eed2;padding:0.75rem 1rem;border-radius:3px;
                font-family:'Work Sans',sans-serif;font-size:0.85rem;color:#43474d;
                margin-bottom:0.75rem">
      Select a route above to inspect it.
    </div>""", unsafe_allow_html=True)

# ── Actions ──
st.markdown("<div style='height:0.25rem'></div>", unsafe_allow_html=True)
legal_types = _legal_action_types(current_game)

a_label, a_draw, a_claim = st.columns([1.5, 1.0, 1.0], gap="medium")

with a_label:
    if active_player.name == "Human":
        st.markdown("""
        <p style="font-family:'Space Grotesk',sans-serif;font-size:0.7rem;
                  text-transform:uppercase;letter-spacing:0.08em;color:#43474d;margin-top:6px">
          Choose an action — AI responds automatically.
        </p>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <p style="font-family:'Space Grotesk',sans-serif;font-size:0.7rem;
                  text-transform:uppercase;letter-spacing:0.08em;color:#9b4338;margin-top:6px">
          AI Strategist is calculating…
        </p>""", unsafe_allow_html=True)

with a_draw:
    draw_disabled = (
        ("d" not in legal_types) or current_game.terminal or (active_player.name != "Human")
    )
    if st.button("Draw Cards", disabled=draw_disabled, use_container_width=True):
        st.session_state.last_message = None
        ok = rules.apply_action(current_game, rules.Action("d"))
        if ok is False:
            _set_message("Draw failed (deck empty).")
            st.rerun()
        _append_message("Human drew 2 cards.")
        execute_ai_turn(current_game, n_rollouts=int(rollouts))
        st.rerun()

with a_claim:
    claim_disabled = True
    if selected is not None and not current_game.terminal:
        claimable_now, _, _, _ = can_claim_path(active_player, selected["obj"])
        if claimable_now and active_player.name == "Human":
            # For grey paths, a colour must be selected before claiming
            if selected["colour"] == "gray" and grey_colour_choice is None:
                claim_disabled = True
            else:
                claim_disabled = False
    if st.button("Claim Route", disabled=claim_disabled, use_container_width=True):
        st.session_state.last_message = None
        path_obj = selected["obj"]
        colour = path_obj.get_colour()
        needed = int(path_obj.get_distance())
        # Pass chosen colour for grey paths so the correct cards are spent
        chosen = grey_colour_choice if colour == "gray" else None
        action = rules.Action("c", path_obj, colour=chosen)
        ok = rules.apply_action(current_game, action)
        if ok is False:
            _set_message("Claim failed (not enough cards/trains, or route already claimed).")
            st.rerun()
        if colour == "gray":
            spent_colour = chosen or "a single colour"
            _append_message(f"Human claimed {_describe_path(path_obj)} using {needed} × {spent_colour} card(s).")
        else:
            _append_message(f"Human claimed {_describe_path(path_obj)} using {needed} {colour} card(s).")
        st.session_state.selected_path_id = None
        st.session_state.grey_colour_choice = None
        execute_ai_turn(current_game, n_rollouts=int(rollouts))
        st.rerun()

# ── Evaluation ──
st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
st.markdown("""
<p style="font-family:'Newsreader',serif;font-size:1.1rem;color:#142d4f;margin-bottom:0.5rem">
  Score Breakdown
</p>""", unsafe_allow_html=True)

try:
    breakdown = evaluation.utility_breakdown(current_game, ai, human)
    e1, e2, e3 = st.columns(3)
    with e1:
        st.markdown("""<p style="font-family:'Space Grotesk',sans-serif;font-size:9px;text-transform:uppercase;
                       letter-spacing:0.1em;opacity:0.55;color:#1f1c0b;margin-bottom:4px">Human</p>""",
                    unsafe_allow_html=True)
        st.metric("Total", breakdown["Opponent"]["total"])
        st.metric("Path pts", breakdown["Opponent"]["path_points"])
        st.metric("Ticket pts", breakdown["Opponent"]["ticket_points"])
        st.metric("Longest bonus", breakdown["Opponent"]["longest_bonus"])
    with e2:
        st.markdown("""<p style="font-family:'Space Grotesk',sans-serif;font-size:9px;text-transform:uppercase;
                       letter-spacing:0.1em;color:#9b4338;opacity:0.8;margin-bottom:4px">AI Strategist</p>""",
                    unsafe_allow_html=True)
        st.metric("Total", breakdown["AI"]["total"])
        st.metric("Path pts", breakdown["AI"]["path_points"])
        st.metric("Ticket pts", breakdown["AI"]["ticket_points"])
        st.metric("Longest bonus", breakdown["AI"]["longest_bonus"])
    with e3:
        st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
        st.metric("Utility U(s)", breakdown["utility"])
except Exception as exc:
    st.warning(f"Evaluation not available yet: {exc}")

# ── Auto-execute AI turn on load ──
if active_player.name == "AI" and not current_game.terminal:
    last = st.session_state.get("ai_last_executed_round", None)
    if last != current_game.current_round:
        st.session_state.ai_last_executed_round = current_game.current_round
        execute_ai_turn(current_game, n_rollouts=int(rollouts))
        st.rerun()
