PUZZLE_INITIAL = (
    (1, 2, 3),
    (4, 0, 6),
    (7, 5, 8)
)

PUZZLE_GOAL = (
    (1, 2, 3),
    (4, 5, 6),
    (7, 8, 0)
)


def find_blank(state):
    for r in range(3):
        for c in range(3):
            if state[r][c] == 0:
                return r, c


def get_actions_8puzzle(state):
    r, c = find_blank(state)
    actions = []
    if r > 0:
        actions.append('Up')
    if r < 2:
        actions.append('Down')
    if c > 0:
        actions.append('Left')
    if c < 2:
        actions.append('Right')

    return actions


def get_result_8puzzle(state, action):
    r, c = find_blank(state)
    grid = [list(row) for row in state]
    if action == 'Up':
        grid[r][c], grid[r - 1][c] = grid[r - 1][c], grid[r][c]
    elif action == 'Down':
        grid[r][c], grid[r + 1][c] = grid[r + 1][c], grid[r][c]
    elif action == 'Left':
        grid[r][c], grid[r][c - 1] = grid[r][c - 1], grid[r][c]
    elif action == 'Right':
        grid[r][c], grid[r][c + 1] = grid[r][c + 1], grid[r][c]
    return tuple(tuple(row) for row in grid)


def get_cost_8puzzle(state, action, new_state):
    if action in ('Up', 'Down'):
        return 1
    return 2


VACUUM_INITIAL = ('A', 'D', 'D')


def is_goal_vacuum(state):
    return state in [('A', 'C', 'C'), ('B', 'C', 'C')]


def get_actions_vacuum(state):
    return ['Suck', 'Left', 'Right']


def get_result_vacuum(state, action):
    pos, status_A, status_B = state

    if action == 'Suck':
        if pos == 'A':
            return ('A', 'C', status_B)
        elif pos == 'B':
            return ('B', status_A, 'C')

    elif action == 'Left':
        return ('A', status_A, status_B)

    elif action == 'Right':
        return ('B', status_A, status_B)

    return state


def get_cost_vacuum(state, action, new_state):
    if action == 'Suck':
        return 1
    return 2
