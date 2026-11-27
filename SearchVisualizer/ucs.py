import heapq


class Node:
    def __init__(self, state, parent=None, action=None, path_cost=0):
        self.state = state
        self.parent = parent
        self.action = action
        self.path_cost = path_cost      # g(n): tổng chi phí từ gốc đến node này

    def __lt__(self, other):            # để heapq so sánh các node theo g(n)
        return self.path_cost < other.path_cost


def is_goal(state, goal_condition):
    if callable(goal_condition):
        return goal_condition(state)
    return state == goal_condition


def PriorityQueue():
    queue = []
    return queue


def enqueue(queue, node):
    heapq.heappush(queue, node)


def dequeue(queue):
    if is_empty(queue):
        return None
    return heapq.heappop(queue)         # node có g(n) nhỏ nhất


def is_empty(queue):
    return len(queue) == 0


def child_node(problem, parent, action):
    new_state = problem.result(parent.state, action)
    cost = parent.path_cost + problem.action_cost(parent.state, action, new_state)
    child = Node(
        state=new_state,
        parent=parent,
        action=action,
        path_cost=cost
    )
    return child


def solution(node):
    path = []
    actions = []
    curr = node
    while curr is not None:
        path.append(curr.state)
        if curr.parent is not None:     # node gốc không có hành động
            actions.append(curr.action)
        curr = curr.parent
    path.reverse()
    actions.reverse()
    return path, actions


class Problem:
    def __init__(self, initial_state, goal_condition, actions, result, action_cost=None):
        self.initial_state = initial_state
        self.goal_condition = goal_condition
        self._actions_fn = actions
        self._result_fn = result
        self._action_cost_fn = action_cost

    def is_goal(self, state):
        return is_goal(state, self.goal_condition)

    def actions(self, state):
        return self._actions_fn(state)

    def result(self, state, action):
        return self._result_fn(state, action)

    def action_cost(self, state, action, new_state):
        if self._action_cost_fn is None:
            return 1                    # mặc định mỗi hành động có chi phí 1
        return self._action_cost_fn(state, action, new_state)   # phải không âm


def find_in_frontier(frontier, state):
    for i, node in enumerate(frontier):
        if node.state == state:
            return i
    return None


def UCS(problem):
    node = Node(problem.initial_state, path_cost=0)
    frontier = PriorityQueue()
    enqueue(frontier, node)
    explored = set()

    while not is_empty(frontier):
        node = dequeue(frontier)
        if problem.is_goal(node.state):
            path, actions = solution(node)
            return {
                "path": path,
                "actions": actions,
                "cost": node.path_cost,
                "goal_node": node
            }

        explored.add(node.state)
        for action in problem.actions(node.state):
            child = child_node(problem, node, action)
            index = find_in_frontier(frontier, child.state)
            if child.state not in explored and index is None:
                enqueue(frontier, child)
            elif index is not None and frontier[index].path_cost > child.path_cost:
                frontier[index] = child
                heapq.heapify(frontier)

    return None
