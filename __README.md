# Setup Guide — Ticket to Ride AI

## Prerequisites

- **Python 3.10+** — download from https://www.python.org/downloads/

## Install dependencies

Open a terminal in this folder and run:

```bash
pip install -r requirements.txt
```

This installs:

| Package      | Purpose                                      |
|--------------|----------------------------------------------|
| `pandas`     | Data handling (hand summaries, route tables)  |
| `streamlit`  | Web-based UI for the game (`app3.py`)         |
| `pyvis`      | Interactive network graph for the board map   |

## How to run

### Terminal mode (no UI)

```bash
python main.py
```

Play the game directly in the terminal. At startup you are prompted to choose the AI algorithm:

1. **MCTS (Monte Carlo Tree Search)** — you then enter the number of rollouts (default 50).
2. **Alpha-Beta Pruning** — you then enter the search depth (default 3).

During the game you type commands (`d` to draw, `c` to claim, `q` to quit, `h` to see your hand, `s` for scoreboard, `r` for claimed routes).

### Web UI mode (Streamlit)

```bash
python main2.py
```

Opens an interactive browser-based interface with a visual map, route selection, and evaluation panels. The sidebar includes an **AI Settings** section where you can switch between MCTS and Alpha-Beta Pruning and configure the rollout count or search depth at any time during the game.

## Troubleshooting

- If `pip` is not recognized, try `pip3` or `python -m pip` instead.
- On some systems you may need to use `python3` instead of `python`.
- Make sure the CSV data files (`ttr_europe_map_data.csv`, `route_cards.csv`) are present in this folder — they ship with the repository.

---

## File Descriptions

### Python files

| File | Description |
|------|-------------|
| `main.py` | Terminal-mode entry point. Prompts the player to choose the AI algorithm (MCTS or Alpha-Beta Pruning) and its parameter (rollouts or depth), then runs a full Human vs AI game in the console with text-based input (draw, claim, quit, view hand/score/routes). No GUI required. |

| `main2.py` | Streamlit entry point and shared helpers. Contains `create_new_game()` (initialises the board, players, deck, and tickets), `execute_ai_turn()` (runs the AI's decision via MCTS or Alpha-Beta Pruning), hand formatting utilities, and the terminal print helpers (`_print_turn_header`, `_print_final_scoring`). Running `python main2.py` launches the Streamlit web UI. |

| `app3.py` | Streamlit web UI. Builds the full browser-based interface: interactive board map (via PyVis), player panels, route selection/search, draw and claim buttons, evaluation dashboard, and debug panels. |

| `game.py` | Core game objects. Defines the `player`, `node`, `path`, `card`, `deck`, `graph`, and `ticket` classes. Also includes graph algorithms: BFS shortest path, longest possible route (graph diameter), building a player's subgraph, and finding the shortest connection between two subgraphs. Loads the board from CSV. |

| `state.py` | Game state container. The `state` class holds the full game: graph, players, deck, discard pile, turn counter, and terminal/endgame flags. Also provides `observable_state_for_ai()` which returns a restricted view that hides the opponent's hand and the deck order (partial observability). |

| `rules.py` | Game rules and action logic. Defines the `Action` dataclass (draw / claim / quit), `legal_actions()`, `apply_action()`, `claim_path()`, and `draw_card()`. Also contains the human interactive input handler (`human_decide_action`), the Alpha-Beta Pruning search (`alpha_beta_pruning_decide_action`), and opponent-model helpers used during simulation (`_opponent_legal_actions`, `_opponent_apply_action`). |

| `evaluation.py` | Scoring and evaluation functions. Implements `points_for_path_length()` (standard Ticket to Ride scoring table), `claimed_path_points()`, `destination_ticket_points()` (+/- based on completion), `longest_path_bonus()`, `final_score()`, `utility()` (AI score minus opponent score), `utility_breakdown()`, and the non-terminal heuristic `E_s()` used by the search algorithms. |

| `search.py` | Monte Carlo Tree Search (MCTS). Implements UCB1-based tree search with selection, expansion, random rollout, and backpropagation. Opponent turns are treated as stochastic environment transitions (Boltzmann-sampled via `E_s`). Exposes `choose_best_action_monte_carlo()` and `mcts_search()` as the main API. |

| `models_P.py` | Probabilistic model terms for the evaluation function. Computes `P_colour()` (probability of drawing a specific colour from the deck), `C_c()` (card-contribution heuristic weighting route value, draw probability, and cards in hand), `P_L()` (estimated probability of winning the longest path bonus), and `P_R()` (ticket-completion progress term). |

| `graph_ui.py` | Board visualisation with PyVis. Converts the game graph into an interactive HTML network map. Colours edges by ownership (blue = Human, red = AI), highlights the selected route, and positions cities using their longitude/latitude coordinates. |

### Data files

| File | Description |
|------|-------------|
| `ttr_europe_map_data.csv` | Board definition. Contains all cities (nodes with coordinates) 
and routes (paths with colour, length, and endpoints) for the Ticket to Ride Europe map. |

| `route_cards.csv` | Destination tickets. Each row is a ticket with two cities and a point value, drawn at the start of the game. |

### Config files

| File | Description |
|------|-------------|
| `requirements.txt` | Python package dependencies. Run `pip install -r requirements.txt` to install everything needed. |

| `__TASKS.txt` | Internal task tracking notes. |

---

## How the Game Works

This is a simplified two-player version of **Ticket to Ride Europe**, where a human player competes against an AI opponent on a graph-based map of European cities.

### Setup

- The board is a graph of **cities** (nodes) connected by **routes** (edges). Each route has a **colour** and a **length** (1–6 trains).
- A shared **deck** of 96 train cards is created (12 cards per colour across 8 colours: red, blue, green, yellow, black, white, orange, pink) and shuffled.
- Each player starts with **44 trains** and receives one **destination ticket** — a pair of cities they must try to connect for bonus points.

### Turn Structure

Players alternate turns. On each turn, a player must do **one** of the following:

1. **Draw a card** — take the top card from the deck and add it to your hand. If the deck runs out, the discard pile is reshuffled into a new deck. If both are empty, drawing is no longer possible.

2. **Claim a route** — spend train cards from your hand matching the route's colour and length to claim it. The route is now yours: it scores points immediately and counts toward your network. For **grey routes**, any single colour can be used as long as you have enough cards of that colour. Each claimed route also costs that many trains from your supply of 44.

3. **Quit** (human only) — end the game early.

### Endgame

The endgame triggers when any player drops to **2 or fewer trains** remaining. After that, the other player gets **one final turn**, and then the game ends. The game also ends if both the deck and the discard pile are empty and no draw is possible.

### Scoring

At the end of the game, each player's final score is the sum of three components:

| Component | How it works |
|-----------|--------------|
| **Route points** | Points awarded immediately when claiming a route, based on its length: 1 train = 1 pt, 2 = 2, 3 = 4, 4 = 7, 5 = 10, 6 = 15. |
| **Destination ticket** | If you connected the two cities on your ticket through your claimed routes: **+points**. If not: **-points** (penalty). |
| **Longest path bonus** | The player with the longest continuous chain of claimed routes gets **+10 points**. If tied, both players receive the bonus. |

The **utility** of a final game state is defined as:

```
U(s) = FinalScore(AI) - FinalScore(Human)
```

A positive utility means the AI won; negative means the human won.

### AI Decision-Making

The player can choose between two AI algorithms at the start of each game (terminal mode) or at any time via the sidebar (web UI):

#### Monte Carlo Tree Search (MCTS)

Controlled by the **number of rollouts** (default 50). The four phases per iteration:

1. **Selection** — walk down the search tree, picking the most promising child node using the UCB1 formula (balancing exploitation and exploration).
2. **Expansion** — when a leaf node is reached, expand one untried action.
3. **Simulation (rollout)** — play out the rest of the game randomly from that point to a terminal state.
4. **Backpropagation** — propagate the result (utility) back up the tree to update visit counts and value estimates.

After many iterations, the AI picks the action with the **most visits** (robust child selection).

During MCTS, opponent turns are modelled as **stochastic environment transitions**: the opponent's moves are sampled using a Boltzmann-weighted policy based on a heuristic evaluation function `E(s)`, rather than being part of the search tree. This reflects the **partial observability** of the game — the AI cannot see the opponent's hand.

#### Alpha-Beta Pruning

Controlled by the **search depth** (default 3). This is a classic minimax search with alpha-beta pruning:

- **Maximising nodes** correspond to the AI's turns; **minimising nodes** correspond to the opponent's turns.
- At terminal states the true `utility()` is used. At depth-limited leaves the heuristic `E(s)` provides an estimate.
- The opponent is modelled with **imperfect information**: since the AI cannot see the opponent's hand, the opponent is assumed to be able to claim any route they have enough trains for (card constraints are ignored).
- Alpha-beta cut-offs prune branches that cannot affect the final decision, making the search more efficient than plain minimax.

### Non-Terminal Evaluation: E(s)

When the search reaches a depth limit (not a terminal state), the heuristic `E(s)` estimates the position's value:

```
E(s) = Delta_C_T + P_L * longest_bonus + P_R * ticket_points + C_c
```

Where:
- **Delta_C_T** — sum of claimed route points for opponents (context for relative standing).
- **P_L** — estimated probability of winning the longest path bonus, based on the ratio of consecutive claimed paths.
- **P_R** — ticket-completion progress, measuring how close the player is to connecting their destination cities relative to the board diameter.
- **C_c** — card-contribution term, weighting each unclaimed route by its score value, the probability of drawing its colour from the deck, and how many matching cards the player already holds.

### Game Properties

This implementation models Ticket to Ride as a:
- **Two-player** adversarial game
- **Turn-based** (players alternate)
- **Stochastic** (card draws are random)
- **Partially observable** (each player's hand and the deck order are hidden from the opponent)
