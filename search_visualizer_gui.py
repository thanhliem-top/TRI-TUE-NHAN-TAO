
import os
import time
import heapq
import random
import threading
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from collections import deque
import ttkbootstrap as tb
from ttkbootstrap.constants import *

# Giới hạn số lượng node sinh ra tối đa để tránh treo máy
MAX_NODES = 50000

STANDARD_SEARCH_ALGORITHMS = [
    "BFS",
    "DFS",
    "IDS",
    "UCS",
    "A*",
    "Simple Hill Climbing",
    "Steepest Ascent Hill Climbing",
    "Stochastic Hill Climbing",
    "Random Restart Hill Climbing",
    "Local Beam Search",
]

CSP_ALGORITHMS = [
    "CSP: Path Consistency",
    "CSP: Global Constraints",
    "CSP: Backtracking Search",
    "CSP: Forward Checking",
    "CSP: AC-3",
    "CSP: Min-Conflicts",
]

COMPLEX_ENV_ALGORITHMS = [
    "Complex Env: AND-OR Search",
    "Complex Env: No Observation",
    "Complex Env: Partial Observation",
]

ALGORITHM_CHOICES = (
    STANDARD_SEARCH_ALGORITHMS
    + CSP_ALGORITHMS
    + COMPLEX_ENV_ALGORITHMS
)

# =============================================================================
# CẤU TRÚC DỮ LIỆU CHÍNH & THUẬT TOÁN (TƯƠNG TỰ BẢN CONSOLE)
# =============================================================================

class SearchNode:
    """Đại diện cho một nút trong cây tìm kiếm."""
    def __init__(self, state, parent=None, parent_id=None, move=None, depth=0, cost=0, node_id="", gen_order=0, h=0, f=0):
        self.state = state          # Trạng thái bàn cờ dạng tuple 9 phần tử
        self.parent = parent        # Con trỏ tham chiếu đến nút cha
        self.parent_id = parent_id  # Tên định danh của nút cha
        self.move = move            # Hướng di chuyển từ cha (L, R, U, D)
        self.depth = depth          # Độ sâu của nút
        self.cost = cost            # Tổng chi phí g(n) từ Start
        self.id = node_id           # Tên duy nhất (A, B, C, ..., Z, N27, N28, ...)
        self.gen_order = gen_order  # Thứ tự sinh ra để sắp xếp khi chi phí bằng nhau
        self.h = h                  # Heuristic cost h(n)
        self.f = f                  # Total cost f(n) = g(n) + h(n)

class SearchStep:
    """Lưu lại ảnh chụp thông tin tại mỗi bước tìm kiếm để mô phỏng."""
    def __init__(self, step, current_node, frontier, explored, generated_children, note=""):
        self.step = step
        self.current_node = current_node          # Nút hiện tại đang được xét
        self.frontier = frontier                  # Danh sách các nút trong Frontier
        self.explored = explored                  # Danh sách các nút trong Explored
        self.generated_children = generated_children  # Các nút con vừa được tạo ra ở bước này
        self.note = note                          # Ghi chú phụ (ví dụ: "IDS LIMIT = 1")

class SearchResult:
    """Chứa kết quả cuối cùng của thuật toán tìm kiếm."""
    def __init__(self, success, algorithm, steps, solution_path, moves, total_cost, total_steps,
                 expanded_nodes, generated_nodes, max_frontier_size, time_taken, message=""):
        self.success = success
        self.algorithm = algorithm
        self.steps = steps                       # Danh sách toàn bộ các SearchStep
        self.solution_path = solution_path       # Đường đi từ Start -> Goal (list SearchNode)
        self.moves = moves                       # Danh sách các bước di chuyển (L, R, U, D)
        self.total_cost = total_cost             # Tổng chi phí đường đi
        self.total_steps = total_steps           # Số bước đi
        self.expanded_nodes = expanded_nodes     # Số nút đã duyệt (đã lấy ra xét)
        self.generated_nodes = generated_nodes   # Số nút đã sinh ra (đã được đặt tên)
        self.max_frontier_size = max_frontier_size  # Kích thước frontier lớn nhất
        self.time_taken = time_taken             # Thời gian chạy thuật toán
        self.message = message                   # Thông báo lỗi nếu thất bại

# Tự động sinh tên cho node (A, B, ..., Z, N27, N28, ...)
def get_node_name(index):
    if index < 26:
        return chr(65 + index)
    else:
        return f"N{index + 1}"

class NodeNameGenerator:
    """Bộ tạo tên nút duy nhất cho từng trạng thái trong suốt quá trình chạy thuật toán."""
    def __init__(self):
        self.state_to_id = {}
        self.count = 0

    def get_or_create(self, state):
        if state not in self.state_to_id:
            self.state_to_id[state] = get_node_name(self.count)
            self.count += 1
        return self.state_to_id[state]

# HÀM BỔ TRỢ XỬ LÝ TRẠNG THÁI & HIỂN THỊ
def parse_state(input_text):
    """Chuyển đổi chuỗi nhập của người dùng thành tuple 9 số."""
    cleaned = input_text.replace(",", " ").strip()
    parts = cleaned.split()
    try:
        state = tuple(int(x) for x in parts)
        return state
    except ValueError:
        return None

def validate_state(state):
    """Kiểm tra xem trạng thái bàn cờ có hợp lệ không."""
    if len(state) != 9:
        return False, "Trạng thái phải gồm đúng 9 số."
    if set(state) != set(range(9)):
        return False, "Trạng thái phải chứa đầy đủ các số từ 0 đến 8 không trùng lặp."
    return True, ""

def get_inversions(state):
    """Tính số lượng cặp nghịch thế để kiểm tra tính giải được."""
    nums = [x for x in state if x != 0]
    inv = 0
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] > nums[j]:
                inv += 1
    return inv

def is_solvable(start, goal):
    """Kiểm tra xem câu đố có giải được không bằng inversion parity."""
    return get_inversions(start) % 2 == get_inversions(goal) % 2

def get_neighbors(state, move_order=('L', 'R', 'U', 'D')):
    """Sinh các trạng thái con khi di chuyển ô trống (số 0)."""
    blank_idx = state.index(0)
    r = blank_idx // 3
    c = blank_idx % 3
    neighbors = []

    for move in move_order:
        new_r, new_c = r, c
        if move == 'L':
            new_c -= 1
        elif move == 'R':
            new_c += 1
        elif move == 'U':
            new_r -= 1
        elif move == 'D':
            new_r += 1

        if 0 <= new_r < 3 and 0 <= new_c < 3:
            new_idx = new_r * 3 + new_c
            moved_tile = state[new_idx]
            lst = list(state)
            lst[blank_idx], lst[new_idx] = lst[new_idx], lst[blank_idx]
            next_state = tuple(lst)
            neighbors.append((move, next_state, moved_tile))

    return neighbors

# =============================================================================
# THUẬT TOÁN TÌM KIẾM
# =============================================================================

def run_bfs(start, goal, move_order=('L', 'R', 'U', 'D')):
    """Thuật toán tìm kiếm theo chiều rộng (BFS)."""
    name_gen = NodeNameGenerator()
    start_name = name_gen.get_or_create(start)
    start_node = SearchNode(
        state=start, parent=None, parent_id=None, move=None,
        depth=0, cost=0, node_id=start_name, gen_order=0
    )

    frontier = deque([start_node])
    frontier_states = {start}
    explored = []
    explored_states = set()

    steps = []
    step_num = 0
    max_frontier_size = 1
    generated_count = 1

    while frontier:
        max_frontier_size = max(max_frontier_size, len(frontier))
        current_node = frontier.popleft()
        frontier_states.discard(current_node.state)

        # Dừng khi Goal được pop ra để xét
        if current_node.state == goal:
            explored.append(current_node)
            explored_states.add(current_node.state)

            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=list(frontier),
                explored=list(explored),
                generated_children=[]
            ))

            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()

            moves = [n.move for n in path if n.move is not None]

            return SearchResult(
                success=True, algorithm="BFS", steps=steps, solution_path=path, moves=moves,
                total_cost=current_node.cost, total_steps=len(moves), expanded_nodes=len(explored),
                generated_nodes=name_gen.count, max_frontier_size=max_frontier_size, time_taken=0.0
            )

        explored.append(current_node)
        explored_states.add(current_node.state)

        children = []
        neighbors = get_neighbors(current_node.state, move_order)
        for move, next_state, moved_tile in neighbors:
            if next_state not in explored_states and next_state not in frontier_states:
                if name_gen.count >= MAX_NODES:
                    return SearchResult(
                        success=False, algorithm="BFS", steps=steps, solution_path=[], moves=[],
                        total_cost=0, total_steps=0, expanded_nodes=len(explored),
                        generated_nodes=name_gen.count, max_frontier_size=max_frontier_size,
                        time_taken=0.0, message="Search stopped because node limit was reached."
                    )

                child_name = name_gen.get_or_create(next_state)
                generated_count += 1
                child_node = SearchNode(
                    state=next_state, parent=current_node, parent_id=current_node.id, move=move,
                    depth=current_node.depth + 1, cost=current_node.cost + 1, node_id=child_name,
                    gen_order=generated_count
                )
                frontier.append(child_node)
                frontier_states.add(next_state)
                children.append(child_node)

        steps.append(SearchStep(
            step=step_num,
            current_node=current_node,
            frontier=list(frontier),
            explored=list(explored),
            generated_children=children
        ))
        step_num += 1

    return SearchResult(
        success=False, algorithm="BFS", steps=steps, solution_path=[], moves=[],
        total_cost=0, total_steps=0, expanded_nodes=len(explored),
        generated_nodes=name_gen.count, max_frontier_size=max_frontier_size,
        time_taken=0.0, message="No solution found."
    )

def run_dfs(start, goal, move_order=('L', 'R', 'U', 'D'), depth_limit=20):
    """Thuật toán tìm kiếm theo chiều sâu (DFS) giới hạn độ sâu."""
    name_gen = NodeNameGenerator()
    start_name = name_gen.get_or_create(start)
    start_node = SearchNode(
        state=start, parent=None, parent_id=None, move=None,
        depth=0, cost=0, node_id=start_name, gen_order=0
    )

    frontier = [start_node]
    frontier_states = {start}
    explored = []
    explored_states = set()

    steps = []
    step_num = 0
    max_frontier_size = 1
    generated_count = 1

    while frontier:
        max_frontier_size = max(max_frontier_size, len(frontier))
        current_node = frontier.pop()
        frontier_states.discard(current_node.state)

        if current_node.state == goal:
            explored.append(current_node)
            explored_states.add(current_node.state)

            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=list(frontier),
                explored=list(explored),
                generated_children=[]
            ))

            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()

            moves = [n.move for n in path if n.move is not None]

            return SearchResult(
                success=True, algorithm="DFS", steps=steps, solution_path=path, moves=moves,
                total_cost=current_node.cost, total_steps=len(moves), expanded_nodes=len(explored),
                generated_nodes=name_gen.count, max_frontier_size=max_frontier_size, time_taken=0.0
            )

        explored.append(current_node)
        explored_states.add(current_node.state)

        children = []
        if current_node.depth < depth_limit:
            neighbors = get_neighbors(current_node.state, move_order)
            reversed_neighbors = list(reversed(neighbors))

            for move, next_state, moved_tile in reversed_neighbors:
                ancestor = current_node
                is_ancestor = False
                while ancestor:
                    if ancestor.state == next_state:
                        is_ancestor = True
                        break
                    ancestor = ancestor.parent

                if not is_ancestor and next_state not in explored_states:
                    if name_gen.count >= MAX_NODES:
                        return SearchResult(
                            success=False, algorithm="DFS", steps=steps, solution_path=[], moves=[],
                            total_cost=0, total_steps=0, expanded_nodes=len(explored),
                            generated_nodes=name_gen.count, max_frontier_size=max_frontier_size,
                            time_taken=0.0, message="Search stopped because node limit was reached."
                        )

                    child_name = name_gen.get_or_create(next_state)
                    generated_count += 1
                    child_node = SearchNode(
                        state=next_state, parent=current_node, parent_id=current_node.id, move=move,
                        depth=current_node.depth + 1, cost=current_node.cost + 1, node_id=child_name,
                        gen_order=generated_count
                    )
                    frontier.append(child_node)
                    frontier_states.add(next_state)
                    children.insert(0, child_node)

        steps.append(SearchStep(
            step=step_num,
            current_node=current_node,
            frontier=list(frontier),
            explored=list(explored),
            generated_children=children
        ))
        step_num += 1

    return SearchResult(
        success=False, algorithm="DFS", steps=steps, solution_path=[], moves=[],
        total_cost=0, total_steps=0, expanded_nodes=len(explored),
        generated_nodes=name_gen.count, max_frontier_size=max_frontier_size,
        time_taken=0.0, message=f"No solution found within depth limit of {depth_limit}."
    )

def run_ids(start, goal, move_order=('L', 'R', 'U', 'D'), max_depth=20):
    """Thuật toán tìm kiếm sâu dần (IDS)."""
    global_steps = []
    name_gen = NodeNameGenerator()
    max_frontier_size = 0
    total_expanded = 0
    generated_count = 0

    for limit in range(max_depth + 1):
        start_name = name_gen.get_or_create(start)
        start_node = SearchNode(
            state=start, parent=None, parent_id=None, move=None,
            depth=0, cost=0, node_id=start_name, gen_order=0
        )

        frontier = [start_node]
        explored = []
        explored_states = set()

        while frontier:
            max_frontier_size = max(max_frontier_size, len(frontier))
            current_node = frontier.pop()

            note_str = f"IDS LIMIT = {limit}"

            if current_node.state == goal:
                explored.append(current_node)
                explored_states.add(current_node.state)

                global_steps.append(SearchStep(
                    step=len(global_steps),
                    current_node=current_node,
                    frontier=list(frontier),
                    explored=list(explored),
                    generated_children=[],
                    note=note_str
                ))

                path = []
                curr = current_node
                while curr:
                    path.append(curr)
                    curr = curr.parent
                path.reverse()

                moves = [n.move for n in path if n.move is not None]
                total_expanded += len(explored)

                return SearchResult(
                    success=True, algorithm="IDS", steps=global_steps, solution_path=path, moves=moves,
                    total_cost=current_node.cost, total_steps=len(moves), expanded_nodes=total_expanded,
                    generated_nodes=name_gen.count, max_frontier_size=max_frontier_size,
                    time_taken=0.0, message=f"Goal found at limit = {limit}."
                )

            explored.append(current_node)
            explored_states.add(current_node.state)

            children = []
            if current_node.depth < limit:
                neighbors = get_neighbors(current_node.state, move_order)
                reversed_neighbors = list(reversed(neighbors))

                for move, next_state, moved_tile in reversed_neighbors:
                    ancestor = current_node
                    is_ancestor = False
                    while ancestor:
                        if ancestor.state == next_state:
                            is_ancestor = True
                            break
                        ancestor = ancestor.parent

                    if not is_ancestor and next_state not in explored_states:
                        if name_gen.count >= MAX_NODES:
                            return SearchResult(
                                success=False, algorithm="IDS", steps=global_steps, solution_path=[],
                                moves=[], total_cost=0, total_steps=0, expanded_nodes=total_expanded + len(explored),
                                generated_nodes=name_gen.count, max_frontier_size=max_frontier_size,
                                time_taken=0.0, message="Search stopped because node limit was reached."
                            )

                        child_name = name_gen.get_or_create(next_state)
                        generated_count += 1
                        child_node = SearchNode(
                            state=next_state, parent=current_node, parent_id=current_node.id, move=move,
                            depth=current_node.depth + 1, cost=current_node.cost + 1, node_id=child_name,
                            gen_order=generated_count
                        )
                        frontier.append(child_node)
                        children.insert(0, child_node)

            global_steps.append(SearchStep(
                step=len(global_steps),
                current_node=current_node,
                frontier=list(frontier),
                explored=list(explored),
                generated_children=children,
                note=note_str
            ))

        total_expanded += len(explored)

    return SearchResult(
        success=False, algorithm="IDS", steps=global_steps, solution_path=[], moves=[],
        total_cost=0, total_steps=0, expanded_nodes=total_expanded,
        generated_nodes=name_gen.count, max_frontier_size=max_frontier_size,
        time_taken=0.0, message=f"No solution found within max depth limit of {max_depth}."
    )

def run_ucs(start, goal, move_order=('L', 'R', 'U', 'D'), cost_mode=1):
    """Thuật toán tìm kiếm chi phí đồng nhất (UCS)."""
    name_gen = NodeNameGenerator()
    start_name = name_gen.get_or_create(start)
    start_node = SearchNode(
        state=start, parent=None, parent_id=None, move=None,
        depth=0, cost=0, node_id=start_name, gen_order=0
    )

    pq = []
    heapq.heappush(pq, (0, 0, start_node))

    best_costs = {start: 0}
    explored = []
    explored_states = set()

    steps = []
    step_num = 0
    max_frontier_size = 1
    generated_count = 0

    while pq:
        max_frontier_size = max(max_frontier_size, len(pq))
        cost, order, current_node = heapq.heappop(pq)

        if current_node.state in explored_states:
            continue

        # Chỉ dừng khi Goal được pop ra khỏi priority queue
        if current_node.state == goal:
            explored.append(current_node)
            explored_states.add(current_node.state)

            sorted_pq_nodes = [item[2] for item in sorted(pq, key=lambda x: (x[0], x[1]))]

            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=sorted_pq_nodes,
                explored=list(explored),
                generated_children=[]
            ))

            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()

            moves = [n.move for n in path if n.move is not None]

            return SearchResult(
                success=True, algorithm="UCS", steps=steps, solution_path=path, moves=moves,
                total_cost=current_node.cost, total_steps=len(moves), expanded_nodes=len(explored),
                generated_nodes=name_gen.count, max_frontier_size=max_frontier_size, time_taken=0.0
            )

        explored.append(current_node)
        explored_states.add(current_node.state)

        children = []
        neighbors = get_neighbors(current_node.state, move_order)
        for move, next_state, moved_tile in neighbors:
            step_cost = 1 if cost_mode == 1 else moved_tile
            next_cost = current_node.cost + step_cost

            if next_state not in explored_states:
                if next_state not in best_costs or next_cost < best_costs[next_state]:
                    if name_gen.count >= MAX_NODES:
                        return SearchResult(
                            success=False, algorithm="UCS", steps=steps, solution_path=[], moves=[],
                            total_cost=0, total_steps=0, expanded_nodes=len(explored),
                            generated_nodes=name_gen.count, max_frontier_size=max_frontier_size,
                            time_taken=0.0, message="Search stopped because node limit was reached."
                        )

                    best_costs[next_state] = next_cost
                    child_name = name_gen.get_or_create(next_state)
                    generated_count += 1
                    child_node = SearchNode(
                        state=next_state, parent=current_node, parent_id=current_node.id, move=move,
                        depth=current_node.depth + 1, cost=next_cost, node_id=child_name,
                        gen_order=generated_count
                    )
                    heapq.heappush(pq, (next_cost, generated_count, child_node))
                    children.append(child_node)

        sorted_pq_nodes = [item[2] for item in sorted(pq, key=lambda x: (x[0], x[1]))]

        steps.append(SearchStep(
            step=step_num,
            current_node=current_node,
            frontier=sorted_pq_nodes,
            explored=list(explored),
            generated_children=children
        ))
        step_num += 1

    return SearchResult(
        success=False, algorithm="UCS", steps=steps, solution_path=[], moves=[],
        total_cost=0, total_steps=0, expanded_nodes=len(explored),
        generated_nodes=name_gen.count, max_frontier_size=max_frontier_size,
        time_taken=0.0, message="No solution found."
    )

def run_astar(start, goal, move_order=('L', 'R', 'U', 'D'), cost_mode=1, heuristic_mode=1):
    """
    Thuật toán tìm kiếm A* (A-star).
    - Dùng heapq.
    - Sắp xếp ưu tiên: 1. Tổng cost f(n) = g(n) + h(n), 2. Thứ tự sinh nút (gen_order).
    - g(n) = tổng cost từ Start đến node hiện tại.
    - h(n) = heuristic từ node hiện tại đến Goal.
    - Cost mode:
      + 1: Step cost = 1
      + 2: Moved tile cost (bằng giá trị số ô tráo đổi với ô trống)
    - Heuristic mode:
      + 1: Manhattan Distance
      + 2: Misplaced Tiles
    """
    def calc_h(state):
        if heuristic_mode == 1:
            dist = 0
            goal_pos = {val: idx for idx, val in enumerate(goal)}
            for idx, val in enumerate(state):
                if val != 0:
                    curr_r, curr_c = idx // 3, idx % 3
                    g_idx = goal_pos[val]
                    goal_r, goal_c = g_idx // 3, g_idx % 3
                    dist += abs(curr_r - goal_r) + abs(curr_c - goal_c)
            return dist
        else:
            count = 0
            for idx, val in enumerate(state):
                if val != 0 and val != goal[idx]:
                    count += 1
            return count

    name_gen = NodeNameGenerator()
    start_name = name_gen.get_or_create(start)
    h0 = calc_h(start)
    start_node = SearchNode(
        state=start, parent=None, parent_id=None, move=None,
        depth=0, cost=0, node_id=start_name, gen_order=0, h=h0, f=h0
    )

    pq = []
    heapq.heappush(pq, (h0, 0, start_node))

    best_costs = {start: 0}
    explored = []
    explored_states = set()

    steps = []
    step_num = 0
    max_frontier_size = 1
    generated_count = 0

    while pq:
        max_frontier_size = max(max_frontier_size, len(pq))
        f_val, order, current_node = heapq.heappop(pq)

        if current_node.state in explored_states:
            continue

        if current_node.state == goal:
            explored.append(current_node)
            explored_states.add(current_node.state)

            sorted_pq_nodes = [item[2] for item in sorted(pq, key=lambda x: (x[0], x[1]))]

            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=sorted_pq_nodes,
                explored=list(explored),
                generated_children=[]
            ))

            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()

            moves = [n.move for n in path if n.move is not None]
            h_name = "Manhattan" if heuristic_mode == 1 else "Misplaced Tiles"
            c_mode_name = "Step cost=1" if cost_mode == 1 else "Moved tile cost"

            return SearchResult(
                success=True,
                algorithm=f"A* ({h_name}, {c_mode_name})",
                steps=steps,
                solution_path=path,
                moves=moves,
                total_cost=current_node.cost,
                total_steps=len(moves),
                expanded_nodes=len(explored),
                generated_nodes=name_gen.count,
                max_frontier_size=max_frontier_size,
                time_taken=0.0
            )

        explored.append(current_node)
        explored_states.add(current_node.state)

        children = []
        neighbors = get_neighbors(current_node.state, move_order)
        for move, next_state, moved_tile in neighbors:
            step_cost = 1 if cost_mode == 1 else moved_tile
            next_g = current_node.cost + step_cost

            if next_state not in explored_states:
                if next_state not in best_costs or next_g < best_costs[next_state]:
                    if name_gen.count >= MAX_NODES:
                        h_name = "Manhattan" if heuristic_mode == 1 else "Misplaced Tiles"
                        c_mode_name = "Step cost=1" if cost_mode == 1 else "Moved tile cost"
                        return SearchResult(
                            success=False,
                            algorithm=f"A* ({h_name}, {c_mode_name})",
                            steps=steps,
                            solution_path=[],
                            moves=[],
                            total_cost=0,
                            total_steps=0,
                            expanded_nodes=len(explored),
                            generated_nodes=name_gen.count,
                            max_frontier_size=max_frontier_size,
                            time_taken=0.0,
                            message="Search stopped because node limit was reached."
                        )

                    best_costs[next_state] = next_g
                    child_name = name_gen.get_or_create(next_state)
                    generated_count += 1
                    child_h = calc_h(next_state)
                    child_f = next_g + child_h
                    child_node = SearchNode(
                        state=next_state,
                        parent=current_node,
                        parent_id=current_node.id,
                        move=move,
                        depth=current_node.depth + 1,
                        cost=next_g,
                        node_id=child_name,
                        gen_order=generated_count,
                        h=child_h,
                        f=child_f
                    )
                    heapq.heappush(pq, (child_f, generated_count, child_node))
                    children.append(child_node)

        sorted_pq_nodes = [item[2] for item in sorted(pq, key=lambda x: (x[0], x[1]))]

        steps.append(SearchStep(
            step=step_num,
            current_node=current_node,
            frontier=sorted_pq_nodes,
            explored=list(explored),
            generated_children=children
        ))
        step_num += 1

    h_name = "Manhattan" if heuristic_mode == 1 else "Misplaced Tiles"
    c_mode_name = "Step cost=1" if cost_mode == 1 else "Moved tile cost"
    return SearchResult(
        success=False,
        algorithm=f"A* ({h_name}, {c_mode_name})",
        steps=steps,
        solution_path=[],
        moves=[],
        total_cost=0,
        total_steps=0,
        expanded_nodes=len(explored),
        generated_nodes=name_gen.count,
        max_frontier_size=max_frontier_size,
        time_taken=0.0,
        message="No solution found."
    )

def run_simple_hill_climbing(start, goal, move_order=('L', 'R', 'U', 'D'), heuristic_mode=1, max_iterations=100):
    """
    Thuật toán tìm kiếm Leo đồi Đơn giản (Simple Hill Climbing).
    - h(n): Manhattan hoặc Misplaced.
    - Chọn trạng thái lân cận đầu tiên có h nhỏ hơn.
    """
    def calc_h(state):
        if heuristic_mode == 1:
            dist = 0
            goal_pos = {val: idx for idx, val in enumerate(goal)}
            for idx, val in enumerate(state):
                if val != 0:
                    curr_r, curr_c = idx // 3, idx % 3
                    g_idx = goal_pos[val]
                    goal_r, goal_c = g_idx // 3, g_idx % 3
                    dist += abs(curr_r - goal_r) + abs(curr_c - goal_c)
            return dist
        else:
            return sum(1 for idx, val in enumerate(state) if val != 0 and val != goal[idx])

    name_gen = NodeNameGenerator()
    start_name = name_gen.get_or_create(start)
    h0 = calc_h(start)
    start_node = SearchNode(
        state=start, parent=None, parent_id=None, move=None,
        depth=0, cost=0, node_id=start_name, gen_order=0, h=h0, f=h0
    )

    steps = []
    step_num = 0
    explored = []
    explored_states = set()

    current_node = start_node
    generated_count = 1
    iteration = 0

    while iteration < max_iterations:
        explored.append(current_node)
        explored_states.add(current_node.state)

        if current_node.state == goal:
            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=[],
                explored=list(explored),
                generated_children=[],
                note="Goal reached!"
            ))

            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()
            moves = [n.move for n in path if n.move is not None]

            return SearchResult(
                success=True,
                algorithm=f"Simple Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
                steps=steps,
                solution_path=path,
                moves=moves,
                total_cost=current_node.cost,
                total_steps=len(moves),
                expanded_nodes=len(explored),
                generated_nodes=name_gen.count,
                max_frontier_size=0,
                time_taken=0.0
            )

        neighbors = get_neighbors(current_node.state, move_order)
        children = []
        next_node = None

        for move, next_state, moved_tile in neighbors:
            if name_gen.count >= MAX_NODES:
                return SearchResult(
                    success=False,
                    algorithm=f"Simple Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
                    steps=steps,
                    solution_path=[],
                    moves=[],
                    total_cost=0,
                    total_steps=0,
                    expanded_nodes=len(explored),
                    generated_nodes=name_gen.count,
                    max_frontier_size=0,
                    time_taken=0.0,
                    message="Search stopped because node limit was reached."
                )

            child_name = name_gen.get_or_create(next_state)
            generated_count += 1
            child_h = calc_h(next_state)
            child_node = SearchNode(
                state=next_state,
                parent=current_node,
                parent_id=current_node.id,
                move=move,
                depth=current_node.depth + 1,
                cost=current_node.cost + 1,
                node_id=child_name,
                gen_order=generated_count,
                h=child_h,
                f=child_h
            )
            children.append(child_node)

            if child_h < current_node.h:
                next_node = child_node
                break

        if next_node is not None:
            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=[],
                explored=list(explored),
                generated_children=children,
                note=f"Chuyển sang {next_node.id} vì h={next_node.h} < {current_node.h}"
            ))
            current_node = next_node
            step_num += 1
            iteration += 1
        else:
            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=[],
                explored=list(explored),
                generated_children=children,
                note="Dừng vì đã đạt cực đại cục bộ (không có lân cận tốt hơn)"
            ))

            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()
            moves = [n.move for n in path if n.move is not None]

            return SearchResult(
                success=False,
                algorithm=f"Simple Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
                steps=steps,
                solution_path=path,
                moves=moves,
                total_cost=current_node.cost,
                total_steps=len(moves),
                expanded_nodes=len(explored),
                generated_nodes=name_gen.count,
                max_frontier_size=0,
                time_taken=0.0,
                message="Dừng vì đã đạt cực đại cục bộ (Local Maximum) mà chưa đạt đích."
            )

    steps.append(SearchStep(
        step=step_num,
        current_node=current_node,
        frontier=[],
        explored=list(explored),
        generated_children=[],
        note=f"Dừng sau tối đa {max_iterations} vòng lặp"
    ))

    path = []
    curr = current_node
    while curr:
        path.append(curr)
        curr = curr.parent
    path.reverse()
    moves = [n.move for n in path if n.move is not None]

    return SearchResult(
        success=False,
        algorithm=f"Simple Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
        steps=steps,
        solution_path=path,
        moves=moves,
        total_cost=current_node.cost,
        total_steps=len(moves),
        expanded_nodes=len(explored),
        generated_nodes=name_gen.count,
        max_frontier_size=0,
        time_taken=0.0,
        message="Dừng sau số vòng lặp tối đa."
    )


def run_steepest_ascent_hill_climbing(start, goal, move_order=('L', 'R', 'U', 'D'), heuristic_mode=1, max_iterations=100):
    """Thuật toán Leo đồi Dốc nhất (Steepest Ascent Hill Climbing)."""
    def calc_h(state):
        if heuristic_mode == 1:
            dist = 0
            goal_pos = {val: idx for idx, val in enumerate(goal)}
            for idx, val in enumerate(state):
                if val != 0:
                    curr_r, curr_c = idx // 3, idx % 3
                    g_idx = goal_pos[val]
                    goal_r, goal_c = g_idx // 3, g_idx % 3
                    dist += abs(curr_r - goal_r) + abs(curr_c - goal_c)
            return dist
        else:
            return sum(1 for idx, val in enumerate(state) if val != 0 and val != goal[idx])

    name_gen = NodeNameGenerator()
    start_name = name_gen.get_or_create(start)
    h0 = calc_h(start)
    start_node = SearchNode(
        state=start, parent=None, parent_id=None, move=None,
        depth=0, cost=0, node_id=start_name, gen_order=0, h=h0, f=h0
    )

    steps = []
    step_num = 0
    explored = []
    explored_states = set()

    current_node = start_node
    generated_count = 1
    iteration = 0

    while iteration < max_iterations:
        explored.append(current_node)
        explored_states.add(current_node.state)

        if current_node.state == goal:
            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=[],
                explored=list(explored),
                generated_children=[],
                note="Goal reached!"
            ))
            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()
            moves = [n.move for n in path if n.move is not None]
            return SearchResult(
                success=True,
                algorithm=f"Steepest Ascent Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
                steps=steps,
                solution_path=path,
                moves=moves,
                total_cost=current_node.cost,
                total_steps=len(moves),
                expanded_nodes=len(explored),
                generated_nodes=name_gen.count,
                max_frontier_size=0,
                time_taken=0.0
            )

        neighbors = get_neighbors(current_node.state, move_order)
        children = []
        better_nodes = []

        for move, next_state, moved_tile in neighbors:
            if name_gen.count >= MAX_NODES:
                return SearchResult(
                    success=False,
                    algorithm=f"Steepest Ascent Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
                    steps=steps,
                    solution_path=[],
                    moves=[],
                    total_cost=0,
                    total_steps=0,
                    expanded_nodes=len(explored),
                    generated_nodes=name_gen.count,
                    max_frontier_size=0,
                    time_taken=0.0,
                    message="Search stopped because node limit was reached."
                )

            child_name = name_gen.get_or_create(next_state)
            generated_count += 1
            child_h = calc_h(next_state)
            child_node = SearchNode(
                state=next_state,
                parent=current_node,
                parent_id=current_node.id,
                move=move,
                depth=current_node.depth + 1,
                cost=current_node.cost + 1,
                node_id=child_name,
                gen_order=generated_count,
                h=child_h,
                f=child_h
            )
            children.append(child_node)
            if child_h < current_node.h:
                better_nodes.append(child_node)

        if better_nodes:
            next_node = min(better_nodes, key=lambda node: (node.h, node.cost, node.gen_order))
            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=better_nodes,
                explored=list(explored),
                generated_children=children,
                note=f"Chuyển sang {next_node.id} vì h={next_node.h} tốt nhất"
            ))
            current_node = next_node
            step_num += 1
            iteration += 1
        else:
            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=better_nodes,
                explored=list(explored),
                generated_children=children,
                note="Dừng vì đã đạt cực đại cục bộ (không có lân cận tốt nhất tốt hơn)"
            ))
            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()
            moves = [n.move for n in path if n.move is not None]
            return SearchResult(
                success=False,
                algorithm=f"Steepest Ascent Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
                steps=steps,
                solution_path=path,
                moves=moves,
                total_cost=current_node.cost,
                total_steps=len(moves),
                expanded_nodes=len(explored),
                generated_nodes=name_gen.count,
                max_frontier_size=0,
                time_taken=0.0,
                message="Dừng vì đã đạt cực đại cục bộ (Local Maximum) mà chưa đạt đích."
            )

    steps.append(SearchStep(
        step=step_num,
        current_node=current_node,
        frontier=[],
        explored=list(explored),
        generated_children=[],
        note=f"Dừng sau tối đa {max_iterations} vòng lặp"
    ))
    path = []
    curr = current_node
    while curr:
        path.append(curr)
        curr = curr.parent
    path.reverse()
    moves = [n.move for n in path if n.move is not None]
    return SearchResult(
        success=False,
        algorithm=f"Steepest Ascent Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
        steps=steps,
        solution_path=path,
        moves=moves,
        total_cost=current_node.cost,
        total_steps=len(moves),
        expanded_nodes=len(explored),
        generated_nodes=name_gen.count,
        max_frontier_size=0,
        time_taken=0.0,
        message="Dừng sau số vòng lặp tối đa."
    )


def run_stochastic_hill_climbing(start, goal, move_order=('L', 'R', 'U', 'D'), heuristic_mode=1, max_iterations=100):
    """Thuật toán Leo đồi Ngẫu nhiên (Stochastic Hill Climbing)."""
    def calc_h(state):
        if heuristic_mode == 1:
            dist = 0
            goal_pos = {val: idx for idx, val in enumerate(goal)}
            for idx, val in enumerate(state):
                if val != 0:
                    curr_r, curr_c = idx // 3, idx % 3
                    g_idx = goal_pos[val]
                    goal_r, goal_c = g_idx // 3, g_idx % 3
                    dist += abs(curr_r - goal_r) + abs(curr_c - goal_c)
            return dist
        else:
            return sum(1 for idx, val in enumerate(state) if val != 0 and val != goal[idx])

    name_gen = NodeNameGenerator()
    start_name = name_gen.get_or_create(start)
    h0 = calc_h(start)
    start_node = SearchNode(
        state=start, parent=None, parent_id=None, move=None,
        depth=0, cost=0, node_id=start_name, gen_order=0, h=h0, f=h0
    )

    steps = []
    step_num = 0
    explored = []
    explored_states = set()

    current_node = start_node
    generated_count = 1
    iteration = 0

    while iteration < max_iterations:
        explored.append(current_node)
        explored_states.add(current_node.state)

        if current_node.state == goal:
            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=[],
                explored=list(explored),
                generated_children=[],
                note="Goal reached!"
            ))
            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()
            moves = [n.move for n in path if n.move is not None]
            return SearchResult(
                success=True,
                algorithm=f"Stochastic Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
                steps=steps,
                solution_path=path,
                moves=moves,
                total_cost=current_node.cost,
                total_steps=len(moves),
                expanded_nodes=len(explored),
                generated_nodes=name_gen.count,
                max_frontier_size=0,
                time_taken=0.0
            )

        neighbors = get_neighbors(current_node.state, move_order)
        children = []
        better_nodes = []

        for move, next_state, moved_tile in neighbors:
            if name_gen.count >= MAX_NODES:
                return SearchResult(
                    success=False,
                    algorithm=f"Stochastic Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
                    steps=steps,
                    solution_path=[],
                    moves=[],
                    total_cost=0,
                    total_steps=0,
                    expanded_nodes=len(explored),
                    generated_nodes=name_gen.count,
                    max_frontier_size=0,
                    time_taken=0.0,
                    message="Search stopped because node limit was reached."
                )

            child_name = name_gen.get_or_create(next_state)
            generated_count += 1
            child_h = calc_h(next_state)
            child_node = SearchNode(
                state=next_state,
                parent=current_node,
                parent_id=current_node.id,
                move=move,
                depth=current_node.depth + 1,
                cost=current_node.cost + 1,
                node_id=child_name,
                gen_order=generated_count,
                h=child_h,
                f=child_h
            )
            children.append(child_node)
            if child_h < current_node.h:
                better_nodes.append(child_node)

        if better_nodes:
            next_node = random.choice(better_nodes)
            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=better_nodes,
                explored=list(explored),
                generated_children=children,
                note=f"Chọn ngẫu nhiên {next_node.id} với h={next_node.h}"
            ))
            current_node = next_node
            step_num += 1
            iteration += 1
        else:
            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=better_nodes,
                explored=list(explored),
                generated_children=children,
                note="Dừng vì đã đạt cực đại cục bộ (không có lân cận tốt hơn)"
            ))
            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()
            moves = [n.move for n in path if n.move is not None]
            return SearchResult(
                success=False,
                algorithm=f"Stochastic Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
                steps=steps,
                solution_path=path,
                moves=moves,
                total_cost=current_node.cost,
                total_steps=len(moves),
                expanded_nodes=len(explored),
                generated_nodes=name_gen.count,
                max_frontier_size=0,
                time_taken=0.0,
                message="Dừng vì đã đạt cực đại cục bộ (Local Maximum) mà chưa đạt đích."
            )

    steps.append(SearchStep(
        step=step_num,
        current_node=current_node,
        frontier=[],
        explored=list(explored),
        generated_children=[],
        note=f"Dừng sau tối đa {max_iterations} vòng lặp"
    ))
    path = []
    curr = current_node
    while curr:
        path.append(curr)
        curr = curr.parent
    path.reverse()
    moves = [n.move for n in path if n.move is not None]
    return SearchResult(
        success=False,
        algorithm=f"Stochastic Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
        steps=steps,
        solution_path=path,
        moves=moves,
        total_cost=current_node.cost,
        total_steps=len(moves),
        expanded_nodes=len(explored),
        generated_nodes=name_gen.count,
        max_frontier_size=0,
        time_taken=0.0,
        message="Dừng sau số vòng lặp tối đa."
    )


def run_random_restart_hill_climbing(start, goal, move_order=('L', 'R', 'U', 'D'), heuristic_mode=1, max_iterations=100, restarts=5):
    """Thuật toán Leo đồi với Khởi động lại ngẫu nhiên (Random Restart Hill Climbing)."""
    def calc_h(state):
        if heuristic_mode == 1:
            dist = 0
            goal_pos = {val: idx for idx, val in enumerate(goal)}
            for idx, val in enumerate(state):
                if val != 0:
                    curr_r, curr_c = idx // 3, idx % 3
                    g_idx = goal_pos[val]
                    goal_r, goal_c = g_idx // 3, g_idx % 3
                    dist += abs(curr_r - goal_r) + abs(curr_c - goal_c)
            return dist
        else:
            return sum(1 for idx, val in enumerate(state) if val != 0 and val != goal[idx])

    def random_walk(node, steps=3):
        current = node
        for _ in range(steps):
            neighbors = get_neighbors(current.state, move_order)
            if not neighbors:
                break
            move, next_state, moved_tile = random.choice(neighbors)
            child_name = name_gen.get_or_create(next_state)
            nonlocal generated_count
            generated_count += 1
            child_h = calc_h(next_state)
            child_node = SearchNode(
                state=next_state,
                parent=current,
                parent_id=current.id,
                move=move,
                depth=current.depth + 1,
                cost=current.cost + 1,
                node_id=child_name,
                gen_order=generated_count,
                h=child_h,
                f=child_h
            )
            current = child_node
            explored.append(current)
            explored_states.add(current.state)
        return current

    name_gen = NodeNameGenerator()
    start_name = name_gen.get_or_create(start)
    h0 = calc_h(start)
    start_node = SearchNode(
        state=start, parent=None, parent_id=None, move=None,
        depth=0, cost=0, node_id=start_name, gen_order=0, h=h0, f=h0
    )

    steps = [SearchStep(
        step=0,
        current_node=start_node,
        frontier=[start_node],
        explored=[],
        generated_children=[start_node],
        note=f"Start và Random Restart tối đa={restarts}"
    )]
    step_num = 1
    explored = []
    explored_states = {start}

    current_node = start_node
    generated_count = 1
    restart = 0

    while restart <= restarts:
        iteration = 0
        while iteration < max_iterations:
            if current_node.state == goal:
                steps.append(SearchStep(
                    step=step_num,
                    current_node=current_node,
                    frontier=[],
                    explored=list(explored),
                    generated_children=[],
                    note=f"Goal reached after restart {restart}"
                ))
                path = []
                curr = current_node
                while curr:
                    path.append(curr)
                    curr = curr.parent
                path.reverse()
                moves = [n.move for n in path if n.move is not None]
                return SearchResult(
                    success=True,
                    algorithm=f"Random Restart Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
                    steps=steps,
                    solution_path=path,
                    moves=moves,
                    total_cost=current_node.cost,
                    total_steps=len(moves),
                    expanded_nodes=len(explored),
                    generated_nodes=name_gen.count,
                    max_frontier_size=0,
                    time_taken=0.0
                )

            neighbors = get_neighbors(current_node.state, move_order)
            children = []
            better_nodes = []

            for move, next_state, moved_tile in neighbors:
                if name_gen.count >= MAX_NODES:
                    return SearchResult(
                        success=False,
                        algorithm=f"Random Restart Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
                        steps=steps,
                        solution_path=[],
                        moves=[],
                        total_cost=0,
                        total_steps=0,
                        expanded_nodes=len(explored),
                        generated_nodes=name_gen.count,
                        max_frontier_size=0,
                        time_taken=0.0,
                        message="Search stopped because node limit was reached."
                    )

                child_name = name_gen.get_or_create(next_state)
                generated_count += 1
                child_h = calc_h(next_state)
                child_node = SearchNode(
                    state=next_state,
                    parent=current_node,
                    parent_id=current_node.id,
                    move=move,
                    depth=current_node.depth + 1,
                    cost=current_node.cost + 1,
                    node_id=child_name,
                    gen_order=generated_count,
                    h=child_h,
                    f=child_h
                )
                children.append(child_node)
                if child_h < current_node.h:
                    better_nodes.append(child_node)

            if better_nodes:
                next_node = random.choice(better_nodes)
                steps.append(SearchStep(
                    step=step_num,
                    current_node=current_node,
                    frontier=better_nodes,
                    explored=list(explored),
                    generated_children=children,
                    note=f"Chuyển sang {next_node.id} với h={next_node.h} trong restart {restart}"
                ))
                current_node = next_node
                step_num += 1
                iteration += 1
            else:
                steps.append(SearchStep(
                    step=step_num,
                    current_node=current_node,
                    frontier=better_nodes,
                    explored=list(explored),
                    generated_children=children,
                    note=f"Stuck tại restart {restart}, sẽ khởi động lại ngẫu nhiên"
                ))
                current_node = random_walk(current_node, steps=3)
                step_num += 1
                restart += 1
                break

        if current_node.state == goal:
            break
        if iteration >= max_iterations:
            steps.append(SearchStep(
                step=step_num,
                current_node=current_node,
                frontier=[],
                explored=list(explored),
                generated_children=[],
                note=f"Dừng sau tối đa {max_iterations} vòng lặp tại restart {restart}"
            ))
            step_num += 1
            if restart < restarts:
                current_node = random_walk(current_node, steps=3)
                step_num += 1
                restart += 1
            else:
                break

    if current_node.state == goal:
        path = []
        curr = current_node
        while curr:
            path.append(curr)
            curr = curr.parent
        path.reverse()
        moves = [n.move for n in path if n.move is not None]
        return SearchResult(
            success=True,
            algorithm=f"Random Restart Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
            steps=steps,
            solution_path=path,
            moves=moves,
            total_cost=current_node.cost,
            total_steps=len(moves),
            expanded_nodes=len(explored),
            generated_nodes=name_gen.count,
            max_frontier_size=0,
            time_taken=0.0
        )

    path = []
    curr = current_node
    while curr:
        path.append(curr)
        curr = curr.parent
    path.reverse()
    moves = [n.move for n in path if n.move is not None]
    return SearchResult(
        success=False,
        algorithm=f"Random Restart Hill Climbing ({'Manhattan' if heuristic_mode == 1 else 'Misplaced'})",
        steps=steps,
        solution_path=path,
        moves=moves,
        total_cost=current_node.cost,
        total_steps=len(moves),
        expanded_nodes=len(explored),
        generated_nodes=name_gen.count,
        max_frontier_size=0,
        time_taken=0.0,
        message="Goal not found sau nhiều khởi động lại ngẫu nhiên."
    )


def run_local_beam_search(start, goal, move_order=('L', 'R', 'U', 'D'), beam_width=3, max_iterations=100, heuristic_mode=1):
    """Thuật toán Local Beam Search cho 8-puzzle."""
    def calc_h(state):
        if heuristic_mode == 1:
            dist = 0
            goal_pos = {val: idx for idx, val in enumerate(goal)}
            for idx, val in enumerate(state):
                if val != 0:
                    curr_r, curr_c = idx // 3, idx % 3
                    g_idx = goal_pos[val]
                    goal_r, goal_c = g_idx // 3, g_idx % 3
                    dist += abs(curr_r - goal_r) + abs(curr_c - goal_c)
            return dist
        else:
            return sum(1 for idx, val in enumerate(state) if val != 0 and val != goal[idx])

    name_gen = NodeNameGenerator()
    start_name = name_gen.get_or_create(start)
    h0 = calc_h(start)
    start_node = SearchNode(
        state=start, parent=None, parent_id=None, move=None,
        depth=0, cost=0, node_id=start_name, gen_order=0, h=h0, f=h0
    )

    beam = [start_node]
    explored = []
    explored_states = {start}
    steps = [SearchStep(
        step=0,
        current_node=start_node,
        frontier=list(beam),
        explored=list(explored),
        generated_children=list(beam),
        note=f"Initial beam k={beam_width}"
    )]
    max_frontier_size = len(beam)
    iteration = 0

    while iteration < max_iterations:
        if any(node.state == goal for node in beam):
            break

        successors = []
        for node in beam:
            explored.append(node)
            for move, next_state, moved_tile in get_neighbors(node.state, move_order):
                if next_state in explored_states:
                    continue
                explored_states.add(next_state)

                child_name = name_gen.get_or_create(next_state)
                child_h = calc_h(next_state)
                child_node = SearchNode(
                    state=next_state,
                    parent=node,
                    parent_id=node.id,
                    move=move,
                    depth=node.depth + 1,
                    cost=node.cost + 1,
                    node_id=child_name,
                    gen_order=name_gen.count - 1,
                    h=child_h,
                    f=child_h
                )
                successors.append(child_node)

        if not successors:
            break

        successors.sort(key=lambda n: (n.h, n.cost, n.gen_order))
        beam = successors[:beam_width]
        max_frontier_size = max(max_frontier_size, len(successors))
        iteration += 1

        steps.append(SearchStep(
            step=iteration,
            current_node=beam[0],
            frontier=list(beam),
            explored=list(explored),
            generated_children=list(beam),
            note=f"Beam k={beam_width}, iter={iteration}"
        ))

        if any(node.state == goal for node in beam):
            break

    goal_node = next((node for node in beam if node.state == goal), None)
    if goal_node:
        path = []
        curr = goal_node
        while curr:
            path.append(curr)
            curr = curr.parent
        path.reverse()
        moves = [n.move for n in path if n.move is not None]

        return SearchResult(
            success=True,
            algorithm=f"Local Beam Search (k={beam_width})",
            steps=steps,
            solution_path=path,
            moves=moves,
            total_cost=goal_node.cost,
            total_steps=len(moves),
            expanded_nodes=len(explored),
            generated_nodes=name_gen.count,
            max_frontier_size=max_frontier_size,
            time_taken=0.0
        )

    best_node = beam[0]
    path = []
    curr = best_node
    while curr:
        path.append(curr)
        curr = curr.parent
    path.reverse()
    moves = [n.move for n in path if n.move is not None]

    return SearchResult(
        success=False,
        algorithm=f"Local Beam Search (k={beam_width})",
        steps=steps,
        solution_path=path,
        moves=moves,
        total_cost=best_node.cost,
        total_steps=len(moves),
        expanded_nodes=len(explored),
        generated_nodes=name_gen.count,
        max_frontier_size=max_frontier_size,
        time_taken=0.0,
        message="Goal not found within max iterations."
    )

# =============================================================================
# HÀM ĐỊNH DẠNG TEXT ĐỂ IN LÊN SCROLLABLE TEXT WIDGET
# =============================================================================

def format_node_matrix(node):
    """Trả về chuỗi biểu diễn nút dạng: Tên = (Cha, Hướng, ChiPhí) + ma trận 3x3."""
    if hasattr(node, 'h') and (node.h > 0 or getattr(node, 'f', 0) > 0):
        parent_part = f"({node.parent_id}, {node.move}, g={node.cost}, h={node.h}, f={node.f})" if node.parent_id else f"Start (g=0, h={node.h}, f={node.f})"
    else:
        parent_part = f"({node.parent_id}, {node.move}, {node.cost})" if node.parent_id else "Start"
    header = f"{node.id} = {parent_part}"
    
    rows = []
    for i in range(0, 9, 3):
        rows.append(f"{node.state[i]} {node.state[i+1]} {node.state[i+2]}")
    return header + "\n" + "\n".join(rows)

def format_explored_matrix(node):
    """Trả về chuỗi biểu diễn nút explored dạng: Tên + ma trận 3x3."""
    rows = [node.id]
    for i in range(0, 9, 3):
        rows.append(f"{node.state[i]} {node.state[i+1]} {node.state[i+2]}")
    return "\n".join(rows)

def format_state_matrix(state):
    """Trả về chuỗi biểu diễn trực tiếp 3x3 của trạng thái bàn cờ."""
    rows = []
    for i in range(0, 9, 3):
        rows.append(f"{state[i]} {state[i+1]} {state[i+2]}")
    return "\n".join(rows)


# =============================================================================
# CSP & COMPLEX ENVIRONMENT ALGORITHMS APPLIED TO 8-PUZZLE
# =============================================================================

def reconstruct_path(node):
    path = []
    curr = node
    while curr:
        path.append(curr)
        curr = curr.parent
    path.reverse()
    return path


def run_csp_backtracking_puzzle(start, goal, forward_checking=False, depth_limit=10,
                                move_order=('L', 'R', 'U', 'D')):
    """CSP Backtracking / Forward Checking cho 8-puzzle."""
    name_gen = NodeNameGenerator()
    root = SearchNode(state=start, parent=None, parent_id=None, move=None,
                      depth=0, cost=0, node_id=name_gen.get_or_create(start), gen_order=0)

    steps = []
    explored = []
    node_counter = [1]
    max_fs = 0
    goal_pos = {v: i for i, v in enumerate(goal)}

    def h(state):
        d = 0
        for i, v in enumerate(state):
            if v:
                gr, gc = goal_pos[v] // 3, goal_pos[v] % 3
                d += abs(i // 3 - gr) + abs(i % 3 - gc)
        return d

    def bt(path_nodes, depth):
        nonlocal max_fs
        cur = path_nodes[-1]
        explored.append(cur)
        if cur.state == goal:
            steps.append(SearchStep(len(steps), cur, [], list(explored), [], "Goal reached!"))
            return cur
        if depth >= depth_limit:
            return None
        raw = get_neighbors(cur.state, move_order)
        cands = [(m, s) for m, s, _ in raw if not any(n.state == s for n in path_nodes)]
        if forward_checking:
            rem = depth_limit - depth - 1
            cands = [(m, s) for m, s in cands if h(s) <= rem]
        max_fs = max(max_fs, len(cands))
        children = []
        for move, ns in cands:
            cn = SearchNode(state=ns, parent=cur, parent_id=cur.id, move=move,
                            depth=depth+1, cost=depth+1,
                            node_id=name_gen.get_or_create(ns), gen_order=node_counter[0])
            node_counter[0] += 1
            children.append(cn)
        steps.append(SearchStep(len(steps), cur, children, list(explored), children,
                                f"depth={depth}, {len(cands)} branches"))
        for cn in children:
            r = bt(path_nodes + [cn], depth + 1)
            if r:
                return r
        return None

    sol = bt([root], 0)
    algo = "CSP: Forward Checking" if forward_checking else "CSP: Backtracking"
    if sol:
        path = reconstruct_path(sol)
        moves = [n.move for n in path if n.move]
        return SearchResult(True, algo, steps, path, moves, len(moves), len(moves),
                            len(explored), name_gen.count, max_fs, 0.0)
    return SearchResult(False, algo, steps, [], [], 0, 0,
                        len(explored), name_gen.count, max_fs, 0.0,
                        f"No solution within depth {depth_limit}.")


def run_csp_path_consistency_puzzle(start, goal, depth_limit=20, move_order=('L', 'R', 'U', 'D')):
    """Path consistency cho 8-puzzle: moi cap trang thai lien tiep phai hop le va duong di khong lap."""
    name_gen = NodeNameGenerator()
    goal_pos = {v: i for i, v in enumerate(goal)}

    def h(state):
        return sum(
            abs(i // 3 - goal_pos[v] // 3) + abs(i % 3 - goal_pos[v] % 3)
            for i, v in enumerate(state) if v != 0
        )

    root = SearchNode(state=start, parent=None, parent_id=None, move=None,
                      depth=0, cost=0, node_id=name_gen.get_or_create(start),
                      gen_order=0, h=h(start), f=h(start))
    frontier = [root]
    explored = []
    steps = []
    generated = 1
    max_frontier = 1

    while frontier:
        max_frontier = max(max_frontier, len(frontier))
        current = frontier.pop()
        explored.append(current)
        if current.state == goal:
            path = reconstruct_path(current)
            moves = [n.move for n in path if n.move]
            steps.append(SearchStep(len(steps), current, list(frontier), list(explored), [], "Path consistent goal."))
            return SearchResult(True, "CSP: Path Consistency", steps, path, moves,
                                len(moves), len(moves), len(explored), name_gen.count,
                                max_frontier, 0.0)
        if current.depth >= depth_limit:
            continue

        path_states = set()
        p = current
        while p:
            path_states.add(p.state)
            p = p.parent

        children = []
        remaining = depth_limit - current.depth - 1
        for move, next_state, _ in get_neighbors(current.state, move_order):
            if next_state in path_states:
                continue
            if h(next_state) > remaining + h(goal):
                continue
            child_h = h(next_state)
            child = SearchNode(state=next_state, parent=current, parent_id=current.id,
                               move=move, depth=current.depth + 1, cost=current.cost + 1,
                               node_id=name_gen.get_or_create(next_state),
                               gen_order=generated, h=child_h,
                               f=current.cost + 1 + child_h)
            generated += 1
            children.append(child)
        children.sort(key=lambda n: (n.h, n.gen_order), reverse=True)
        frontier.extend(children)
        steps.append(SearchStep(len(steps), current, list(frontier), list(explored),
                                children, f"path-consistent branches={len(children)}"))

    return SearchResult(False, "CSP: Path Consistency", steps, [], [], 0, 0,
                        len(explored), name_gen.count, max_frontier, 0.0,
                        f"No path-consistent solution within depth {depth_limit}.")


def run_csp_global_constraints_puzzle(start, goal, depth_limit=40, move_order=('L', 'R', 'U', 'D')):
    """Global constraints cho 8-puzzle: all-different tiles, parity solvability va A* bounded depth."""
    if set(start) != set(range(9)) or set(goal) != set(range(9)):
        return SearchResult(False, "CSP: Global Constraints", [], [], [], 0, 0, 0, 0, 0, 0.0,
                            "Global all-different constraint failed.")
    if not is_solvable(start, goal):
        return SearchResult(False, "CSP: Global Constraints", [], [], [], 0, 0, 0, 0, 0, 0.0,
                            "Global parity constraint failed.")

    result = run_astar(start, goal, move_order=move_order, cost_mode=1, heuristic_mode=1)
    result.algorithm = "CSP: Global Constraints"
    if result.success and result.total_steps > depth_limit:
        result.success = False
        result.message = f"Solution violates global max-depth constraint ({depth_limit})."
    for step in result.steps:
        step.note = (step.note + "\n" if step.note else "") + "Global constraints: all-different, solvable parity, bounded depth."
    return result


def run_csp_backtracking_search_puzzle(start, goal, depth_limit=10, move_order=('L', 'R', 'U', 'D')):
    result = run_csp_backtracking_puzzle(start, goal, forward_checking=False,
                                         depth_limit=depth_limit, move_order=move_order)
    result.algorithm = "CSP: Backtracking Search"
    return result


def run_csp_ac3_puzzle(start, goal, depth_limit=10, move_order=('L', 'R', 'U', 'D')):
    """AC-3 cho 8-puzzle: rut gon mien hanh dong ke tiep, roi backtracking tren mien da loc."""
    opposite = {'L': 'R', 'R': 'L', 'U': 'D', 'D': 'U'}
    domains = {i: set(move_order) for i in range(depth_limit)}
    queue = deque((i, i + 1) for i in range(depth_limit - 1))
    revisions = 0

    def revise(xi, xj):
        removed = set()
        for action in set(domains[xi]):
            if not any(next_action != opposite[action] for next_action in domains[xj]):
                removed.add(action)
        if removed:
            domains[xi] -= removed
            return True
        return False

    while queue:
        xi, xj = queue.popleft()
        if revise(xi, xj):
            revisions += 1
            if not domains[xi]:
                return SearchResult(False, "CSP: AC-3", [], [], [], 0, 0, 0, 0, 0, 0.0,
                                    f"AC-3 found an empty domain at A{xi + 1}.")
            for xk in (xi - 1,):
                if xk >= 0 and xk != xj:
                    queue.append((xk, xi))

    name_gen = NodeNameGenerator()
    root = SearchNode(state=start, parent=None, parent_id=None, move=None,
                      depth=0, cost=0, node_id=name_gen.get_or_create(start), gen_order=0)
    steps = []
    explored = []
    generated = 1
    max_frontier = 1
    goal_pos = {v: i for i, v in enumerate(goal)}

    def h(state):
        return sum(
            abs(i // 3 - goal_pos[v] // 3) + abs(i % 3 - goal_pos[v] % 3)
            for i, v in enumerate(state) if v != 0
        )

    def bt(path_nodes, depth):
        nonlocal generated, max_frontier
        current = path_nodes[-1]
        explored.append(current)
        if current.state == goal:
            steps.append(SearchStep(len(steps), current, [], list(explored), [],
                                    f"Goal reached after AC-3 preprocessing ({revisions} revisions)."))
            return current
        if depth >= depth_limit:
            return None

        path_states = {n.state for n in path_nodes}
        remaining = depth_limit - depth - 1
        children = []
        for move, next_state, _ in get_neighbors(current.state, move_order):
            if move not in domains[depth]:
                continue
            if current.move and move == opposite[current.move]:
                continue
            if next_state in path_states:
                continue
            if h(next_state) > remaining:
                continue
            child_h = h(next_state)
            child = SearchNode(state=next_state, parent=current, parent_id=current.id,
                               move=move, depth=depth + 1, cost=current.cost + 1,
                               node_id=name_gen.get_or_create(next_state),
                               gen_order=generated, h=child_h,
                               f=current.cost + 1 + child_h)
            generated += 1
            children.append(child)

        children.sort(key=lambda n: (n.h, n.gen_order))
        max_frontier = max(max_frontier, len(children))
        steps.append(SearchStep(len(steps), current, children, list(explored), children,
                                f"AC-3 domains ready, branches={len(children)}"))
        for child in children:
            result = bt(path_nodes + [child], depth + 1)
            if result:
                return result
        return None

    solution = bt([root], 0)
    if solution:
        path = reconstruct_path(solution)
        moves = [n.move for n in path if n.move]
        return SearchResult(True, "CSP: AC-3", steps, path, moves,
                            len(moves), len(moves), len(explored), name_gen.count,
                            max_frontier, 0.0)
    return SearchResult(False, "CSP: AC-3", steps, [], [], 0, 0,
                        len(explored), name_gen.count, max_frontier, 0.0,
                        f"No AC-3 assisted solution within depth {depth_limit}.")


def run_csp_min_conflicts_puzzle(start, goal, max_steps=100, move_order=('L', 'R', 'U', 'D')):
    """Min-conflicts cho 8-puzzle: chon lan can co so xung dot thap nhat."""
    name_gen = NodeNameGenerator()

    def conflicts(state):
        misplaced = sum(1 for i, v in enumerate(state) if v != 0 and v != goal[i])
        goal_pos = {v: i for i, v in enumerate(goal)}
        manhattan = sum(
            abs(i // 3 - goal_pos[v] // 3) + abs(i % 3 - goal_pos[v] % 3)
            for i, v in enumerate(state) if v != 0
        )
        return misplaced + manhattan

    current = SearchNode(state=start, parent=None, parent_id=None, move=None,
                         depth=0, cost=0, node_id=name_gen.get_or_create(start),
                         gen_order=0, h=conflicts(start), f=conflicts(start))
    explored = [current]
    steps = []
    visited = {start}
    max_frontier = 1

    for step_idx in range(max_steps + 1):
        if current.state == goal:
            path = reconstruct_path(current)
            moves = [n.move for n in path if n.move]
            steps.append(SearchStep(len(steps), current, [], list(explored), [], "No conflicts remain."))
            return SearchResult(True, "CSP: Min-Conflicts", steps, path, moves,
                                len(moves), len(moves), len(explored), name_gen.count,
                                max_frontier, 0.0)

        candidates = []
        for move, next_state, _ in get_neighbors(current.state, move_order):
            h_val = conflicts(next_state)
            child = SearchNode(state=next_state, parent=current, parent_id=current.id,
                               move=move, depth=current.depth + 1, cost=current.cost + 1,
                               node_id=name_gen.get_or_create(next_state),
                               gen_order=name_gen.count, h=h_val, f=h_val)
            candidates.append(child)
        if not candidates:
            break

        min_h = min(c.h for c in candidates)
        best = [c for c in candidates if c.h == min_h]
        unvisited_best = [c for c in best if c.state not in visited]
        next_node = random.choice(unvisited_best or best)

        max_frontier = max(max_frontier, len(candidates))
        steps.append(SearchStep(len(steps), current, candidates, list(explored),
                                candidates, f"min-conflicts={min_h}"))
        current = next_node
        explored.append(current)
        visited.add(current.state)

    path = reconstruct_path(current)
    moves = [n.move for n in path if n.move]
    return SearchResult(False, "CSP: Min-Conflicts", steps, path, moves,
                        current.cost, current.depth, len(explored), name_gen.count,
                        max_frontier, 0.0,
                        f"Did not remove all conflicts within {max_steps} steps.")


def run_and_or_search_puzzle(start, goal, max_depth=5, move_order=('L', 'R', 'U', 'D')):
    """AND-OR Search cho 8-puzzle (nondeterministic: action can slip)."""
    name_gen = NodeNameGenerator()
    root = SearchNode(state=start, parent=None, parent_id=None, move=None,
                      depth=0, cost=0, node_id=name_gen.get_or_create(start), gen_order=0)
    steps = []
    explored = []
    nc = [1]
    max_fs = 0

    def outcomes(state, action):
        valid = {m: s for m, s, _ in get_neighbors(state, move_order)}
        if action not in valid:
            return [state]
        alts = [s for m, s in valid.items() if m != action]
        return [valid[action], alts[0]] if alts else [valid[action]]

    def or_search(node, state, path, depth):
        nonlocal max_fs
        explored.append(node)
        if state == goal:
            steps.append(SearchStep(len(steps), node, [], list(explored), [], "Goal!"))
            return "Goal", [node]
        if depth >= max_depth:
            return None
        for action in [m for m, _, _ in get_neighbors(state, move_order)]:
            outs = outcomes(state, action)
            children = []
            for o in outs:
                cn = SearchNode(state=o, parent=node, parent_id=node.id, move=action,
                                depth=depth+1, cost=depth+1,
                                node_id=name_gen.get_or_create(o), gen_order=nc[0])
                nc[0] += 1
                children.append(cn)
            max_fs = max(max_fs, len(children))
            steps.append(SearchStep(len(steps), node, [], list(explored), children,
                                    f"OR:{action}, AND over {len(outs)} outcomes"))
            plans, rep, ok = [], None, True
            for cn, o in zip(children, outs):
                if o == state or o in path:
                    ok = False; break
                sub = or_search(cn, o, path + [state], depth + 1)
                if sub is None:
                    ok = False; break
                pt, pnodes = sub
                plans.append(f"if {o[0]}..{o[-1]} -> {pt}")
                rep = rep or [node] + pnodes
            if ok and rep:
                node.details = getattr(node, 'details', '') + f"\nPlan: {action}->{' | '.join(plans)}"
                return f"{action}->({' | '.join(plans)})", rep
        return None

    res = or_search(root, start, [], 0)
    if res:
        plan, path = res
        path[-1].details = getattr(path[-1], 'details', '') + f"\nFinal: {plan}"
        moves = [n.move for n in path if n.move]
        return SearchResult(True, "Complex Env: AND-OR Search", steps, path, moves,
                            len(moves), len(moves), len(explored), name_gen.count, max_fs, 0.0)
    return SearchResult(False, "Complex Env: AND-OR Search", steps, [root], [], 0, 0,
                        len(explored), name_gen.count, max_fs, 0.0,
                        f"No conditional plan within depth {max_depth}.")


def run_no_observation_search_puzzle(start, goal, max_depth=10, move_order=('L', 'R', 'U', 'D')):
    """Sensorless (No Observation) belief-state search cho 8-puzzle."""
    def trans(state, action):
        bi = state.index(0); r, c = bi // 3, bi % 3
        dr, dc = {'L':(0,-1),'R':(0,1),'U':(-1,0),'D':(1,0)}[action]
        nr, nc2 = r+dr, c+dc
        if 0 <= nr < 3 and 0 <= nc2 < 3:
            ni = nr*3+nc2; lst = list(state); lst[bi], lst[ni] = lst[ni], lst[bi]
            return tuple(lst)
        return state

    def b2board(belief):
        b = []
        for i in range(9):
            vals = {s[i] for s in belief}
            b.append(next(iter(vals)) if len(vals) == 1 else 9)
        return tuple(b)

    nbrs = get_neighbors(start, move_order)
    init_b = frozenset([start] + [s for _, s, _ in nbrs[:2]])
    name_gen = NodeNameGenerator()
    root = SearchNode(state=b2board(init_b), parent=None, parent_id=None, move=None,
                      depth=0, cost=0, node_id=name_gen.get_or_create(init_b), gen_order=0)
    root.belief = init_b
    root.details = f"Initial belief: {len(init_b)} states"

    frontier = deque([(init_b, root)])
    visited = {init_b}
    explored, steps = [], []
    max_fs, nc = 1, [1]

    while frontier:
        max_fs = max(max_fs, len(frontier))
        belief, node = frontier.popleft()
        explored.append(node)
        if all(s == goal for s in belief):
            steps.append(SearchStep(len(steps), node, [x[1] for x in frontier],
                                    list(explored), [], "Belief converged to Goal!"))
            path = reconstruct_path(node)
            moves = [n.move for n in path if n.move]
            return SearchResult(True, "Complex Env: No Observation", steps, path, moves,
                                len(moves), len(moves), len(explored), nc[0], max_fs, 0.0)
        if node.depth >= max_depth:
            continue
        children = []
        for action in move_order:
            nb = frozenset(trans(s, action) for s in belief)
            if nb in visited:
                continue
            visited.add(nb)
            cn = SearchNode(state=b2board(nb), parent=node, parent_id=node.id, move=action,
                            depth=node.depth+1, cost=node.cost+1,
                            node_id=name_gen.get_or_create(nb), gen_order=nc[0])
            cn.belief = nb
            cn.details = f"Action:{action}, belief size:{len(nb)}"
            nc[0] += 1
            children.append((nb, cn))
        for item in children:
            frontier.append(item)
        steps.append(SearchStep(len(steps), node, [x[1] for x in frontier],
                                list(explored), [c for _, c in children],
                                f"Belief size={len(belief)}"))
    return SearchResult(False, "Complex Env: No Observation", steps, [root], [], 0, 0,
                        len(explored), nc[0], max_fs, 0.0,
                        f"No conformant plan within depth {max_depth}.")


def run_partially_observable_search_puzzle(start, goal, max_steps=12, move_order=('L', 'R', 'U', 'D')):
    """Partial Observation belief-state search cho 8-puzzle."""
    from itertools import permutations as _perms

    def obs(state):
        return (state.index(0), state[:3])

    def trans(state, action):
        bi = state.index(0); r, c = bi // 3, bi % 3
        dr, dc = {'L':(0,-1),'R':(0,1),'U':(-1,0),'D':(1,0)}[action]
        nr, nc2 = r+dr, c+dc
        if 0 <= nr < 3 and 0 <= nc2 < 3:
            ni = nr*3+nc2; lst = list(state); lst[bi], lst[ni] = lst[ni], lst[bi]
            return tuple(lst)
        return state

    def b2board(belief):
        b = []
        for i in range(9):
            vals = {s[i] for s in belief}
            b.append(next(iter(vals)) if len(vals) == 1 else 9)
        return tuple(b)

    row1 = start[:3]
    remaining = [x for x in range(9) if x not in row1]
    blist = []
    for p in _perms(remaining):
        s = row1 + p
        if s.index(0) == start.index(0) and is_solvable(s, goal):
            blist.append(s)
    belief = frozenset(blist)

    name_gen = NodeNameGenerator()
    root = SearchNode(state=b2board(belief), parent=None, parent_id=None, move=None,
                      depth=0, cost=0, node_id=name_gen.get_or_create(belief), gen_order=0)
    root.belief = belief
    root.details = f"Partial obs. Initial belief: {len(belief)} states"

    steps = [SearchStep(0, root, [], [root], [], "Initial belief")]
    explored = [root]
    current_node = root
    actual = start

    astar_res = run_astar(start, goal, cost_mode=1, heuristic_mode=1)
    if not astar_res.success:
        return SearchResult(False, "Complex Env: Partial Observation", steps, [root],
                            [], 0, 0, 1, 1, 1, 0.0, "A* failed on actual state.")

    for depth, action in enumerate(astar_res.moves, 1):
        if depth > max_steps:
            break
        next_actual = trans(actual, action)
        o = obs(next_actual)
        predicted = {trans(s, action) for s in belief}
        next_b = frozenset(s for s in predicted if obs(s) == o)
        cn = SearchNode(state=b2board(next_b), parent=current_node, parent_id=current_node.id,
                        move=action, depth=depth, cost=depth,
                        node_id=name_gen.get_or_create(next_b), gen_order=depth)
        cn.belief = next_b
        cn.details = (f"Action:{action}\nObs:{o}\n"
                      f"Belief: {len(predicted)}->{len(next_b)}\nActual:{next_actual}")
        explored.append(cn)
        steps.append(SearchStep(len(steps), cn, [], list(explored), [], "Belief update"))
        current_node = cn
        actual = next_actual
        belief = next_b
        if actual == goal and all(s == goal for s in belief):
            path = reconstruct_path(cn)
            moves = [n.move for n in path if n.move]
            return SearchResult(True, "Complex Env: Partial Observation", steps, path, moves,
                                len(moves), len(moves), len(explored), name_gen.count, 1, 0.0)

    path = reconstruct_path(current_node)
    moves = [n.move for n in path if n.move]
    return SearchResult(False, "Complex Env: Partial Observation", steps, path, moves,
                        current_node.cost, current_node.depth,
                        len(explored), name_gen.count, 1, 0.0,
                        f"Did not converge after {max_steps} steps.")


# =============================================================================
# BỘ SINH TRẠNG THÁI NGẪU NHIÊN CHẮC CHẮN GIẢI ĐƯỢC
# =============================================================================

def generate_random_puzzle(difficulty="medium"):
    """
    Sinh một trạng thái 8-puzzle ngẫu nhiên chắc chắn giải được bằng cách
    đi lùi ngẫu nhiên (random walk backward) từ trạng thái đích.
    """
    state = (1, 2, 3, 4, 5, 6, 7, 8, 0)
    visited = {state}
    
    if difficulty == "easy":
        steps = random.randint(5, 8)
    elif difficulty == "hard":
        steps = random.randint(25, 35)
    else:  # medium
        steps = random.randint(12, 18)
        
    curr = state
    for _ in range(steps):
        blank_idx = curr.index(0)
        r = blank_idx // 3
        c = blank_idx % 3
        moves = []
        if r > 0: moves.append(-3)  # Up
        if r < 2: moves.append(3)   # Down
        if c > 0: moves.append(-1)  # Left
        if c < 2: moves.append(1)   # Right
        
        next_states = []
        for m in moves:
            lst = list(curr)
            lst[blank_idx], lst[blank_idx+m] = lst[blank_idx+m], lst[blank_idx]
            next_states.append(tuple(lst))
            
        valid_next = [s for s in next_states if s not in visited]
        if not valid_next:
            valid_next = next_states
            
        curr = random.choice(valid_next)
        visited.add(curr)
        
    return curr


# =============================================================================
# LỚP GIAO DIỆN CHÍNH (UPGRADED TTKBOOTSTRAP APP)
# =============================================================================

class SearchVisualizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("8-Puzzle Search Visualizer (Upgraded UI)")
        
        # Biến quản lý trạng thái
        self.steps = []
        self.search_steps = []
        self.solution_steps = []
        self.current_step_idx = -1
        self.result = None
        self.auto_playing = False
        
        # Trạng thái mặc định
        self.default_start = (1, 2, 3, 4, 0, 6, 7, 5, 8)
        self.default_goal = (1, 2, 3, 4, 5, 6, 7, 8, 0)
        self.current_board_state = self.default_start
        self.manual_moves = 0
        self.play_speed = 700  # ms
        
        # Thiết lập giao diện
        self.create_widgets()
        self.on_algo_change()
        self.load_example_state()
        
    def create_widgets(self):
        # Frame chính
        main_frame = tb.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # ---------------------------------------------------------------------
        # TOP PANEL: Cấu hình Trạng thái & Giao diện
        # ---------------------------------------------------------------------
        top_frame = tb.LabelFrame(main_frame, text=" Cấu hình Trạng thái & Giao diện ")
        top_frame.pack(side=TOP, fill=X, padx=10, pady=(0, 10))
        
        # Grid layout cho Top frame
        top_frame.columnconfigure(1, weight=1)
        top_frame.columnconfigure(3, weight=1)
        
        tb.Label(top_frame, text="Start state:").grid(row=0, column=0, sticky=W, padx=5, pady=5)
        self.entry_start = tb.Entry(top_frame)
        self.entry_start.grid(row=0, column=1, sticky=EW, padx=5, pady=5)
        self.entry_start.insert(0, "1 2 3 4 0 6 7 5 8")
        
        tb.Label(top_frame, text="Goal state:").grid(row=0, column=2, sticky=W, padx=5, pady=5)
        self.entry_goal = tb.Entry(top_frame)
        self.entry_goal.grid(row=0, column=3, sticky=EW, padx=5, pady=5)
        self.entry_goal.insert(0, "1 2 3 4 5 6 7 8 0")
        
        self.btn_load_example = tb.Button(top_frame, text="Mặc định", bootstyle=SECONDARY, command=self.load_example_state)
        self.btn_load_example.grid(row=0, column=4, padx=5, pady=5)
        
        tb.Label(top_frame, text="Giao diện:").grid(row=0, column=5, sticky=W, padx=10, pady=5)
        self.theme_combo = tb.Combobox(
            top_frame, 
            values=["darkly", "superhero", "cyborg", "vapor", "solar", "flatly", "cosmo", "sandstone", "yeti"], 
            state="readonly", 
            width=10
        )
        self.theme_combo.grid(row=0, column=6, padx=5, pady=5)
        self.theme_combo.set("darkly")
        self.theme_combo.bind("<<ComboboxSelected>>", self.change_theme)
        
        # ---------------------------------------------------------------------
        # MIDDLE DIVISION: Left (Board & Tools), Right (Visualizer & Comparison)
        # ---------------------------------------------------------------------
        mid_frame = tb.Frame(main_frame)
        mid_frame.pack(side=TOP, fill=BOTH, expand=YES)
        
        # Cột trái: Bàn cờ & Điều khiển Chơi
        left_panel = tb.Frame(mid_frame)
        left_panel.pack(side=LEFT, fill=Y, padx=(0, 15))
        
        # Bàn cờ 3x3
        board_container = tb.LabelFrame(left_panel, text=" Bàn cờ (Nhấp ô liền kề để chơi) ")
        board_container.pack(side=TOP, fill=X, padx=10, pady=(0, 10))
        
        self.board_frame = tb.Frame(board_container)
        self.board_frame.pack(anchor=CENTER)
        
        self.tiles = []
        for r in range(3):
            row_tiles = []
            for c in range(3):
                lbl = tk.Label(
                    self.board_frame, text="", font=("Helvetica", 24, "bold"),
                    width=5, height=2, bd=2, relief=tk.RAISED, bg="#2C3E50", fg="#FFFFFF"
                )
                lbl.grid(row=r, column=c, padx=3, pady=3)
                lbl.bind("<Button-1>", lambda event, row=r, col=c: self.click_tile(row, col))
                row_tiles.append(lbl)
            self.tiles.append(row_tiles)
            
        # Sinh trạng thái
        gen_container = tb.LabelFrame(left_panel, text=" Sinh Trạng Thái Ngẫu Nhiên ")
        gen_container.pack(side=TOP, fill=X, padx=10, pady=(0, 10))
        
        tb.Button(gen_container, text="Dễ", bootstyle=SUCCESS, command=lambda: self.generate_board("easy")).pack(side=LEFT, fill=X, expand=YES, padx=2)
        tb.Button(gen_container, text="T.Bình", bootstyle=INFO, command=lambda: self.generate_board("medium")).pack(side=LEFT, fill=X, expand=YES, padx=2)
        tb.Button(gen_container, text="Khó", bootstyle=DANGER, command=lambda: self.generate_board("hard")).pack(side=LEFT, fill=X, expand=YES, padx=2)
        
        # Chơi thủ công & Gợi ý
        manual_container = tb.LabelFrame(left_panel, text=" Chơi Thủ Công & Gợi Ý ")
        manual_container.pack(side=TOP, fill=X, padx=10, pady=(0, 10))
        
        self.lbl_manual_status = tb.Label(manual_container, text="Số bước đi bằng tay: 0", font=("Helvetica", 10))
        self.lbl_manual_status.pack(anchor=W, pady=(0, 8))
        
        tb.Button(manual_container, text="Chơi Lại", bootstyle=SECONDARY, command=self.reset_manual_play).pack(side=LEFT, fill=X, expand=YES, padx=2)
        tb.Button(manual_container, text="Gợi Ý", bootstyle=WARNING, command=self.get_hint).pack(side=LEFT, fill=X, expand=YES, padx=2)
        
        # Cột phải: Notebook cho Trực quan & So sánh
        right_panel = tb.Frame(mid_frame)
        right_panel.pack(side=LEFT, fill=BOTH, expand=YES)
        
        self.notebook = tb.Notebook(right_panel, bootstyle=PRIMARY)
        self.notebook.pack(fill=BOTH, expand=YES)
        
        # Tab 1: Trực quan hóa
        self.tab_visualizer = tb.Frame(self.notebook)
        self.tab_visualizer.pack_configure(padx=10, pady=10)
        self.notebook.add(self.tab_visualizer, text="Trực quan tìm kiếm")
        
        # Khung thuật toán ở trên cùng Tab 1
        algo_frame = tb.Frame(self.tab_visualizer)
        algo_frame.pack(side=TOP, fill=X, padx=5, pady=(0, 5))
        
        tb.Label(algo_frame, text="Thuật toán:").pack(side=LEFT, padx=5)
        self.algo_combo = tb.Combobox(
            algo_frame, 
            values=ALGORITHM_CHOICES, 
            state="readonly", 
            width=34
        )
        self.algo_combo.pack(side=LEFT, padx=5)
        self.algo_combo.set("A*")
        self.algo_combo.bind("<<ComboboxSelected>>", self.on_algo_change)
        
        # Khung cấu hình động của từng thuật toán
        self.options_frame = tb.Frame(self.tab_visualizer)
        self.options_frame.pack(side=TOP, fill=X, padx=5, pady=(0, 5))
        
        # Khung điều khiển chạy từng bước
        ctrl_container = tb.LabelFrame(self.tab_visualizer, text=" Bảng Điều Khiển Chạy ")
        ctrl_container.pack(side=TOP, fill=X, padx=10, pady=(0, 10))
        
        btn_row = tb.Frame(ctrl_container)
        btn_row.pack(fill=X, pady=2)
        
        self.btn_run = tb.Button(btn_row, text="Chạy Tìm Kiếm", bootstyle=SUCCESS, width=12, command=self.click_run_search)
        self.btn_run.pack(side=LEFT, padx=2)
        
        self.btn_reset = tb.Button(btn_row, text="Về Đầu", bootstyle=SECONDARY, width=10, command=self.click_reset)
        self.btn_reset.pack(side=LEFT, padx=2)
        
        self.btn_prev = tb.Button(btn_row, text="Lùi 1 Bước", bootstyle=SECONDARY, width=10, command=self.click_prev_step)
        self.btn_prev.pack(side=LEFT, padx=2)
        
        self.btn_next = tb.Button(btn_row, text="Tiến 1 Bước", bootstyle=SECONDARY, width=10, command=self.click_next_step)
        self.btn_next.pack(side=LEFT, padx=2)
        
        self.btn_auto = tb.Button(btn_row, text="Tự Động Chạy", bootstyle=INFO, width=12, command=self.click_auto_play)
        self.btn_auto.pack(side=LEFT, padx=2)
        
        self.btn_pause = tb.Button(btn_row, text="Tạm Dừng", bootstyle=WARNING, width=10, command=self.click_pause)
        self.btn_pause.pack(side=LEFT, padx=2)
        
        # Chế độ xem: Tìm kiếm vs Lời giải
        mode_row = tb.Frame(ctrl_container)
        mode_row.pack(fill=X, pady=(0, 5))
        
        tb.Label(mode_row, text="Chế độ xem:").pack(side=LEFT, padx=5)
        self.view_mode_var = tk.StringVar(value="search")
        
        self.rad_search_mode = tb.Radiobutton(
            mode_row, text="Tiến trình tìm kiếm (Frontier)", 
            variable=self.view_mode_var, value="search", 
            command=self.toggle_view_mode
        )
        self.rad_search_mode.pack(side=LEFT, padx=10)
        
        self.rad_solution_mode = tb.Radiobutton(
            mode_row, text="Đường đi lời giải (Solution Path)", 
            variable=self.view_mode_var, value="solution", 
            command=self.toggle_view_mode
        )
        self.rad_solution_mode.pack(side=LEFT, padx=10)
        
        # Thanh trượt tốc độ & Tiến trình
        slider_row = tb.Frame(ctrl_container)
        slider_row.pack(fill=X, pady=(8, 2))
        
        tb.Label(slider_row, text="Tốc độ:").pack(side=LEFT, padx=5)
        self.speed_slider = tb.Scale(slider_row, from_=100, to=2000, orient=tk.HORIZONTAL, value=700, command=self.change_speed)
        self.speed_slider.config(length=100)
        self.speed_slider.pack(side=LEFT, padx=5, fill=X, expand=NO)
        self.lbl_speed_val = tb.Label(slider_row, text="700ms", width=6)
        self.lbl_speed_val.pack(side=LEFT, padx=2)
        
        tb.Label(slider_row, text="Bước:").pack(side=LEFT, padx=(15, 5))
        self.step_slider = tb.Scale(slider_row, from_=0, to=0, orient=tk.HORIZONTAL, command=self.slide_step)
        self.step_slider.pack(side=LEFT, fill=X, expand=YES, padx=5)
        
        # Text log hiển thị bước
        log_container = tb.LabelFrame(self.tab_visualizer, text=" Nhật Ký Từng Bước (Step Log) ")
        log_container.pack(side=TOP, fill=BOTH, expand=YES, padx=10, pady=10)
        
        self.scrollbar = tb.Scrollbar(log_container, orient=VERTICAL)
        self.scrollbar.pack(side=RIGHT, fill=Y)
        
        self.text_log = tb.Text(
            log_container, font=("Consolas", 10), wrap=WORD,
            yscrollcommand=self.scrollbar.set, bg="#1E1E1E", fg="#D4D4D4"
        )
        self.text_log.pack(side=LEFT, fill=BOTH, expand=YES)
        self.scrollbar.config(command=self.text_log.yview)
        self.text_log.config(state=DISABLED)
        
        # Tab 2: So sánh hiệu năng
        self.tab_comparison = tb.Frame(self.notebook)
        self.tab_comparison.pack_configure(padx=10, pady=10)
        self.notebook.add(self.tab_comparison, text="Bảng so sánh thuật toán")
        
        comp_container = tb.Frame(self.tab_comparison)
        comp_container.pack(fill=BOTH, expand=YES)
        
        top_comp_bar = tb.Frame(comp_container)
        top_comp_bar.pack(side=TOP, fill=X, pady=(0, 10))
        
        self.btn_compare_all = tb.Button(
            top_comp_bar, text="Chạy tất cả thuật toán & So sánh", 
            bootstyle=DANGER, command=self.click_compare_all
        )
        self.btn_compare_all.pack(side=LEFT)
        
        self.lbl_comp_status = tb.Label(top_comp_bar, text="Trạng thái: Sẵn sàng so sánh", font=("Helvetica", 10, "italic"))
        self.lbl_comp_status.pack(side=LEFT, padx=15)
        
        # Cấu hình bảng Treeview
        self.tree = tb.Treeview(
            comp_container, 
            columns=("algo", "success", "steps", "cost", "expanded", "generated", "time"), 
            show="headings", 
            bootstyle=DANGER
        )
        self.tree.pack(side=TOP, fill=BOTH, expand=YES)
        
        self.tree.heading("algo", text="Thuật toán")
        self.tree.heading("success", text="Kết quả")
        self.tree.heading("steps", text="Số bước")
        self.tree.heading("cost", text="Chi phí (g)")
        self.tree.heading("expanded", text="Nút duyệt (Expanded)")
        self.tree.heading("generated", text="Nút sinh (Generated)")
        self.tree.heading("time", text="Thời gian (ms)")
        
        self.tree.column("algo", width=180, anchor=W)
        self.tree.column("success", width=90, anchor=CENTER)
        self.tree.column("steps", width=80, anchor=E)
        self.tree.column("cost", width=80, anchor=E)
        self.tree.column("expanded", width=150, anchor=E)
        self.tree.column("generated", width=150, anchor=E)
        self.tree.column("time", width=110, anchor=E)
        
        tree_scroll = tb.Scrollbar(self.tree, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side=RIGHT, fill=Y)
        
        note_lbl = tb.Label(
            comp_container, 
            text="Lưu ý:\n- Các thuật toán Heuristic (A*) được chạy với Heuristic: Manhattan.\n- Chi phí (Cost Mode) được cài đặt là Moved tile cost (Chi phí = Giá trị ô di chuyển).\n- DFS và IDS chạy với giới hạn độ sâu (Limit) là 20 để tránh quá tải.\n- So sánh sẽ chạy ngầm (multi-threaded) nên giao diện sẽ không bị đơ.",
            justify=LEFT, anchor=W
        )
        note_lbl.pack(side=BOTTOM, fill=X, padx=0, pady=10)
        
        # ---------------------------------------------------------------------
        # BOTTOM PANEL: Thanh trạng thái
        # ---------------------------------------------------------------------
        self.status_var = tk.StringVar(value="Sẵn sàng. Vui lòng nhấn Run Search hoặc chơi thử bằng tay.")
        self.lbl_status = tk.Label(
            main_frame, textvariable=self.status_var,
            bd=1, relief=SUNKEN, anchor=W,
            font=("Helvetica", 9, "italic")
        )
        self.lbl_status.pack(side=BOTTOM, fill=X, padx=5, pady=(5, 0))
        
        # Cập nhật trạng thái nút
        self.update_control_states()
        
    def on_algo_change(self, event=None):
        """Thay đổi động các widget tuỳ chỉnh tham số thuật toán."""
        algo = self.algo_combo.get()
        
        for child in self.options_frame.winfo_children():
            child.destroy()
            
        if algo == "DFS":
            tb.Label(self.options_frame, text="Giới hạn Độ sâu (Limit):").pack(side=LEFT, padx=5)
            self.entry_dfs_limit = tb.Entry(self.options_frame, width=8)
            self.entry_dfs_limit.pack(side=LEFT, padx=5)
            self.entry_dfs_limit.insert(0, "20")
        elif algo == "IDS":
            tb.Label(self.options_frame, text="Độ sâu tối đa (Max Depth):").pack(side=LEFT, padx=5)
            self.entry_ids_max = tb.Entry(self.options_frame, width=8)
            self.entry_ids_max.pack(side=LEFT, padx=5)
            self.entry_ids_max.insert(0, "20")
        elif algo == "UCS":
            tb.Label(self.options_frame, text="Tính chi phí (Cost):").pack(side=LEFT, padx=5)
            self.ucs_cost_mode_var = tk.IntVar(value=2)
            tb.Radiobutton(self.options_frame, text="Step cost = 1", variable=self.ucs_cost_mode_var, value=1).pack(side=LEFT, padx=5)
            tb.Radiobutton(self.options_frame, text="Moved tile cost", variable=self.ucs_cost_mode_var, value=2).pack(side=LEFT, padx=5)
        elif algo == "A*":
            tb.Label(self.options_frame, text="Heuristic:").pack(side=LEFT, padx=5)
            self.astar_heuristic_mode_var = tk.IntVar(value=1)
            tb.Radiobutton(self.options_frame, text="Manhattan", variable=self.astar_heuristic_mode_var, value=1).pack(side=LEFT, padx=5)
            tb.Radiobutton(self.options_frame, text="Misplaced", variable=self.astar_heuristic_mode_var, value=2).pack(side=LEFT, padx=5)
            
            tb.Label(self.options_frame, text="Chi phí:").pack(side=LEFT, padx=15)
            self.astar_cost_mode_var = tk.IntVar(value=2)
            tb.Radiobutton(self.options_frame, text="Step = 1", variable=self.astar_cost_mode_var, value=1).pack(side=LEFT, padx=5)
            tb.Radiobutton(self.options_frame, text="Moved tile", variable=self.astar_cost_mode_var, value=2).pack(side=LEFT, padx=5)
        elif algo in ("Simple Hill Climbing", "Steepest Ascent Hill Climbing", "Stochastic Hill Climbing", "Random Restart Hill Climbing"):
            tb.Label(self.options_frame, text="Heuristic:").pack(side=LEFT, padx=5)
            self.hill_heuristic_mode_var = tk.IntVar(value=1)
            tb.Radiobutton(self.options_frame, text="Manhattan", variable=self.hill_heuristic_mode_var, value=1).pack(side=LEFT, padx=5)
            tb.Radiobutton(self.options_frame, text="Misplaced", variable=self.hill_heuristic_mode_var, value=2).pack(side=LEFT, padx=5)
            
            tb.Label(self.options_frame, text="Max Iterations:").pack(side=LEFT, padx=15)
            self.hill_max_iter_entry = tb.Entry(self.options_frame, width=6)
            self.hill_max_iter_entry.pack(side=LEFT, padx=5)
            self.hill_max_iter_entry.insert(0, "100")
            
            if algo == "Random Restart Hill Climbing":
                tb.Label(self.options_frame, text="Restarts:").pack(side=LEFT, padx=15)
                self.hill_restart_entry = tb.Entry(self.options_frame, width=6)
                self.hill_restart_entry.pack(side=LEFT, padx=5)
                self.hill_restart_entry.insert(0, "5")
        elif algo == "Local Beam Search":
            tb.Label(self.options_frame, text="Beam Width k:").pack(side=LEFT, padx=5)
            self.beam_width_entry = tb.Entry(self.options_frame, width=6)
            self.beam_width_entry.pack(side=LEFT, padx=5)
            self.beam_width_entry.insert(0, "3")
            
            tb.Label(self.options_frame, text="Heuristic:").pack(side=LEFT, padx=15)
            self.lbs_heuristic_mode_var = tk.IntVar(value=1)
            tb.Radiobutton(self.options_frame, text="Manhattan", variable=self.lbs_heuristic_mode_var, value=1).pack(side=LEFT, padx=5)
            tb.Radiobutton(self.options_frame, text="Misplaced", variable=self.lbs_heuristic_mode_var, value=2).pack(side=LEFT, padx=5)
        elif algo in CSP_ALGORITHMS:
            limit_label = "Max Iterations:" if algo == "CSP: Min-Conflicts" else "Giới hạn Độ sâu (Limit):"
            if algo == "CSP: Min-Conflicts":
                default_limit = "100"
            elif algo == "CSP: Global Constraints":
                default_limit = "40"
            elif algo == "CSP: Path Consistency":
                default_limit = "20"
            elif algo == "CSP: AC-3":
                default_limit = "20"
            else:
                default_limit = "10"
            tb.Label(self.options_frame, text=limit_label).pack(side=LEFT, padx=5)
            self.entry_csp_limit = tb.Entry(self.options_frame, width=8)
            self.entry_csp_limit.pack(side=LEFT, padx=5)
            self.entry_csp_limit.insert(0, default_limit)
        elif algo in COMPLEX_ENV_ALGORITHMS:
            tb.Label(self.options_frame, text="Độ sâu tối đa / Số bước:").pack(side=LEFT, padx=5)
            self.entry_complex_limit = tb.Entry(self.options_frame, width=8)
            self.entry_complex_limit.pack(side=LEFT, padx=5)
            if algo == "Complex Env: AND-OR Search":
                self.entry_complex_limit.insert(0, "5")
            elif algo == "Complex Env: No Observation":
                self.entry_complex_limit.insert(0, "10")
            else:
                self.entry_complex_limit.insert(0, "12")
        else:
            tb.Label(self.options_frame, text="Thuật toán chạy với cấu hình mặc định.", font=("Helvetica", 9, "italic")).pack(side=LEFT, padx=5)
            
    def load_example_state(self):
        """Khôi phục trạng thái Start & Goal ví dụ mặc định."""
        self.entry_start.delete(0, tk.END)
        self.entry_start.insert(0, "1 2 3 4 0 6 7 5 8")
        
        self.entry_goal.delete(0, tk.END)
        self.entry_goal.insert(0, "1 2 3 4 5 6 7 8 0")
        
        self.current_board_state = self.default_start
        self.draw_custom_board(self.default_start)
        self.click_clear_log()
        self.status_var.set("Đã tải trạng thái mặc định của ví dụ.")
        
    def is_csp_visualization_active(self):
        return self.result is not None and self.result.algorithm.startswith("CSP:")

    def get_moved_tile_value(self, node):
        if not node or not node.parent:
            return None
        parent_blank = node.parent.state.index(0)
        return node.state[parent_blank]

    def get_candidate_tile_values(self, step):
        values = set()
        if not step:
            return values
        current_state = step.current_node.state
        for child in step.generated_children:
            try:
                new_blank = child.state.index(0)
                moved_value = current_state[new_blank]
                if moved_value != 0:
                    values.add(moved_value)
            except Exception:
                continue
        return values

    def append_csp_color_legend(self, log_lines):
        if not self.is_csp_visualization_active():
            return
        log_lines.append("CSP COLORING:")
        log_lines.append("Green = satisfied tile constraint")
        log_lines.append("Red = conflict / unsatisfied tile constraint")
        log_lines.append("Orange = current assigned move")
        log_lines.append("Cyan = candidate domain values for next branch")
        log_lines.append("")

    def draw_custom_board(self, state, step=None):
        """Vẽ trạng thái state lên bàn cờ hiển thị 3x3 ở cột trái, highlight đúng/sai."""
        goal = parse_state(self.entry_goal.get())
        csp_mode = self.is_csp_visualization_active()
        moved_tile = self.get_moved_tile_value(step.current_node) if csp_mode and step else None
        candidate_tiles = self.get_candidate_tile_values(step) if csp_mode and step else set()
        for r in range(3):
            for c in range(3):
                val = state[r*3 + c]
                if val == 0:
                    self.tiles[r][c].config(text="", bg="#3A3F44")
                elif val == 9:
                    self.tiles[r][c].config(text="?", bg="#7F8C8D", fg="#FFFFFF")
                elif csp_mode:
                    is_correct = goal and (goal[r*3 + c] == val)
                    if val == moved_tile:
                        bg_color = "#F39C12"
                    elif val in candidate_tiles:
                        bg_color = "#17A2B8"
                    elif is_correct:
                        bg_color = "#00BC8C"
                    else:
                        bg_color = "#E74C3C"
                    self.tiles[r][c].config(text=str(val), bg=bg_color, fg="#FFFFFF")
                else:
                    # Highlight màu xanh lá nếu ô nằm đúng vị trí đích, ngược lại màu xanh dương
                    is_correct = goal and (goal[r*3 + c] == val)
                    if is_correct:
                        bg_color = "#00BC8C"  # Thành công - Green
                        fg_color = "#FFFFFF"
                    else:
                        bg_color = "#375A7F"  # Thông thường - Blue
                        fg_color = "#FFFFFF"
                    self.tiles[r][c].config(text=str(val), bg=bg_color, fg=fg_color)
                    
    def click_clear_log(self):
        """Xoá toàn bộ log và các bước chạy hiện tại."""
        self.auto_playing = False
        self.steps = []
        self.search_steps = []
        self.solution_steps = []
        self.view_mode_var.set("search")
        self.current_step_idx = -1
        self.result = None
        
        self.text_log.config(state=NORMAL)
        self.text_log.delete("1.0", tk.END)
        self.text_log.config(state=DISABLED)
        
        self.step_slider.config(from_=0, to=0)
        self.step_slider.set(0)
        
        # Cập nhật lại bàn cờ theo Start State hiện tại
        start_state = parse_state(self.entry_start.get())
        if start_state and len(start_state) == 9:
            self.current_board_state = start_state
            self.draw_custom_board(start_state)
            
        self.update_control_states()
        self.status_var.set("Đã xoá sạch log. Trạng thái sẵn sàng.")
        
    def update_control_states(self):
        """Bật/tắt các nút điều khiển tùy thuộc vào việc đã chạy thuật toán chưa."""
        has_steps = len(self.steps) > 0
        state = NORMAL if has_steps else DISABLED
        
        self.btn_prev.config(state=state)
        self.btn_next.config(state=state)
        self.btn_auto.config(state=state)
        self.btn_pause.config(state=state)
        self.btn_reset.config(state=state)
        self.step_slider.config(state=state)
        
        has_result = self.result is not None
        radio_state = NORMAL if has_result else DISABLED
        self.rad_search_mode.config(state=radio_state)
        self.rad_solution_mode.config(state=radio_state)
        
    def click_run_search(self):
        """Thực thi chạy thuật toán tìm kiếm trên một Thread riêng."""
        self.auto_playing = False
        
        start_txt = self.entry_start.get()
        goal_txt = self.entry_goal.get()
        
        start = parse_state(start_txt)
        goal = parse_state(goal_txt)
        
        if start is None or goal is None:
            messagebox.showwarning("Lỗi định dạng", "Trạng thái nhập không hợp lệ. Vui lòng nhập 9 số từ 0 đến 8.")
            return
            
        ok, msg = validate_state(start)
        if not ok:
            messagebox.showwarning("Lỗi Start State", f"Start State không hợp lệ: {msg}")
            return
            
        ok, msg = validate_state(goal)
        if not ok:
            messagebox.showwarning("Lỗi Goal State", f"Goal State không hợp lệ: {msg}")
            return
            
        if not is_solvable(start, goal):
            messagebox.showerror("Không thể giải", "Câu đố này không thể giải được!\nHai trạng thái có tính chẵn lẻ của số lượng cặp nghịch thế không khớp nhau.")
            self.status_var.set("Bài toán không thể giải (Not solvable).")
            self.click_clear_log()
            return
            
        # Reset game chơi thủ công
        self.manual_moves = 0
        self.lbl_manual_status.config(text="Số bước đi bằng tay: 0")
        
        # Bắt đầu chạy tìm kiếm ngầm
        self.btn_run.config(state=DISABLED)
        self.status_var.set("Đang chạy tìm kiếm trên luồng phụ...")
        self.root.update()
        
        algo = self.algo_combo.get()
        
        params = {}
        if algo == "DFS":
            try:
                params['depth_limit'] = int(self.entry_dfs_limit.get())
            except ValueError:
                params['depth_limit'] = 20
        elif algo == "IDS":
            try:
                params['max_depth'] = int(self.entry_ids_max.get())
            except ValueError:
                params['max_depth'] = 20
        elif algo == "UCS":
            params['cost_mode'] = self.ucs_cost_mode_var.get()
        elif algo == "A*":
            params['cost_mode'] = self.astar_cost_mode_var.get()
            params['heuristic_mode'] = self.astar_heuristic_mode_var.get()
        elif algo in ("Simple Hill Climbing", "Steepest Ascent Hill Climbing", "Stochastic Hill Climbing", "Random Restart Hill Climbing"):
            params['heuristic_mode'] = self.hill_heuristic_mode_var.get()
            try:
                params['max_iterations'] = max(1, int(self.hill_max_iter_entry.get()))
            except Exception:
                params['max_iterations'] = 100
            if algo == "Random Restart Hill Climbing":
                try:
                    params['restarts'] = max(1, int(self.hill_restart_entry.get()))
                except Exception:
                    params['restarts'] = 5
        elif algo == "Local Beam Search":
            try:
                params['beam_width'] = max(1, int(self.beam_width_entry.get()))
            except Exception:
                params['beam_width'] = 3
            params['heuristic_mode'] = self.lbs_heuristic_mode_var.get()
            params['max_iterations'] = 100
        elif algo in CSP_ALGORITHMS:
            try:
                params['depth_limit'] = int(self.entry_csp_limit.get())
            except Exception:
                params['depth_limit'] = 10
        elif algo in COMPLEX_ENV_ALGORITHMS:
            try:
                params['max_depth'] = int(self.entry_complex_limit.get())
            except Exception:
                params['max_depth'] = 5 if algo == "Complex Env: AND-OR Search" else (10 if algo == "Complex Env: No Observation" else 12)
            
        # Chạy thuật toán trong Thread phụ
        threading.Thread(target=self.run_search_worker, args=(algo, start, goal, params), daemon=True).start()
        
    def run_search_worker(self, algo, start, goal, params):
        start_time = time.perf_counter()
        
        if algo == "BFS":
            result = run_bfs(start, goal)
        elif algo == "DFS":
            result = run_dfs(start, goal, depth_limit=params['depth_limit'])
        elif algo == "IDS":
            result = run_ids(start, goal, max_depth=params['max_depth'])
        elif algo == "UCS":
            result = run_ucs(start, goal, cost_mode=params['cost_mode'])
        elif algo == "A*":
            result = run_astar(start, goal, cost_mode=params['cost_mode'], heuristic_mode=params['heuristic_mode'])
        elif algo == "Simple Hill Climbing":
            result = run_simple_hill_climbing(start, goal, heuristic_mode=params['heuristic_mode'], max_iterations=params['max_iterations'])
        elif algo == "Steepest Ascent Hill Climbing":
            result = run_steepest_ascent_hill_climbing(start, goal, heuristic_mode=params['heuristic_mode'], max_iterations=params['max_iterations'])
        elif algo == "Stochastic Hill Climbing":
            result = run_stochastic_hill_climbing(start, goal, heuristic_mode=params['heuristic_mode'], max_iterations=params['max_iterations'])
        elif algo == "Random Restart Hill Climbing":
            result = run_random_restart_hill_climbing(
                start, goal,
                heuristic_mode=params['heuristic_mode'],
                max_iterations=params['max_iterations'],
                restarts=params.get('restarts', 5)
            )
        elif algo == "Local Beam Search":
            result = run_local_beam_search(
                start, goal,
                beam_width=params.get('beam_width', 3),
                max_iterations=params.get('max_iterations', 100),
                heuristic_mode=params.get('heuristic_mode', 1)
            )
        elif algo in ("CSP: Backtracking", "CSP: Backtracking Search"):
            result = run_csp_backtracking_search_puzzle(start, goal,
                                                        depth_limit=params.get('depth_limit', 10))
        elif algo == "CSP: Forward Checking":
            result = run_csp_backtracking_puzzle(start, goal, forward_checking=True,
                                                 depth_limit=params.get('depth_limit', 10))
        elif algo == "CSP: AC-3":
            result = run_csp_ac3_puzzle(start, goal,
                                        depth_limit=params.get('depth_limit', 20))
        elif algo == "CSP: Path Consistency":
            result = run_csp_path_consistency_puzzle(start, goal,
                                                     depth_limit=params.get('depth_limit', 20))
        elif algo == "CSP: Global Constraints":
            result = run_csp_global_constraints_puzzle(start, goal,
                                                       depth_limit=params.get('depth_limit', 40))
        elif algo == "CSP: Min-Conflicts":
            result = run_csp_min_conflicts_puzzle(start, goal,
                                                  max_steps=params.get('depth_limit', 100))
        elif algo == "Complex Env: AND-OR Search":
            result = run_and_or_search_puzzle(start, goal, max_depth=params.get('max_depth', 5))
        elif algo == "Complex Env: No Observation":
            result = run_no_observation_search_puzzle(start, goal, max_depth=params.get('max_depth', 10))
        elif algo == "Complex Env: Partial Observation":
            result = run_partially_observable_search_puzzle(start, goal, max_steps=params.get('max_depth', 12))
        else:
            result = run_simple_hill_climbing(start, goal)
            
        end_time = time.perf_counter()
        result.time_taken = end_time - start_time
        
        # Trả kết quả về luồng UI chính
        self.root.after(0, lambda: self.search_finished(result))
        
    def search_finished(self, result):
        self.btn_run.config(state=NORMAL)
        self.result = result
        
        # Lưu các bước tìm kiếm và đường đi lời giải
        self.search_steps = result.steps
        self.solution_steps = []
        if result.success and result.solution_path:
            for idx, node in enumerate(result.solution_path):
                step = SearchStep(
                    step=idx,
                    current_node=node,
                    frontier=[],
                    explored=[],
                    generated_children=[],
                    note=f"Bước {idx}/{result.total_steps}: Di chuyển '{node.move}'" if node.move else "Trạng thái xuất phát (Start)"
                )
                self.solution_steps.append(step)
                
        # Thiết lập các bước hiển thị dựa trên chế độ xem được chọn
        if self.view_mode_var.get() == "solution" and result.success:
            self.steps = self.solution_steps
        else:
            self.view_mode_var.set("search")
            self.steps = self.search_steps
            
        self.current_step_idx = 0
        
        start_state = parse_state(self.entry_start.get())
        if start_state:
            self.current_board_state = start_state
            
        self.update_control_states()
        
        if self.steps:
            self.step_slider.config(from_=0, to=len(self.steps) - 1)
            self.step_slider.set(0)
            self.show_current_step()
            
        if result.success:
            self.status_var.set(f"Đã tìm thấy Goal! Tổng số bước di chuyển: {result.total_steps}. Tổng cost: {result.total_cost}. Kích thước Frontier max: {result.max_frontier_size}")
        else:
            self.status_var.set(f"Tìm kiếm thất bại: {result.message}")
            
    def toggle_view_mode(self):
        """Chuyển đổi giữa chế độ xem tiến trình tìm kiếm và xem đường đi lời giải."""
        if not self.result:
            return
            
        mode = self.view_mode_var.get()
        if mode == "solution":
            if not self.result.success:
                messagebox.showwarning("Không có lời giải", "Tìm kiếm thất bại nên không có đường đi lời giải.")
                self.view_mode_var.set("search")
                return
            self.steps = self.solution_steps
        else:
            self.steps = self.search_steps
            
        self.current_step_idx = 0
        self.auto_playing = False
        
        if self.steps:
            self.step_slider.config(from_=0, to=len(self.steps) - 1)
            self.step_slider.set(0)
            self.current_board_state = self.steps[0].current_node.state
            self.show_current_step()
        self.update_control_states()

    def show_current_step(self):
        """Hiển thị bước hiện tại lên bàn cờ và Text log bên phải."""
        if not self.steps or self.current_step_idx < 0:
            return
            
        step = self.steps[self.current_step_idx]
        
        # Vẽ lại bàn cờ của bước này
        self.draw_custom_board(step.current_node.state, step)
        
        # Nếu đang ở chế độ xem lời giải (solution path)
        if self.view_mode_var.get() == "solution":
            log_lines = []
            note_str = f" ({step.note})" if step.note else ""
            
            log_lines.append("==================================================")
            log_lines.append(f"BƯỚC LỜI GIẢI {step.step}{note_str}")
            log_lines.append("==================================================")
            log_lines.append("")
            
            log_lines.append("TRẠNG THÁI BÀN CỜ:")
            log_lines.append(format_state_matrix(step.current_node.state))
            log_lines.append("")
            self.append_csp_color_legend(log_lines)

            if self.current_step_idx > 0:
                prev_state = self.result.solution_path[self.current_step_idx - 1].state
                log_lines.append("BẢNG TRƯỚC:")
                log_lines.append(format_state_matrix(prev_state))
                log_lines.append("")

            if self.current_step_idx < len(self.result.solution_path) - 1:
                next_state = self.result.solution_path[self.current_step_idx + 1].state
                log_lines.append("BẢNG TIẾP THEO:")
                log_lines.append(format_state_matrix(next_state))
                log_lines.append("")
            
            # Show path of moves so far
            path_so_far = self.result.solution_path[:self.current_step_idx + 1]
            moves_so_far = [n.move for n in path_so_far if n.move is not None]
            log_lines.append("CÁC BƯỚC DI CHUYỂN ĐÃ QUA:")
            if not moves_so_far:
                log_lines.append("Bắt đầu")
            else:
                log_lines.append(" -> ".join(moves_so_far))
            log_lines.append("")
            
            # Show remaining moves
            remaining_path = self.result.solution_path[self.current_step_idx + 1:]
            remaining_moves = [n.move for n in remaining_path if n.move is not None]
            log_lines.append("CÁC BƯỚC DI CHUYỂN TIẾP THEO:")
            if not remaining_moves:
                log_lines.append("Đã đạt trạng thái đích!")
            else:
                log_lines.append(" -> ".join(remaining_moves))
            log_lines.append("")
            
            # Nếu là bước cuối cùng
            is_last_step = (self.current_step_idx == len(self.steps) - 1)
            if is_last_step:
                log_lines.append("==================================================")
                log_lines.append("KẾT QUẢ CHUNG CUỘC:")
                log_lines.append(f"Thuật toán: {self.result.algorithm}")
                log_lines.append(f"Tổng số bước di chuyển: {self.result.total_steps}")
                log_lines.append(f"Tổng chi phí (g): {self.result.total_cost}")
                log_lines.append(f"Thời gian tính toán: {self.result.time_taken:.5f} giây")
                log_lines.append("==================================================")
                
            self.text_log.config(state=NORMAL)
            self.text_log.delete("1.0", tk.END)
            self.text_log.insert(tk.END, "\n".join(log_lines))
            self.text_log.config(state=DISABLED)
            self.text_log.see("1.0")
            return

        # Nếu ở chế độ duyệt cây tìm kiếm (search tree mode)
        log_lines = []
        note_str = f" ({step.note})" if step.note else ""
        
        log_lines.append("==================================================")
        log_lines.append(f"STEP {step.step}{note_str}")
        log_lines.append("==================================================")
        log_lines.append("")
        self.append_csp_color_legend(log_lines)
        
        log_lines.append("NODE:")
        log_lines.append(format_node_matrix(step.current_node))
        log_lines.append("")
        
        log_lines.append("FRONTIER:")
        if not step.frontier:
            log_lines.append("(empty)")
        else:
            if len(step.frontier) <= 10:
                for node in step.frontier:
                    log_lines.append(format_node_matrix(node))
                    log_lines.append("")
            else:
                for node in step.frontier[:10]:
                    log_lines.append(format_node_matrix(node))
                    log_lines.append("")
                # Rút gọn phần còn lại
                rem = step.frontier[10:]
                log_lines.append(f"+ {len(rem)} more nodes in frontier:")
                concise_parts = []
                for node in rem:
                    parent_part = f"{node.parent_id},{node.move},{node.cost}" if node.parent_id else "Start"
                    concise_parts.append(f"{node.id}=({parent_part})")
                log_lines.append(", ".join(concise_parts))
                log_lines.append("")
                
        log_lines.append("EXPLORED:")
        if not step.explored:
            log_lines.append("(empty)")
        else:
            if len(step.explored) <= 10:
                for node in step.explored:
                    log_lines.append(format_explored_matrix(node))
                    log_lines.append("")
            else:
                earlier = step.explored[:-10]
                earlier_names = ", ".join(node.id for node in earlier)
                log_lines.append(f"... (earlier nodes: {earlier_names})")
                log_lines.append("")
                for node in step.explored[-10:]:
                    log_lines.append(format_explored_matrix(node))
                    log_lines.append("")
                    
        # Nếu node hiện tại chính là đích và là bước cuối, in RESULT
        is_last_step = (self.current_step_idx == len(self.steps) - 1)
        if is_last_step and self.result.success:
            log_lines.append("==================================================")
            log_lines.append("RESULT:")
            log_lines.append("Goal found!")
            log_lines.append(f"Algorithm: {self.result.algorithm}")
            path_str = " -> ".join(n.id for n in self.result.solution_path)
            log_lines.append(f"Path nodes: {path_str}")
            moves_str = " -> ".join(self.result.moves)
            log_lines.append(f"Moves: {moves_str}")
            log_lines.append(f"Total steps: {self.result.total_steps}")
            log_lines.append(f"Total cost: {self.result.total_cost}")
            log_lines.append(f"Expanded nodes: {self.result.expanded_nodes}")
            log_lines.append(f"Generated nodes: {self.result.generated_nodes}")
            log_lines.append(f"Time taken: {self.result.time_taken:.5f} seconds")
            log_lines.append("==================================================")
            
        # Cập nhật Text widget
        self.text_log.config(state=NORMAL)
        self.text_log.delete("1.0", tk.END)
        self.text_log.insert(tk.END, "\n".join(log_lines))
        self.text_log.config(state=DISABLED)
        
        # Tự động cuộn lên đầu
        self.text_log.see("1.0")
        
    def click_next_step(self):
        """Chuyển sang bước tiếp theo."""
        if not self.steps:
            return
        if self.current_step_idx < len(self.steps) - 1:
            self.current_step_idx += 1
            self.step_slider.set(self.current_step_idx)
            self.current_board_state = self.steps[self.current_step_idx].current_node.state
            self.show_current_step()
        else:
            self.auto_playing = False
            messagebox.showinfo("Hoàn tất", "Đã đạt tới bước cuối cùng của cây tìm kiếm.")
            
    def click_prev_step(self):
        """Lùi về bước trước đó."""
        if not self.steps:
            return
        if self.current_step_idx > 0:
            self.current_step_idx -= 1
            self.step_slider.set(self.current_step_idx)
            self.current_board_state = self.steps[self.current_step_idx].current_node.state
            self.show_current_step()
            
    def click_reset(self):
        """Quay lại bước đầu tiên (bước 0)."""
        if not self.steps:
            return
        self.auto_playing = False
        self.current_step_idx = 0
        self.step_slider.set(0)
        self.current_board_state = self.steps[0].current_node.state
        self.show_current_step()
        
    def click_auto_play(self):
        """Tự động phát liên tiếp các bước tìm kiếm."""
        if not self.steps:
            return
        if self.current_step_idx == len(self.steps) - 1:
            self.current_step_idx = 0
            self.step_slider.set(0)
            
        self.auto_playing = True
        self.run_auto_step_loop()
        
    def run_auto_step_loop(self):
        if not self.auto_playing:
            return
            
        if self.current_step_idx < len(self.steps) - 1:
            self.current_step_idx += 1
            self.step_slider.set(self.current_step_idx)
            self.current_board_state = self.steps[self.current_step_idx].current_node.state
            self.show_current_step()
            self.root.after(self.play_speed, self.run_auto_step_loop)
        else:
            self.auto_playing = False
            self.status_var.set("Hoàn tất tự động phát.")
            
    def click_pause(self):
        """Tạm dừng quá trình tự động phát."""
        self.auto_playing = False
        self.status_var.set("Tạm dừng tự động phát.")
        
    def slide_step(self, val):
        """Xử lý sự kiện kéo thanh trượt tiến trình bước."""
        if not self.steps:
            return
        idx = int(float(val))
        if 0 <= idx < len(self.steps):
            self.current_step_idx = idx
            self.current_board_state = self.steps[idx].current_node.state
            self.show_current_step()
            
    def change_speed(self, val):
        """Thay đổi tốc độ tự động phát từ thanh trượt."""
        self.play_speed = int(float(val))
        self.lbl_speed_val.config(text=f"{self.play_speed}ms")
        
    def change_theme(self, event=None):
        """Thay đổi giao diện màu sắc của ứng dụng thông qua Combobox."""
        new_theme = self.theme_combo.get()
        tb.Style().theme_use(new_theme)
        # Vẽ lại bàn cờ để cập nhật màu sắc
        self.draw_custom_board(self.current_board_state)
        
    def generate_board(self, difficulty):
        """Tự động sinh và nạp bàn cờ ngẫu nhiên có lời giải."""
        self.auto_playing = False
        state = generate_random_puzzle(difficulty)
        
        self.entry_start.delete(0, tk.END)
        self.entry_start.insert(0, " ".join(str(x) for x in state))
        
        self.current_board_state = state
        self.draw_custom_board(state)
        self.reset_manual_play()
        
        self.steps = []
        self.current_step_idx = -1
        self.result = None
        self.update_control_states()
        self.status_var.set(f"Đã sinh cấu hình 8-Puzzle mới ({difficulty}).")
        
    def reset_manual_play(self):
        """Khôi phục đếm bước chơi thủ công."""
        self.manual_moves = 0
        self.lbl_manual_status.config(text="Số bước đi bằng tay: 0")
        
        start_state = parse_state(self.entry_start.get())
        if start_state and len(start_state) == 9:
            self.current_board_state = start_state
            self.draw_custom_board(start_state)
            
    def click_tile(self, r, c):
        """Xử lý trượt ô số khi người dùng chơi thủ công."""
        if self.auto_playing:
            return
            
        blank_idx = self.current_board_state.index(0)
        blank_r, blank_c = blank_idx // 3, blank_idx % 3
        
        # Kiểm tra ô được click có liền kề ô trống không
        if (abs(r - blank_r) == 1 and c == blank_c) or (r == blank_r and abs(c - blank_c) == 1):
            clicked_idx = r * 3 + c
            lst = list(self.current_board_state)
            lst[blank_idx], lst[clicked_idx] = lst[clicked_idx], lst[blank_idx]
            self.current_board_state = tuple(lst)
            
            self.manual_moves += 1
            self.lbl_manual_status.config(text=f"Số bước đi bằng tay: {self.manual_moves}")
            self.draw_custom_board(self.current_board_state)
            
            # Xoá trạng thái trực quan hóa tìm kiếm
            self.steps = []
            self.current_step_idx = -1
            self.update_control_states()
            
            goal_state = parse_state(self.entry_goal.get())
            if self.current_board_state == goal_state:
                messagebox.showinfo("Chiến thắng!", f"Chúc mừng! Bạn đã tự giải thành công trong {self.manual_moves} bước!")
                self.status_var.set(f"Đã giải xong bằng tay trong {self.manual_moves} bước.")
                
    def get_hint(self):
        """Gợi ý bước đi tiếp theo bằng cách chạy thuật toán A* (Manhattan)."""
        start = self.current_board_state
        goal = parse_state(self.entry_goal.get())
        
        if start == goal:
            messagebox.showinfo("Gợi Ý", "Trạng thái hiện tại đã khớp với trạng thái đích rồi!")
            return
            
        self.status_var.set("Đang tìm gợi ý tối ưu...")
        self.root.update()
        
        result = run_astar(start, goal, cost_mode=1, heuristic_mode=1)
        if result.success and len(result.solution_path) > 1:
            next_state = result.solution_path[1].state
            blank_idx_next = next_state.index(0)
            moved_val = start[blank_idx_next]
            
            r = blank_idx_next // 3
            c = blank_idx_next % 3
            
            # Highlight ô cần di chuyển màu Cam (Orange)
            self.tiles[r][c].config(bg="#E67E22", fg="#FFFFFF")
            self.status_var.set(f"Gợi ý: Hãy di chuyển ô số {moved_val} (tô cam) vào ô trống.")
        else:
            messagebox.showwarning("Lỗi gợi ý", "Không tìm thấy lời giải để đưa ra gợi ý.")
            self.status_var.set("Không thể tìm thấy gợi ý.")
            
    def click_compare_all(self):
        """Khởi chạy tất cả thuật toán để so sánh hiệu năng trên Thread riêng."""
        start_txt = self.entry_start.get()
        goal_txt = self.entry_goal.get()
        
        start = parse_state(start_txt)
        goal = parse_state(goal_txt)
        
        if start is None or goal is None:
            messagebox.showwarning("Lỗi", "Vui lòng cấu hình trạng thái hợp lệ trước.")
            return
            
        ok, msg = validate_state(start)
        if not ok:
            messagebox.showwarning("Lỗi", f"Start State không hợp lệ: {msg}")
            return
            
        ok, msg = validate_state(goal)
        if not ok:
            messagebox.showwarning("Lỗi", f"Goal State không hợp lệ: {msg}")
            return
            
        if not is_solvable(start, goal):
            messagebox.showerror("Không thể giải", "Bài toán này không thể giải được!")
            return
            
        self.btn_compare_all.config(state=DISABLED)
        self.lbl_comp_status.config(text="Đang tính toán so sánh các thuật toán...")
        self.root.update()
        
        # Xoá kết quả cũ trong bảng
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        threading.Thread(target=self.run_comparison_worker, args=(start, goal), daemon=True).start()
        
    def run_comparison_worker(self, start, goal):
        results = []
        
        algos = [
            ("BFS", lambda s, g: run_bfs(s, g)),
            ("DFS (Limit=20)", lambda s, g: run_dfs(s, g, depth_limit=20)),
            ("IDS (Max Depth=20)", lambda s, g: run_ids(s, g, max_depth=20)),
            ("UCS (Cost Mode=2)", lambda s, g: run_ucs(s, g, cost_mode=2)),
            ("A* (Manhattan, Cost=2)", lambda s, g: run_astar(s, g, cost_mode=2, heuristic_mode=1)),
            ("A* (Misplaced, Cost=2)", lambda s, g: run_astar(s, g, cost_mode=2, heuristic_mode=2)),
            ("Simple Hill Climbing", lambda s, g: run_simple_hill_climbing(s, g, heuristic_mode=1, max_iterations=100)),
            ("Steepest Ascent Hill Climbing", lambda s, g: run_steepest_ascent_hill_climbing(s, g, heuristic_mode=1, max_iterations=100)),
            ("Stochastic Hill Climbing", lambda s, g: run_stochastic_hill_climbing(s, g, heuristic_mode=1, max_iterations=100)),
            ("Random Restart Hill Climbing", lambda s, g: run_random_restart_hill_climbing(s, g, heuristic_mode=1, max_iterations=100, restarts=5)),
            ("Local Beam Search (k=3)", lambda s, g: run_local_beam_search(s, g, beam_width=3, max_iterations=100, heuristic_mode=1)),
            ("CSP: Path Consistency", lambda s, g: run_csp_path_consistency_puzzle(s, g, depth_limit=20)),
            ("CSP: Global Constraints", lambda s, g: run_csp_global_constraints_puzzle(s, g, depth_limit=40)),
            ("CSP: Backtracking Search", lambda s, g: run_csp_backtracking_search_puzzle(s, g, depth_limit=10)),
            ("CSP: Forward Checking", lambda s, g: run_csp_backtracking_puzzle(s, g, forward_checking=True, depth_limit=10)),
            ("CSP: AC-3", lambda s, g: run_csp_ac3_puzzle(s, g, depth_limit=20)),
            ("CSP: Min-Conflicts", lambda s, g: run_csp_min_conflicts_puzzle(s, g, max_steps=100)),
            ("Complex Env: AND-OR Search", lambda s, g: run_and_or_search_puzzle(s, g, max_depth=5)),
            ("Complex Env: No Observation", lambda s, g: run_no_observation_search_puzzle(s, g, max_depth=10)),
            ("Complex Env: Partial Observation", lambda s, g: run_partially_observable_search_puzzle(s, g, max_steps=12))
        ]
        
        for name, func in algos:
            self.root.after(0, lambda n=name: self.lbl_comp_status.config(text=f"Đang chạy {n}..."))
            t0 = time.perf_counter()
            try:
                res = func(start, goal)
            except Exception as e:
                res = SearchResult(False, name, [], [], [], 0, 0, 0, 0, 0, 0.0, str(e))
            t1 = time.perf_counter()
            res.time_taken = t1 - t0
            results.append((name, res))
            
        self.root.after(0, lambda: self.comparison_finished(results))
        
    def comparison_finished(self, results):
        self.btn_compare_all.config(state=NORMAL)
        self.lbl_comp_status.config(text="Đã hoàn thành so sánh!")
        
        for name, res in results:
            success_str = "Thành công" if res.success else "Thất bại"
            if res.success:
                steps_str = str(res.total_steps)
                cost_str = str(res.total_cost)
            else:
                steps_str = "-"
                cost_str = "-"
                
            time_ms = f"{res.time_taken * 1000:.2f}"
            
            self.tree.insert("", END, values=(
                name,
                success_str,
                steps_str,
                cost_str,
                f"{res.expanded_nodes:,}",
                f"{res.generated_nodes:,}",
                time_ms
            ))


# =============================================================================
# KHỞI CHẠY CHƯƠNG TRÌNH
# =============================================================================

def main():
    root = tb.Window(themename="darkly", title="8-Puzzle Search Visualizer (Upgraded UI)")
    root.geometry("1100x800")
    root.minsize(1000, 750)
    app = SearchVisualizerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
