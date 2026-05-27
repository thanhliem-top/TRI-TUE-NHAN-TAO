import threading
import tkinter as tk
from collections import deque
from heapq import heappop, heappush


MOVE_DELTAS = {
    "Trái": -1,
    "Phải": 1,
    "Trên": -3,
    "Dưới": 3,
}


class Node:
    def __init__(self, state, parent=None, move=None, depth=0, cost=0, h=0, f=0):
        self.state = state
        self.parent = parent
        self.move = move
        self.depth = depth
        self.cost = cost # g(n)
        self.h = h
        self.f = f


def format_state(state):
    return "\n".join(
        " ".join(str(value) for value in state[i:i + 3])
        for i in range(0, 9, 3)
    )


def zero_position_text(state):
    idx = state.index(0)
    row, col = divmod(idx, 3)
    row_names = ["trên", "giữa", "cuối"]
    col_names = ["trái", "giữa", "phải"]
    return f"Vị trí 0 ở cột {col_names[col]} hàng {row_names[row]}."


def get_successors(state):
    successors = []
    idx = state.index(0)
    row, col = divmod(idx, 3)

    for move, delta in MOVE_DELTAS.items():
        if move == "Trên" and row > 0:
            new_idx = idx + delta
        elif move == "Dưới" and row < 2:
            new_idx = idx + delta
        elif move == "Trái" and col > 0:
            new_idx = idx + delta
        elif move == "Phải" and col < 2:
            new_idx = idx + delta
        else:
            continue

        new_state = list(state)
        new_state[idx], new_state[new_idx] = new_state[new_idx], new_state[idx]
        successors.append((tuple(new_state), move))

    return successors


def is_solvable(start_state, goal_state):
    def inversion_count(state):
        values = [value for value in state if value != 0]
        return sum(
            1
            for i in range(len(values))
            for j in range(i + 1, len(values))
            if values[i] > values[j]
        )

    return inversion_count(start_state) % 2 == inversion_count(goal_state) % 2


def is_cycle(node, state):
    current = node
    while current:
        if current.state == state:
            return True
        current = current.parent
    return False


def build_path(node):
    path = []
    moves = []
    while node:
        path.append(node.state)
        if node.move:
            moves.append(node.move)
        node = node.parent
    return path[::-1], moves[::-1]


def count_correct_tiles(state, goal_state):
    return sum(
        1
        for index, value in enumerate(state)
        if value != 0 and value == goal_state[index]
    )


def state_cost_by_correct_tiles(state, goal_state):
    return 8 - count_correct_tiles(state, goal_state)


def bfs(start_state, goal_state, max_trace_steps=80):
    if not is_solvable(start_state, goal_state):
        return None, 0, [], [], "failure"

    start_node = Node(start_state)
    queue = deque([start_node])
    frontier_states = {start_state}
    explored = set()
    trace = []

    while queue:
        current_node = queue.popleft()
        frontier_states.remove(current_node.state)
        successors = get_successors(current_node.state)
        accepted = []
        skipped = []

        if current_node.state == goal_state:
            path, moves = build_path(current_node)
            return path, len(explored), moves, trace, "solution"

        explored.add(current_node.state)

        for next_state, move in successors:
            if next_state in explored or next_state in frontier_states:
                skipped.append((move, next_state))
                continue
            child = Node(next_state, current_node, move)
            queue.append(child)
            frontier_states.add(next_state)
            accepted.append((move, next_state))

        if len(trace) < max_trace_steps:
            trace.append(
                {
                    "step": len(explored),
                    "current": current_node.state,
                    "possible": successors,
                    "accepted": accepted,
                    "skipped": skipped,
                    "frontier": [(node.move, node.state) for node in queue],
                    "explored": list(explored),
                    "chosen": queue[0].move if queue else None,
                }
            )

    return None, len(explored), [], trace, "failure"


def dfs(start_state, goal_state, max_trace_steps=80):
    if not is_solvable(start_state, goal_state):
        return None, 0, [], [], "failure"

    start_node = Node(start_state)
    stack = [start_node]
    frontier_states = {start_state}
    explored = set()
    trace = []

    while stack:
        current_node = stack.pop()
        frontier_states.remove(current_node.state)
        successors = get_successors(current_node.state)
        accepted = []
        skipped = []

        if current_node.state == goal_state:
            path, moves = build_path(current_node)
            return path, len(explored), moves, trace, "solution"

        explored.add(current_node.state)

        for next_state, move in successors:
            if next_state in explored or next_state in frontier_states:
                skipped.append((move, next_state))
                continue
            child = Node(next_state, current_node, move)
            stack.append(child)
            frontier_states.add(next_state)
            accepted.append((move, next_state))

        if len(trace) < max_trace_steps:
            trace.append(
                {
                    "step": len(explored),
                    "current": current_node.state,
                    "possible": successors,
                    "accepted": accepted,
                    "skipped": skipped,
                    "frontier": [(node.move, node.state) for node in stack],
                    "explored": list(explored),
                    "chosen": stack[-1].move if stack else None,
                }
            )

    return None, len(explored), [], trace, "failure"


def ucs(start_state, goal_state, max_trace_steps=80):
    if not is_solvable(start_state, goal_state):
        return None, 0, [], [], "failure"

    start_node = Node(start_state, cost=0)
    frontier = []
    counter = 0
    heappush(frontier, (0, counter, start_node))
    best_cost = {start_state: 0}
    explored = set()
    trace = []

    while frontier:
        current_cost, _, current_node = heappop(frontier)

        if current_node.state in explored:
            continue

        successors = get_successors(current_node.state)
        accepted = []
        skipped = []

        if current_node.state == goal_state:
            path, moves = build_path(current_node)
            return path, len(explored), moves, trace, "solution"

        explored.add(current_node.state)

        for next_state, move in successors:
            step_cost = state_cost_by_correct_tiles(next_state, goal_state)
            correct_tiles = count_correct_tiles(next_state, goal_state)
            new_cost = current_cost + step_cost
            parent_steps = current_node.depth
            if next_state in explored:
                skipped.append((move, next_state, step_cost, new_cost, correct_tiles, parent_steps))
                continue
            if new_cost >= best_cost.get(next_state, float("inf")):
                skipped.append((move, next_state, step_cost, new_cost, correct_tiles, parent_steps))
                continue

            counter += 1
            child = Node(next_state, current_node, move, current_node.depth + 1, new_cost)
            best_cost[next_state] = new_cost
            heappush(frontier, (new_cost, counter, child))
            accepted.append((move, next_state, step_cost, new_cost, correct_tiles, parent_steps))

        if len(trace) < max_trace_steps:
            active_frontier = [
                (
                    node.move,
                    node.state,
                    state_cost_by_correct_tiles(node.state, goal_state),
                    cost,
                    count_correct_tiles(node.state, goal_state),
                    node.parent.state if node.parent else None,
                    node.parent.depth if node.parent else 0,
                )
                for cost, _, node in sorted(frontier, key=lambda item: (item[0], item[1]))
                if node.state not in explored and best_cost.get(node.state) == cost
            ]
            trace.append(
                {
                    "step": len(explored),
                    "current": current_node.state,
                    "cost": current_cost,
                    "correct": count_correct_tiles(current_node.state, goal_state),
                    "possible": successors,
                    "accepted": accepted,
                    "skipped": skipped,
                    "frontier": active_frontier,
                    "explored": list(explored),
                    "chosen": active_frontier[0][0] if active_frontier else None,
                    "chosen_cost": active_frontier[0][3] if active_frontier else None,
                    "chosen_correct": active_frontier[0][4] if active_frontier else None,
                }
            )

    return None, len(explored), [], trace, "failure"


def astar(start_state, goal_state, max_trace_steps=80):
    if not is_solvable(start_state, goal_state):
        return None, 0, [], [], "failure"

    def calc_h(state):
        dist = 0
        goal_pos = {val: idx for idx, val in enumerate(goal_state)}
        for idx, val in enumerate(state):
            if val != 0:
                curr_r, curr_c = idx // 3, idx % 3
                g_idx = goal_pos[val]
                goal_r, goal_c = g_idx // 3, g_idx % 3
                dist += abs(curr_r - goal_r) + abs(curr_c - goal_c)
        return dist

    h0 = calc_h(start_state)
    start_node = Node(start_state, cost=0, h=h0, f=h0)
    frontier = []
    counter = 0
    heappush(frontier, (h0, counter, start_node))
    best_cost = {start_state: 0}
    explored = set()
    trace = []

    while frontier:
        current_f, _, current_node = heappop(frontier)
        current_g = current_node.cost

        if current_node.state in explored:
            continue

        successors = get_successors(current_node.state)
        accepted = []
        skipped = []

        if current_node.state == goal_state:
            path, moves = build_path(current_node)
            return path, len(explored), moves, trace, "solution"

        explored.add(current_node.state)

        for next_state, move in successors:
            step_cost = 1
            new_g = current_g + step_cost
            next_h = calc_h(next_state)
            new_f = new_g + next_h
            parent_steps = current_node.depth

            if next_state in explored:
                skipped.append((move, next_state, step_cost, new_g, next_h, new_f, parent_steps))
                continue
            if new_g >= best_cost.get(next_state, float("inf")):
                skipped.append((move, next_state, step_cost, new_g, next_h, new_f, parent_steps))
                continue

            counter += 1
            child = Node(next_state, current_node, move, current_node.depth + 1, new_g, h=next_h, f=new_f)
            best_cost[next_state] = new_g
            heappush(frontier, (new_f, counter, child))
            accepted.append((move, next_state, step_cost, new_g, next_h, new_f, parent_steps))

        if len(trace) < max_trace_steps:
            active_frontier = []
            for f, o, node in sorted(frontier, key=lambda item: (item[0], item[1])):
                if node.state not in explored and best_cost.get(node.state) == node.cost:
                    active_frontier.append(
                        (
                            node.move,
                            node.state,
                            1,
                            node.cost,
                            getattr(node, 'h', 0),
                            f,
                            node.parent.state if node.parent else None,
                            node.parent.depth if node.parent else 0,
                        )
                    )
            trace.append(
                {
                    "step": len(explored),
                    "current": current_node.state,
                    "g": current_g,
                    "h": calc_h(current_node.state),
                    "f": current_f,
                    "possible": successors,
                    "accepted": accepted,
                    "skipped": skipped,
                    "frontier": active_frontier,
                    "explored": list(explored),
                    "chosen": active_frontier[0][0] if active_frontier else None,
                    "chosen_g": active_frontier[0][3] if active_frontier else None,
                    "chosen_h": active_frontier[0][4] if active_frontier else None,
                    "chosen_f": active_frontier[0][5] if active_frontier else None,
                }
            )

    return None, len(explored), [], trace, "failure"


def depth_limited_search(start_state, goal_state, limit, trace, max_trace_steps):
    frontier = [Node(start_state)]
    result = "failure"
    expanded_count = 0

    while frontier:
        node = frontier.pop()

        if node.state == goal_state:
            return "solution", node, expanded_count

        possible = get_successors(node.state)
        accepted = []
        skipped_cycles = []
        cutoff_here = False

        if node.depth >= limit:
            result = "cutoff"
            cutoff_here = True
        else:
            for child_state, move in possible:
                if is_cycle(node, child_state):
                    skipped_cycles.append((move, child_state))
                    continue

                child = Node(child_state, node, move, node.depth + 1)
                frontier.append(child)
                accepted.append((move, child_state, child.depth))

        expanded_count += 1

        if len(trace) < max_trace_steps:
            trace.append(
                {
                    "limit": limit,
                    "step": len(trace) + 1,
                    "current": node.state,
                    "depth": node.depth,
                    "possible": possible,
                    "accepted": accepted,
                    "skipped_cycles": skipped_cycles,
                    "cutoff": cutoff_here,
                    "frontier": [(item.move, item.state, item.depth) for item in frontier],
                    "chosen": frontier[-1].move if frontier else None,
                }
            )

    return result, None, expanded_count


def iterative_deepening_search(start_state, goal_state, max_depth=40, max_trace_steps=120):
    if not is_solvable(start_state, goal_state):
        return None, 0, [], [], "failure"

    trace = []
    total_expanded = 0

    for depth in range(max_depth + 1):
        result, solution_node, expanded_count = depth_limited_search(
            start_state, goal_state, depth, trace, max_trace_steps
        )
        total_expanded += expanded_count

        if result != "cutoff":
            if result == "solution":
                path, moves = build_path(solution_node)
                return path, total_expanded, moves, trace, "solution"
            return None, total_expanded, [], trace, result

    return None, total_expanded, [], trace, "cutoff"


ALGORITHMS = {
    "BFS": {
        "solver": bfs,
        "description": "BFS dùng hàng đợi FIFO, lấy node vào frontier sớm nhất trước.",
    },
    "DFS": {
        "solver": dfs,
        "description": "DFS dùng stack LIFO, lấy node sinh sau cùng trước.",
    },
    "UCS": {
        "solver": ucs,
        "description": "UCS dùng priority queue; chi phí mỗi bước = 8 - số ô đúng vị trí.",
    },
    "IDS": {
        "solver": iterative_deepening_search,
        "description": "IDS chạy Depth-Limited Search nhiều lần với giới hạn tăng dần.",
    },
    "A*": {
        "solver": astar,
        "description": "A* dùng đánh giá f(n) = g(n) + h(n); g(n) = depth, h(n) = Manhattan.",
    },
}


class PuzzleGUI:
    def __init__(self, root, start_state, goal_state):
        self.root = root
        self.root.title("8-Puzzle Solver - BFS, DFS, UCS, IDS")
        self.root.geometry("1180x760")
        self.root.configure(bg="#202938")
        self.root.minsize(1040, 700)

        self.start_state = start_state
        self.goal_state = goal_state
        self.algorithm_var = tk.StringVar(value="BFS")
        self.algorithm_buttons = {}
        self.path = []
        self.moves = []
        self.current_step = 0
        self.explored_count = 0
        self.animation_job = None
        self.is_animating = False

        self.main_frame = tk.Frame(self.root, bg="#202938")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        self.left_frame = tk.Frame(self.main_frame, bg="#202938")
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 18))

        self.title_lbl = tk.Label(
            self.left_frame,
            text="8-Puzzle Solver",
            font=("Segoe UI", 22, "bold"),
            bg="#202938",
            fg="#f8fafc",
        )
        self.title_lbl.pack(anchor=tk.W, pady=(0, 10))

        algorithm_box = tk.Frame(
            self.left_frame,
            bg="#202938",
        )
        algorithm_box.pack(fill=tk.X, pady=(0, 10))

        algorithms_keys = list(ALGORITHMS.keys())
        for idx, algorithm in enumerate(algorithms_keys):
            btn = tk.Button(
                algorithm_box,
                text=algorithm,
                command=lambda name=algorithm: self.select_algorithm(name),
                font=("Segoe UI", 11, "bold"),
                bg="#334155",
                fg="#e2e8f0",
                activebackground="#475569",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                cursor="hand2",
                padx=10,
                pady=8,
            )
            btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 6) if idx < len(algorithms_keys) - 1 else 0)
            self.algorithm_buttons[algorithm] = btn

        self.board_frame = tk.Frame(self.left_frame, bg="#334155", bd=6, relief=tk.FLAT)
        self.board_frame.pack(anchor=tk.W, pady=(0, 8))

        self.tiles = []
        for i in range(3):
            row = []
            for j in range(3):
                lbl = tk.Label(
                    self.board_frame,
                    text="",
                    width=1,
                    height=1,
                    font=("Segoe UI", 28, "bold"),
                    bg="#e2e8f0",
                    fg="#0f172a",
                    relief="groove",
                    borderwidth=3,
                )
                lbl.grid(row=i, column=j, padx=3, pady=3, sticky="nsew")
                lbl.config(width=4, height=2)
                row.append(lbl)
            self.tiles.append(row)

        self.stats_lbl = tk.Label(
            self.left_frame,
            text="",
            font=("Segoe UI", 12),
            bg="#202938",
            fg="#fde68a",
            justify=tk.LEFT,
        )
        self.stats_lbl.pack(anchor=tk.W, pady=14)

        controls = tk.Frame(self.left_frame, bg="#202938")
        controls.pack(fill=tk.X, pady=(0, 10))

        self.prev_btn = tk.Button(
            controls,
            text="Bước trước",
            command=self.previous_path_step,
            state=tk.DISABLED,
            font=("Segoe UI", 11, "bold"),
            bg="#475569",
            fg="white",
            relief=tk.FLAT,
            padx=10,
            pady=6,
        )
        self.prev_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.play_btn = tk.Button(
            controls,
            text="Tự chạy",
            command=self.start_animation,
            state=tk.DISABLED,
            font=("Segoe UI", 11, "bold"),
            bg="#475569",
            fg="white",
            relief=tk.FLAT,
            padx=10,
            pady=6,
        )
        self.play_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        self.next_btn = tk.Button(
            controls,
            text="Bước sau",
            command=self.next_path_step,
            state=tk.DISABLED,
            font=("Segoe UI", 11, "bold"),
            bg="#475569",
            fg="white",
            relief=tk.FLAT,
            padx=10,
            pady=6,
        )
        self.next_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))

        self.solve_btn = tk.Button(
            self.left_frame,
            text="Bắt đầu giải",
            command=self.start_solving,
            font=("Segoe UI", 13, "bold"),
            bg="#dc2626",
            fg="white",
            activebackground="#b91c1c",
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            pady=8,
        )
        self.solve_btn.pack(fill=tk.X)

        self.right_frame = tk.Frame(self.main_frame, bg="#111827")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        text_scrollbar = tk.Scrollbar(self.right_frame)
        text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.detail_text = tk.Text(
            self.right_frame,
            wrap=tk.WORD,
            font=("Consolas", 11),
            bg="#f8fafc",
            fg="#111827",
            padx=14,
            pady=12,
            relief=tk.FLAT,
            yscrollcommand=text_scrollbar.set,
        )
        self.detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text_scrollbar.config(command=self.detail_text.yview)

        self.reset()

    @property
    def selected_algorithm(self):
        return self.algorithm_var.get()

    def select_algorithm(self, algorithm):
        self.algorithm_var.set(algorithm)
        self.reset()

    def update_algorithm_buttons(self):
        selected = self.selected_algorithm
        for algorithm, button in self.algorithm_buttons.items():
            if algorithm == selected:
                button.config(bg="#dc2626", fg="white", activebackground="#b91c1c")
            else:
                button.config(bg="#334155", fg="#e2e8f0", activebackground="#475569")

    def on_algorithm_change(self):
        self.reset()

    def update_grid(self, state):
        for i in range(9):
            row, col = divmod(i, 3)
            val = state[i]
            if val == 0:
                self.tiles[row][col].config(text="0", bg="#64748b", fg="white", relief=tk.FLAT)
            elif val == self.goal_state[i]:
                self.tiles[row][col].config(text=str(val), bg="#16a34a", fg="white", relief=tk.RAISED)
            else:
                self.tiles[row][col].config(text=str(val), bg="#2563eb", fg="white", relief=tk.RAISED)

    def set_detail_text(self, content):
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, content)
        self.detail_text.config(state=tk.DISABLED)

    def show_initial_text(self):
        algorithm = self.selected_algorithm
        self.set_detail_text(
            "Trạng thái đầu:\n\n"
            f"{format_state(self.start_state)}\n\n"
            "Trạng thái đích:\n\n"
            f"{format_state(self.goal_state)}\n\n"
            f"Thuật toán đang chọn: {algorithm}\n"
            f"{ALGORITHMS[algorithm]['description']}\n\n"
            "Nhấn 'Bắt đầu giải' để xem quá trình duyệt node."
        )

    def start_solving(self):
        self.stop_animation()
        algorithm = self.selected_algorithm
        self.solve_btn.config(state=tk.DISABLED, text="Đang giải...", bg="#64748b")
        self.prev_btn.config(state=tk.DISABLED)
        self.play_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)
        self.stats_lbl.config(text=f"Trạng thái: Đang chạy {algorithm}...\nVui lòng đợi...")
        self.set_detail_text("Đang tạo bảng phân tích từng bước...")
        threading.Thread(target=self.solve_in_background, args=(algorithm,), daemon=True).start()

    def solve_in_background(self, algorithm):
        solver = ALGORITHMS[algorithm]["solver"]
        path, explored_count, moves, trace, result = solver(self.start_state, self.goal_state)
        self.root.after(0, self.show_result, algorithm, path, explored_count, moves, trace, result)

    def show_result(self, algorithm, path, explored_count, moves, trace, result):
        self.path = path or []
        self.moves = moves
        self.explored_count = explored_count
        self.current_step = 0

        if self.path:
            self.stats_lbl.config(
                text=(
                    f"Thuật toán: {algorithm}\n"
                    "Trạng thái: Đã tìm thấy!\n"
                    f"Số node đã duyệt: {explored_count}\n"
                    f"Số bước đường đi: {len(self.path) - 1}\n"
                    f"Đang xem: bước {self.current_step}"
                )
            )
            self.update_grid(self.path[0])
            self.next_btn.config(state=tk.NORMAL if len(self.path) > 1 else tk.DISABLED)
            self.play_btn.config(state=tk.NORMAL if len(self.path) > 1 else tk.DISABLED)
            self.set_detail_text(self.build_trace_report(algorithm, trace, explored_count, result))
            self.solve_btn.config(state=tk.NORMAL, text="Giải lại", command=self.reset, bg="#16a34a")
            self.start_animation()
        else:
            self.stats_lbl.config(
                text=(
                    f"Thuật toán: {algorithm}\n"
                    f"Trạng thái: {result}\n"
                    f"Số node đã duyệt: {explored_count}\n"
                    "Số bước đường đi: 0"
                )
            )
            self.set_detail_text(self.build_trace_report(algorithm, trace, explored_count, result))
            self.solve_btn.config(state=tk.NORMAL, text="Thử lại", command=self.reset, bg="#dc2626")

    def build_trace_report(self, algorithm, trace, explored_count, result):
        if algorithm == "IDS":
            return self.build_ids_trace_report(trace, explored_count, result)
        if algorithm == "UCS":
            return self.build_ucs_trace_report(trace, explored_count, result)
        if algorithm == "A*":
            return self.build_astar_trace_report(trace, explored_count, result)
        return self.build_graph_search_trace_report(algorithm, trace, explored_count, result)

    def build_graph_search_trace_report(self, algorithm, trace, explored_count, result):
        lines = self.report_header(algorithm)

        for item in trace:
            lines.extend(
                [
                    f"Bước {item['step']}",
                    "Node hiện tại",
                    format_state(item["current"]),
                    "",
                    zero_position_text(item["current"]),
                    "",
                    "Có thể đi:",
                    *[move for _, move in item["possible"]],
                    "",
                ]
            )

            if item["skipped"]:
                lines.append("Bỏ qua vì node đã duyệt hoặc đã có trong frontier:")
                for move, state in item["skipped"]:
                    lines.extend([move, format_state(state), ""])

            lines.append("Frontier")
            if item["frontier"]:
                for move, state in item["frontier"]:
                    lines.extend([move or "Start", format_state(state), ""])
            else:
                lines.extend(["(rỗng)", ""])

            lines.append("Explored")
            for state in item["explored"]:
                lines.extend([format_state(state), ""])

            rule = (
                "Theo BFS, lấy node vào frontier sớm nhất trước (queue FIFO)."
                if algorithm == "BFS"
                else "Theo DFS, lấy node sinh cuối cùng trước (stack LIFO)."
            )
            lines.extend(
                [
                    rule,
                    f"=> Chọn node \"{item['chosen']}\"." if item["chosen"] else "=> Không còn node để chọn.",
                    "",
                    "-" * 44,
                    "",
                ]
            )

        if len(trace) >= 80:
            lines.extend(
                [
                    "Đã rút gọn phần hiển thị sau 80 bước để giao diện không quá nặng.",
                    f"{algorithm} vẫn tiếp tục mở rộng cho đến khi gặp Goal State.",
                    "",
                ]
            )

        lines.extend(self.report_footer(result, explored_count, "Tổng node đã duyệt"))
        return "\n".join(lines)

    def build_ucs_trace_report(self, trace, explored_count, result):
        lines = self.report_header("UCS")

        for item in trace:
            lines.extend(
                [
                    f"Bước {item['step']}",
                    f"Node hiện tại, g(n) = {item['cost']}",
                    f"Số ô đúng vị trí: {item['correct']}/8",
                    format_state(item["current"]),
                    "",
                    zero_position_text(item["current"]),
                    "",
                    "Có thể đi:",
                    *[move for _, move in item["possible"]],
                    "",
                ]
            )

            if item["accepted"]:
                lines.append("Các node được thêm/cập nhật vào frontier:")
                for move, state, step_cost, total_cost, correct_tiles, parent_steps in item["accepted"]:
                    lines.extend(
                        [
                            f"Trạng thái cha, số bước của cha = {parent_steps}:",
                            format_state(item["current"]),
                            "",
                            f"Trạng thái di chuyển: {move}",
                            format_state(state),
                            f"cost = 8 - {correct_tiles} = {step_cost}",
                            f"g(n) = {total_cost}",
                            "",
                        ]
                    )

            if item["skipped"]:
                lines.append("Bỏ qua vì node đã duyệt hoặc đã có đường đi chi phí tốt hơn:")
                for move, state, step_cost, total_cost, correct_tiles, parent_steps in item["skipped"]:
                    lines.extend(
                        [
                            f"Trạng thái cha, số bước của cha = {parent_steps}:",
                            format_state(item["current"]),
                            "",
                            f"Trạng thái di chuyển: {move}",
                            format_state(state),
                            f"cost = 8 - {correct_tiles} = {step_cost}",
                            f"g(n) = {total_cost}",
                            "",
                        ]
                    )

            lines.append("Frontier theo thứ tự chi phí tăng dần")
            if item["frontier"]:
                for move, state, step_cost, total_cost, correct_tiles, parent_state, parent_steps in item["frontier"]:
                    lines.extend(
                        [
                            f"Trạng thái cha, số bước của cha = {parent_steps}:",
                            format_state(parent_state) if parent_state else "(không có)",
                            "",
                            f"Trạng thái di chuyển: {move or 'Start'}",
                            format_state(state),
                            f"cost = 8 - {correct_tiles} = {step_cost}",
                            f"g(n) = {total_cost}",
                            "",
                        ]
                    )
            else:
                lines.extend(["(rỗng)", ""])

            lines.append("Explored")
            for state in item["explored"]:
                lines.extend([format_state(state), ""])

            lines.extend(
                [
                    "Cách tính: ô đúng là ô có cùng giá trị và cùng vị trí với Goal State, không tính ô 0.",
                    "Chi phí bước = 8 - số ô đúng. UCS chọn node có tổng chi phí g(n) nhỏ nhất.",
                    (
                        f"=> Chọn node \"{item['chosen']}\" với ô đúng = {item['chosen_correct']}/8, g(n) = {item['chosen_cost']}."
                        if item["chosen"]
                        else "=> Không còn node để chọn."
                    ),
                    "",
                    "-" * 44,
                    "",
                ]
            )

        if len(trace) >= 80:
            lines.extend(
                [
                    "Đã rút gọn phần hiển thị sau 80 bước để giao diện không quá nặng.",
                    "UCS vẫn tiếp tục mở rộng theo chi phí nhỏ nhất cho đến khi gặp Goal State.",
                    "",
                ]
            )

        lines.extend(self.report_footer(result, explored_count, "Tổng node đã duyệt"))
        return "\n".join(lines)

    def build_astar_trace_report(self, trace, explored_count, result):
        lines = self.report_header("A*")

        for item in trace:
            lines.extend(
                [
                    f"Bước {item['step']}",
                    f"Node hiện tại, g(n) = {item['g']}, h(n) = {item['h']}, f(n) = {item['f']}",
                    format_state(item["current"]),
                    "",
                    zero_position_text(item["current"]),
                    "",
                    "Có thể đi:",
                    *[move for _, move in item["possible"]],
                    "",
                ]
            )

            if item["accepted"]:
                lines.append("Các node được thêm/cập nhật vào frontier:")
                for move, state, step_cost, g, h, f, parent_steps in item["accepted"]:
                    lines.extend(
                        [
                            f"Trạng thái cha, số bước của cha = {parent_steps}:",
                            format_state(item["current"]),
                            "",
                            f"Trạng thái di chuyển: {move}",
                            format_state(state),
                            f"g(n) = {g}, h(n) = {h}, f(n) = {f}",
                            "",
                        ]
                    )

            if item["skipped"]:
                lines.append("Bỏ qua vì node đã duyệt hoặc đã có đường đi chi phí tốt hơn:")
                for move, state, step_cost, g, h, f, parent_steps in item["skipped"]:
                    lines.extend(
                        [
                            f"Trạng thái cha, số bước của cha = {parent_steps}:",
                            format_state(item["current"]),
                            "",
                            f"Trạng thái di chuyển: {move}",
                            format_state(state),
                            f"g(n) = {g}, h(n) = {h}, f(n) = {f}",
                            "",
                        ]
                    )

            lines.append("Frontier theo thứ tự chi phí f(n) tăng dần")
            if item["frontier"]:
                for move, state, step_cost, g, h, f, parent_state, parent_steps in item["frontier"]:
                    lines.extend(
                        [
                            f"Trạng thái cha, số bước của cha = {parent_steps}:",
                            format_state(parent_state) if parent_state else "(không có)",
                            "",
                            f"Trạng thái di chuyển: {move or 'Start'}",
                            format_state(state),
                            f"g(n) = {g}, h(n) = {h}, f(n) = {f}",
                            "",
                        ]
                    )
            else:
                lines.extend(["(rỗng)", ""])

            lines.append("Explored")
            for state in item["explored"]:
                lines.extend([format_state(state), ""])

            lines.extend(
                [
                    "Cách tính: g(n) là số bước từ Start đến node hiện tại, h(n) là khoảng cách Manhattan đến Goal State.",
                    "f(n) = g(n) + h(n). A* chọn node có f(n) nhỏ nhất.",
                    (
                        f"=> Chọn node \"{item['chosen']}\" với g(n) = {item['chosen_g']}, h(n) = {item['chosen_h']}, f(n) = {item['chosen_f']}."
                        if item["chosen"]
                        else "=> Không còn node để chọn."
                    ),
                    "",
                    "-" * 44,
                    "",
                ]
            )

        if len(trace) >= 80:
            lines.extend(
                [
                    "Đã rút gọn phần hiển thị sau 80 bước để giao diện không quá nặng.",
                    "A* vẫn tiếp tục mở rộng cho đến khi gặp Goal State.",
                    "",
                ]
            )

        lines.extend(self.report_footer(result, explored_count, "Tổng node đã duyệt"))
        return "\n".join(lines)

    def build_ids_trace_report(self, trace, explored_count, result):
        lines = self.report_header("IDS")
        lines.extend(
            [
                "ITERATIVE-DEEPENING-SEARCH",
                "for depth = 0 to infinity:",
                "    result = DEPTH-LIMITED-SEARCH(problem, depth)",
                "    if result != cutoff: return result",
                "",
                "=" * 48,
                "",
            ]
        )

        last_limit = None
        for item in trace:
            if item["limit"] != last_limit:
                last_limit = item["limit"]
                lines.extend([f"DEPTH-LIMITED-SEARCH với limit = {last_limit}", "-" * 48, ""])

            lines.extend(
                [
                    f"Bước {item['step']}",
                    f"Node hiện tại, depth = {item['depth']}",
                    format_state(item["current"]),
                    "",
                    zero_position_text(item["current"]),
                    "",
                    "Có thể đi:",
                    *[move for _, move in item["possible"]],
                    "",
                ]
            )

            if item["cutoff"]:
                lines.extend(
                    [
                        f"DEPTH(node) = {item['depth']} >= limit = {item['limit']}",
                        "=> result = cutoff, không mở rộng node này.",
                        "",
                    ]
                )
            else:
                if item["skipped_cycles"]:
                    lines.append("Bỏ qua vì IS-CYCLE(node) đúng:")
                    for move, state in item["skipped_cycles"]:
                        lines.extend([move, format_state(state), ""])

                lines.append("Các node con được thêm vào frontier:")
                if item["accepted"]:
                    for move, state, depth in item["accepted"]:
                        lines.extend([f"{move}, depth = {depth}", format_state(state), ""])
                else:
                    lines.extend(["(không có)", ""])

            lines.append("Frontier")
            if item["frontier"]:
                for move, state, depth in item["frontier"]:
                    lines.extend([f"{move or 'Start'}, depth = {depth}", format_state(state), ""])
            else:
                lines.extend(["(rỗng)", ""])

            lines.extend(
                [
                    "Frontier là stack LIFO.",
                    f"=> Node kế tiếp sẽ là \"{item['chosen']}\"." if item["chosen"] else "=> Không còn node để chọn.",
                    "",
                    "-" * 48,
                    "",
                ]
            )

        if len(trace) >= 120:
            lines.extend(["Đã rút gọn phần hiển thị sau 120 bước để giao diện không quá nặng.", ""])

        lines.extend(self.report_footer(result, explored_count, "Tổng node đã duyệt qua các depth limit"))
        return "\n".join(lines)

    def report_header(self, algorithm):
        return [
            "Trạng thái đầu:",
            "",
            format_state(self.start_state),
            "",
            "Trạng thái đích:",
            "",
            format_state(self.goal_state),
            "",
            f"Thuật toán: {algorithm}",
            ALGORITHMS[algorithm]["description"],
            "",
            "=" * 48,
            "",
        ]

    def report_footer(self, result, explored_count, explored_label):
        return [
            "Kết quả:",
            result,
            "",
            "Goal State",
            format_state(self.goal_state),
            "",
            "Đường đi tìm được:",
            " -> ".join(self.moves) if self.moves else "(không có)",
            "",
            f"{explored_label}: {explored_count}",
        ]

    def update_path_controls(self):
        self.prev_btn.config(state=tk.NORMAL if self.current_step > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.current_step < len(self.path) - 1 else tk.DISABLED)
        self.play_btn.config(state=tk.NORMAL if self.path and self.current_step < len(self.path) - 1 else tk.DISABLED)
        self.stats_lbl.config(
            text=(
                f"Thuật toán: {self.selected_algorithm}\n"
                "Trạng thái: Đã tìm thấy!\n"
                f"Số node đã duyệt: {self.explored_count}\n"
                f"Số bước đường đi: {len(self.path) - 1}\n"
                f"Đang xem: bước {self.current_step}\n"
                f"Di chuyển: {self.moves[self.current_step - 1] if self.current_step > 0 else 'Start'}"
            )
        )

    def previous_path_step(self):
        self.stop_animation()
        if self.current_step > 0:
            self.current_step -= 1
            self.update_grid(self.path[self.current_step])
            self.update_path_controls()

    def next_path_step(self):
        self.stop_animation()
        self.go_to_next_step()

    def go_to_next_step(self):
        if self.current_step < len(self.path) - 1:
            self.current_step += 1
            self.update_grid(self.path[self.current_step])
            self.update_path_controls()

    def start_animation(self):
        if not self.path or self.current_step >= len(self.path) - 1:
            return
        self.stop_animation()
        self.is_animating = True
        self.play_btn.config(state=tk.DISABLED, text="Đang chạy")
        self.prev_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)
        self.animation_job = self.root.after(600, self.animate_next_step)

    def animate_next_step(self):
        self.animation_job = None
        if not self.is_animating:
            return
        self.go_to_next_step()
        if self.current_step < len(self.path) - 1:
            self.prev_btn.config(state=tk.DISABLED)
            self.next_btn.config(state=tk.DISABLED)
            self.play_btn.config(state=tk.DISABLED, text="Đang chạy")
            self.animation_job = self.root.after(600, self.animate_next_step)
        else:
            self.stop_animation()

    def stop_animation(self):
        if self.animation_job is not None:
            self.root.after_cancel(self.animation_job)
            self.animation_job = None
        self.is_animating = False
        if hasattr(self, "play_btn"):
            self.play_btn.config(text="Tự chạy")

    def reset(self):
        self.stop_animation()
        self.path = []
        self.moves = []
        self.current_step = 0
        self.explored_count = 0
        self.update_algorithm_buttons()
        self.update_grid(self.start_state)
        self.prev_btn.config(state=tk.DISABLED)
        self.play_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)
        self.stats_lbl.config(
            text=(
                f"Thuật toán: {self.selected_algorithm}\n"
                "Trạng thái: Chờ lệnh\n"
                "Số node đã duyệt: 0\n"
                "Số bước đường đi: 0"
            )
        )
        self.solve_btn.config(
            state=tk.NORMAL,
            text="Bắt đầu giải",
            command=self.start_solving,
            bg="#dc2626",
        )
        self.show_initial_text()


if __name__ == "__main__":
    start = (2, 8, 3, 1, 6, 4, 7, 0, 5)
    goal = (1, 2, 3, 8, 0, 4, 7, 6, 5)
    root = tk.Tk()
    app = PuzzleGUI(root, start, goal)
    root.mainloop()
