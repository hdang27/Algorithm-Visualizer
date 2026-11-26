class Node:
    def __init__(self, state, parent=None, action=None):
        self.state = state
        self.parent = parent
        self.action = action


def is_goal(state, goal_condition):
    if callable(goal_condition):
        return goal_condition(state)
    return state == goal_condition


def Stack():
    stack = []
    return stack


def push(stack, node):
    stack.append(node)


def pop(stack):
    if is_empty(stack):
        return None
    return stack.pop()


def is_empty(stack):
    return len(stack) == 0


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


def depth(node):
    d = 0
    while node.parent is not None:
        d += 1
        node = node.parent
    return d


def DFS(problem, max_depth=None):
    frontier = Stack()
    push(frontier, Node(problem.initial_state))
    explored = {}   # state -> độ sâu nông nhất mà trạng thái này đã được mở rộng

    while not is_empty(frontier):
        node = pop(frontier)
        if problem.is_goal(node.state):
            return {
                "path": solution(node),
                "goal_node": node
            }

        d = depth(node)
        if max_depth is not None and d >= max_depth:
            continue        # chạm giới hạn độ sâu -> không mở rộng tiếp
        if node.state in explored and explored[node.state] <= d:
            continue        # đã mở rộng trạng thái này ở độ sâu nông hơn
        explored[node.state] = d

        for action in problem.actions(node.state):
            child = child_node(problem, node, action)
            # Khi có giới hạn độ sâu, cho phép thăm lại trạng thái nếu gặp lại ở độ sâu nông hơn 
            if child.state not in explored or (
                    max_depth is not None and explored[child.state] > d + 1):
                push(frontier, child)

    return None
