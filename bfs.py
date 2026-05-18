import threading
import tkinter as tk
from collections import deque


MOVE_DELTAS = {
    "Trái": -1,
    "Phải": 1,
    "Trên": -3,
    "Dưới": 3,
}


class Node:
    def __init__(self, state, parent=None, move=None):
        self.state = state
        self.parent = parent
        self.move = move


def format_state(state):
    rows = []
    for i in range(0, 9, 3):
        rows.append(" ".join(str(value) for value in state[i:i + 3]))
    return "\n".join(rows)


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


def build_path(node):
    path = []
    moves = []
    while node:
        path.append(node.state)
        if node.move:
            moves.append(node.move)
        node = node.parent
    return path[::-1], moves[::-1]


def bfs(start_state, goal_state, max_trace_steps=80):
    if not is_solvable(start_state, goal_state):
        return None, 0, [], []

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
            return path, len(explored), moves, trace

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
            chosen_move = queue[0].move if queue else None
            trace.append(
                {
                    "step": len(explored),
                    "current": current_node.state,
                    "possible": successors,
                    "accepted": accepted,
                    "skipped": skipped,
                    "frontier": [(node.move, node.state) for node in queue],
                    "explored": list(explored),
                    "chosen": chosen_move,
                }
            )

    return None, len(explored), [], trace


class PuzzleGUI:
    def __init__(self, root, start_state, goal_state, algorithm_name):
        self.root = root
        self.root.title(f"8-Puzzle {algorithm_name} Solver")
        self.root.geometry("1120x720")
        self.root.configure(bg="#202938")
        self.root.minsize(980, 640)

        self.start_state = start_state
        self.goal_state = goal_state
        self.algorithm_name = algorithm_name
        self.path = []
        self.moves = []
        self.current_step = 0

        self.main_frame = tk.Frame(self.root, bg="#202938")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        self.left_frame = tk.Frame(self.main_frame, bg="#202938")
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 18))

        self.title_lbl = tk.Label(
            self.left_frame,
            text=f"8-Puzzle {self.algorithm_name}",
            font=("Segoe UI", 22, "bold"),
            bg="#202938",
            fg="#f8fafc",
        )
        self.title_lbl.pack(anchor=tk.W, pady=(0, 12))

        self.board_frame = tk.Frame(self.left_frame, bg="#334155", bd=8, relief=tk.FLAT)
        self.board_frame.pack(anchor=tk.W)

        self.tiles = []
        for i in range(3):
            row = []
            for j in range(3):
                lbl = tk.Label(
                    self.board_frame,
                    text="",
                    width=4,
                    height=2,
                    font=("Segoe UI", 34, "bold"),
                    bg="#e2e8f0",
                    fg="#0f172a",
                    relief="groove",
                    borderwidth=3,
                )
                lbl.grid(row=i, column=j, padx=4, pady=4)
                row.append(lbl)
            self.tiles.append(row)

        self.stats_lbl = tk.Label(
            self.left_frame,
            text="Trạng thái: Chờ lệnh\nSố node đã duyệt: 0\nSố bước đường đi: 0",
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
            pady=8,
        )
        self.prev_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

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
            pady=8,
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
            pady=10,
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

        self.update_grid(self.start_state)
        self.show_initial_text()

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
        self.set_detail_text(
            "Trạng thái đầu:\n\n"
            f"{format_state(self.start_state)}\n\n"
            "Trạng thái đích:\n\n"
            f"{format_state(self.goal_state)}\n\n"
            "Nhấn 'Bắt đầu giải' để xem quá trình BFS duyệt node."
        )

    def start_solving(self):
        self.solve_btn.config(state=tk.DISABLED, text="Đang giải...", bg="#64748b")
        self.prev_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)
        self.stats_lbl.config(text="Trạng thái: Đang duyệt đồ thị bằng BFS...\nVui lòng đợi...")
        self.set_detail_text("Đang tạo bảng phân tích từng bước...")
        threading.Thread(target=self.solve_in_background, daemon=True).start()

    def solve_in_background(self):
        path, explored_count, moves, trace = bfs(self.start_state, self.goal_state)
        self.root.after(0, self.show_result, path, explored_count, moves, trace)

    def show_result(self, path, explored_count, moves, trace):
        self.path = path or []
        self.moves = moves
        self.current_step = 0

        if self.path:
            self.stats_lbl.config(
                text=(
                    "Trạng thái: Đã tìm thấy!\n"
                    f"Số node đã duyệt: {explored_count}\n"
                    f"Số bước đường đi: {len(self.path) - 1}\n"
                    f"Đang xem: bước {self.current_step}"
                )
            )
            self.update_grid(self.path[0])
            self.next_btn.config(state=tk.NORMAL if len(self.path) > 1 else tk.DISABLED)
            self.set_detail_text(self.build_trace_report(trace, explored_count))
            self.solve_btn.config(state=tk.NORMAL, text="Giải lại", command=self.reset, bg="#16a34a")
        else:
            self.stats_lbl.config(
                text=(
                    "Trạng thái: Không tìm thấy lời giải!\n"
                    f"Số node đã duyệt: {explored_count}\n"
                    "Số bước đường đi: 0"
                )
            )
            self.set_detail_text("Puzzle này không có lời giải từ trạng thái đầu đến trạng thái đích.")
            self.solve_btn.config(state=tk.NORMAL, text="Thử lại", bg="#dc2626")

    def build_trace_report(self, trace, explored_count):
        lines = [
            "Trạng thái đầu:",
            "",
            format_state(self.start_state),
            "",
            "Trạng thái đích:",
            "",
            format_state(self.goal_state),
            "",
            "=" * 44,
            "",
        ]

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
                lines.append("Bỏ qua vì quay lại node đã duyệt hoặc đã có trong frontier:")
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

            lines.extend(
                [
                    "Theo BFS, lấy node vào frontier sớm nhất trước (queue FIFO).",
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
                    "BFS vẫn tiếp tục mở rộng theo nguyên tắc queue cho đến khi gặp Goal State.",
                    "",
                ]
            )

        lines.extend(
            [
                "Goal State",
                format_state(self.goal_state),
                "",
                "Đường đi tìm được:",
                " → ".join(self.moves) if self.moves else "(không có)",
                "",
                f"Tổng node đã duyệt: {explored_count}",
            ]
        )
        return "\n".join(lines)

    def update_path_controls(self):
        self.prev_btn.config(state=tk.NORMAL if self.current_step > 0 else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if self.current_step < len(self.path) - 1 else tk.DISABLED)
        self.stats_lbl.config(
            text=(
                "Trạng thái: Đã tìm thấy!\n"
                f"Số bước đường đi: {len(self.path) - 1}\n"
                f"Đang xem: bước {self.current_step}\n"
                f"Di chuyển: {self.moves[self.current_step - 1] if self.current_step > 0 else 'Start'}"
            )
        )

    def previous_path_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.update_grid(self.path[self.current_step])
            self.update_path_controls()

    def next_path_step(self):
        if self.current_step < len(self.path) - 1:
            self.current_step += 1
            self.update_grid(self.path[self.current_step])
            self.update_path_controls()

    def reset(self):
        self.path = []
        self.moves = []
        self.current_step = 0
        self.update_grid(self.start_state)
        self.prev_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)
        self.stats_lbl.config(text="Trạng thái: Chờ lệnh\nSố node đã duyệt: 0\nSố bước đường đi: 0")
        self.solve_btn.config(state=tk.NORMAL, text="Bắt đầu giải", command=self.start_solving, bg="#dc2626")
        self.show_initial_text()


if __name__ == "__main__":
    start = (2, 8, 3, 1, 6, 4, 7, 0, 5)
    goal = (1, 2, 3, 8, 0, 4, 7, 6, 5)
    root = tk.Tk()
    app = PuzzleGUI(root, start, goal, "BFS")
    root.mainloop()
