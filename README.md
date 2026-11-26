# Algorithm Visualizer

A collection of interactive **algorithm visualizers** written in Python with [pygame](https://www.pygame.org/).
Each visualizer lets you run an algorithm, step through its solution, and trace the code as it executes.

| Visualizer | Algorithms | Problems |
|---|---|---|
| [Search Visualizer](#search-visualizer) | BFS, DFS | 8-Puzzle, Vacuum Robot |

## Repository structure

```
Algorithm-Visualizer/
├── README.md
├── .gitignore
└── SearchVisualizer/      # BFS / DFS on 8-Puzzle and Vacuum Robot
```

Each visualizer lives in its own folder and runs on its own.

---

## Search Visualizer

Visualizes two uninformed search algorithms:

- **BFS** (Breadth-First Search) uses a queue and always finds a solution with the **fewest steps**.
- **DFS** (Depth-First Search) uses a stack and explores one branch as deep as possible first, so its
  solutions are usually longer than BFS's.

on two problems:

- **8-Puzzle**: a 3×3 board with 8 numbered tiles and one blank. Slide the blank to reach the goal
  `1 2 3 / 4 5 6 / 7 8 _`.
- **Vacuum Robot**: a robot in two rooms, A and B. Each turn it chooses `Left`, `Right` or `Suck`
  until both rooms are clean.

### Features

- Choose the problem, the algorithm and the initial state (random, or edit it with the mouse).
- **"Lời giải" (Solution) tab**: animated playback of the solution, step forward/backward, speed control
  and the list of actions.
- **"Trace code" tab**: re-runs the actual `BFS` / `DFS` function and highlights each line as it executes,
  along with the current values of `node`, `action`, `child`, `frontier` and `explored`.
- Compare BFS and DFS: solution length, number of expanded nodes and running time.

> The user interface is in Vietnamese.

### Installation

Requires **Python 3.8+**.

```bash
pip install pygame
cd SearchVisualizer
python visualizer.py
```

### Usage

1. Pick a problem (**8-Puzzle** / **Vacuum**) and an algorithm (**BFS** / **DFS**) in the left sidebar.
2. Optionally change the initial state:
   - 8-Puzzle: click a tile next to the blank to slide it, or press **Xáo trộn** (Shuffle).
   - Vacuum: left-click a room to toggle Clean/Dirty, right-click a room to place the robot there,
     or press **Ngẫu nhiên** (Random).
3. Press **Giải bằng BFS/DFS** (Solve with BFS/DFS).
4. Use the playback controls to step through the solution, or switch to the **Trace code** tab
   to watch the code run line by line.

| Key | Action |
|---|---|
| `Enter` | Solve |
| `Space` | Play / Pause |
| `←` / `→` | Step backward / forward |
| `Home` / `End` | Jump to start / end |
| `+` / `-` | Speed up / slow down |
| `T` | Switch between the "Lời giải" and "Trace code" tabs |

### Source files

| File | Contents |
|---|---|
| `visualizer.py` | pygame UI; runs the search in a background thread and displays the results |
| `bfs.py` | BFS implementation (`Node`, queue helpers, `BFS(problem)`) |
| `dfs.py` | DFS implementation (`Node`, stack helpers, `DFS(problem, max_depth)`) |
| `problems.py` | The two problems: initial state, goal, `actions` and `result` functions |
| `tracer.py` | Records every executed line of `BFS` / `DFS` with `sys.settrace` for the "Trace code" tab |

### Notes

- **DFS depth limit**: unbounded DFS can return solutions tens of thousands of steps long, because it
  wanders through a huge number of states before reaching the goal. DFS is therefore limited to
  **31 steps** for 8-Puzzle (every solvable 8-Puzzle state can be solved in at most 31 moves) and
  **3 steps** for Vacuum. The limits are set by `DFS_MAX_DEPTH` in `visualizer.py`.
- **Trace limit**: the "Trace code" tab records at most **100,000 executed lines** (`MAX_EVENTS` in
  `tracer.py`). On hard 8-Puzzle states DFS runs far more lines than that, so the trace is cut off.
  Use the default state or a lightly shuffled one to see the full trace up to the final `return`.
- The running time shown in the results panel comes from a separate run without tracing, so tracing
  does not affect it.
