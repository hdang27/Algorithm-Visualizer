class Node:
    def __init__(self, state, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action


def is_goal(state, goal_condition):
    if callable(goal_condition):
        return goal_condition(state)
    return state == goal_condition


def Queue():
    queue = []
    return queue


def enqueue(queue, node):
    queue.append(node)


def dequeue(queue):
    if is_empty(queue):
        return None
    node = queue[0]
    queue.pop(0)
    return node


def is_empty(queue):
    if len(queue) == 0:
        return True
    else:
        return False


def child_node(problem, parent, action):
    new_state = problem.result(parent.state, action)
    child = Node(
        state=new_state,
        parent=parent,
        action=action
    )
    return child


def solution(node):
    path = []
    curr = node
    while curr is not None:
        path.append(curr.state)
        curr = curr.parent
    path.reverse()
    return path


class Problem:
    def __init__(self, initial_state, goal_condition, actions, result):
        self.initial_state = initial_state
        self.goal_condition = goal_condition
        self._actions_fn = actions
        self._result_fn = result

    def is_goal(self, state):
        return is_goal(state, self.goal_condition)

    def actions(self, state):
        return self._actions_fn(state)

    def result(self, state, action):
        return self._result_fn(state, action)


def BFS(problem):
    node = Node(problem.initial_state)

    if problem.is_goal(node.state):
        return {
            "path": solution(node),
            "goal_node": node
        }

    frontier = Queue()
    enqueue(frontier, node)
    explored = set()

    while not is_empty(frontier):
        node = dequeue(frontier)
        explored.add(node.state)

        for action in problem.actions(node.state):
            child = child_node(problem, node, action)
            if child.state not in explored and child not in frontier:
                if problem.is_goal(child.state):
                    return {
                        "path": solution(child),
                        "goal_node": child
                    }
                enqueue(frontier, child)

    return None
