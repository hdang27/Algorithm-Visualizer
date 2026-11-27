# Algorithm Visualizer

An interactive **search algorithm visualizer** written in Python with [pygame](https://www.pygame.org/).
Run BFS, DFS or UCS on the 8-Puzzle or the Vacuum Robot problem, step through the solution,
and trace the code line by line as it executes.

## Repository structure

```
Algorithm-Visualizer/
├── README.md
├── .gitignore
├── .gitattributes
├── visualizer.py      # pygame UI (entry point)
├── bfs.py             # BFS
├── dfs.py             # DFS
├── ucs.py             # UCS
├── UCS.ipynb          # UCS notebook with runnable examples
├── problems.py        # 8-Puzzle and Vacuum Robot definitions
├── tracer.py          # line-by-line tracing for the "Trace code" tab
└── scaling.py         # high-DPI scaling helpers
```

## Algorithms and problems

The visualizer supports three search algorithms:

| Algorithm | Frontier | What it finds |
|---|---|---|
| **BFS** (Breadth-First Search) | Queue (FIFO) | A solution with the **fewest steps** |
| **DFS** (Depth-First Search) | Stack (LIFO) | Goes as deep as possible along one branch first; solutions are usually much longer than BFS's |
| **UCS** (Uniform-Cost Search) | Priority queue ordered by path cost `g(n)` | A solution with the **lowest total cost** |

They run on two problems:

- **8-Puzzle**: a 3×3 board with 8 numbered tiles and one blank. Slide the blank to reach the goal
  `1 2 3 / 4 5 6 / 7 8 _`.
- **Vacuum Robot**: a robot in two rooms, A and B. Each turn it chooses `Left`, `Right` or `Suck`
  until both rooms are clean.

## Action costs (UCS)

UCS uses these action costs. BFS and DFS ignore them, so the visualizer shows costs only for UCS.

| Problem | Cost 1 | Cost 2 |
|---|---|---|
| 8-Puzzle | `Up`, `Down` | `Left`, `Right` |
| Vacuum Robot | `Suck` | `Left`, `Right` |

Because horizontal moves cost more, UCS can return a solution with more steps than BFS but a lower total cost.

## Features

- Choose the problem, the algorithm (BFS / DFS / UCS) and the initial state (random, or edit it with the mouse).
- **"Lời giải" (Solution) tab**: animated playback of the solution, step forward/backward, speed control
  and the list of actions. With UCS, the header also shows the accumulated cost `g` at the current step.
- **"Trace code" tab**: re-runs the actual `BFS` / `DFS` / `UCS` function and highlights each line as it
  executes, along with the current values of `node`, `action`, `child`, `frontier` and `explored`.
  - DFS also shows the depth `d`.
  - UCS shows `node.g` and `child.g`, and lists the priority queue sorted by `g` (the top entry is the next
    to be dequeued), each with its cost.
- Compare the three algorithms in the results panel: solution length, number of expanded nodes, running time,
  and the total cost for UCS.

> The user interface is in Vietnamese.

## Installation

Requires **Python 3.8+** and pygame (or pygame-ce).

```bash
pip install pygame
python visualizer.py
```

## Usage

1. Pick a problem (**8-Puzzle** / **Vacuum**) and an algorithm (**BFS** / **DFS** / **UCS**) in the left sidebar.
2. Optionally change the initial state:
   - 8-Puzzle: click a tile next to the blank to slide it, or press **Xáo trộn** (Shuffle).
   - Vacuum: left-click a room to toggle Clean/Dirty, right-click a room to place the robot there,
     or press **Ngẫu nhiên** (Random).
3. Press **Giải bằng BFS/DFS/UCS** (Solve with ...).
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

## Source files

| File | Contents |
|---|---|
| `visualizer.py` | pygame UI; runs the search in a background thread and displays the results |
| `bfs.py` | BFS implementation (`Node`, queue helpers, `BFS(problem)`) |
| `dfs.py` | DFS implementation (`Node`, stack helpers, `DFS(problem, max_depth)`) |
| `ucs.py` | UCS implementation (`Node` with `path_cost`, heap-based priority queue, `UCS(problem)`) |
| `UCS.ipynb` | Notebook version of UCS with runnable 8-Puzzle and Vacuum examples |
| `problems.py` | The two problems: initial state, goal, `actions`, `result` and action-cost functions |
| `tracer.py` | Records every executed line of the search function with `sys.settrace` for the "Trace code" tab |
| `scaling.py` | High-DPI scaling helpers for the pygame window |

## Notes

- **DFS depth limit**: unbounded DFS can return solutions tens of thousands of steps long, because it
  wanders through a huge number of states before reaching the goal. DFS is therefore limited to
  **31 steps** for 8-Puzzle (every solvable 8-Puzzle state can be solved in at most 31 moves) and
  **3 steps** for Vacuum. The limits are set by `DFS_MAX_DEPTH` in `visualizer.py`.
- **UCS on hard states**: UCS checks whether a state is already in the frontier by scanning it linearly
  (`find_in_frontier`), so heavily shuffled 8-Puzzle states can take noticeably longer than BFS.
- **Trace limit**: the "Trace code" tab records at most **100,000 executed lines** (`MAX_EVENTS` in
  `tracer.py`). On hard 8-Puzzle states DFS and UCS run far more lines than that, so the trace is cut off.
  Use the default state or a lightly shuffled one to see the full trace up to the final `return`.
- The running time shown in the results panel comes from a separate run without tracing, so tracing
  does not affect it.
