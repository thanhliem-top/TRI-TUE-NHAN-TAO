
import os
import time
import heapq
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from collections import deque

# Giới hạn số lượng node sinh ra tối đa để tránh treo máy
MAX_NODES = 50000

# =============================================================================
# CẤU TRÚC DỮ LIỆU CHÍNH & THUẬT TOÁN (TƯƠNG TỰ BẢN CONSOLE)
# =============================================================================

class SearchNode:
    """Đại diện cho một nút trong cây tìm kiếm."""
    def __init__(self, state, parent=None, parent_id=None, move=None, depth=0, cost=0, node_id="", gen_order=0):
        self.state = state          # Trạng thái bàn cờ dạng tuple 9 phần tử
        self.parent = parent        # Con trỏ tham chiếu đến nút cha
        self.parent_id = parent_id  # Tên định danh của nút cha
        self.move = move            # Hướng di chuyển từ cha (L, R, U, D)
        self.depth = depth          # Độ sâu của nút
        self.cost = cost            # Tổng chi phí g(n) từ Start
        self.id = node_id           # Tên duy nhất (A, B, C, ..., Z, N27, N28, ...)
        self.gen_order = gen_order  # Thứ tự sinh ra để sắp xếp khi chi phí bằng nhau

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

# =============================================================================
# HÀM ĐỊNH DẠNG TEXT ĐỂ IN LÊN SCROLLABLE TEXT WIDGET
# =============================================================================

def format_node_matrix(node):
    """Trả về chuỗi biểu diễn nút dạng: Tên = (Cha, Hướng, ChiPhí) + ma trận 3x3."""
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

# =============================================================================
# LỚP GIAO DIỆN CHÍNH (TKINTER APP)
# =============================================================================

class SearchVisualizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("8-Puzzle Search Visualizer (Tkinter GUI)")
        self.root.geometry("900x700")
        self.root.minsize(850, 650)
        
        # Biến quản lý trạng thái
        self.steps = []
        self.current_step_idx = -1
        self.result = None
        self.auto_playing = False
        
        # Trạng thái start/goal mặc định
        self.default_start = (1, 2, 3, 4, 0, 6, 7, 5, 8)
        self.default_goal = (1, 2, 3, 4, 5, 6, 7, 8, 0)
        
        # Thiết lập giao diện
        self.create_widgets()
        self.load_example_state()
        
    def create_widgets(self):
        # ---------------------------------------------------------------------
        # TOP PANEL: Nhập Start State / Goal State
        # ---------------------------------------------------------------------
        top_frame = tk.LabelFrame(self.root, text="Thiết lập trạng thái ban đầu", padx=10, pady=5)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        tk.Label(top_frame, text="Start state:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.entry_start = tk.Entry(top_frame, width=25)
        self.entry_start.grid(row=0, column=1, padx=5)
        self.entry_start.insert(0, "1 2 3 4 0 6 7 5 8")
        
        tk.Label(top_frame, text="Goal state:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.entry_goal = tk.Entry(top_frame, width=25)
        self.entry_goal.grid(row=0, column=3, padx=5)
        self.entry_goal.insert(0, "1 2 3 4 5 6 7 8 0")
        
        btn_load = tk.Button(top_frame, text="Load Example", command=self.load_example_state)
        btn_load.grid(row=0, column=4, padx=15)
        
        # ---------------------------------------------------------------------
        # MIDDLE PANEL: Chia làm 2 cột (Trái: Bàn cờ, Phải: Text Log)
        # ---------------------------------------------------------------------
        mid_frame = tk.Frame(self.root)
        mid_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Cột trái: Bàn cờ 3x3
        left_panel = tk.LabelFrame(mid_frame, text="Bàn cờ hiện tại (Current Board)", padx=10, pady=10, width=320)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        
        # Khung chứa ma trận 3x3
        self.board_frame = tk.Frame(left_panel, bg="#B0B0B0", bd=2, relief=tk.SOLID)
        self.board_frame.pack(expand=True)
        
        self.tiles = []
        for r in range(3):
            row_tiles = []
            for c in range(3):
                # Tạo label đại diện cho ô số trên bàn cờ
                lbl = tk.Label(
                    self.board_frame, text="", font=("Helvetica", 28, "bold"),
                    width=5, height=2, bd=1, relief=tk.RAISED, bg="#FFFFFF", fg="#333333"
                )
                lbl.grid(row=r, column=c, padx=3, pady=3)
                row_tiles.append(lbl)
            self.tiles.append(row_tiles)
            
        # Cột phải: Scrollable Text Widget in chi tiết bước chạy
        right_panel = tk.LabelFrame(mid_frame, text="Chi tiết các bước tìm kiếm (Step Log)", padx=10, pady=10)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Dùng một Text widget kèm Scrollbar
        self.scrollbar = tk.Scrollbar(right_panel)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Font Monospace: Consolas 11 hoặc Courier New 11
        self.text_log = tk.Text(
            right_panel, font=("Consolas", 11), wrap=tk.WORD,
            yscrollcommand=self.scrollbar.set, bg="#FCFCFC", fg="#111111"
        )
        self.text_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.text_log.yview)
        
        # Mặc định khoá Text widget không cho chỉnh sửa
        self.text_log.config(state=tk.DISABLED)
        
        # ---------------------------------------------------------------------
        # BOTTOM PANEL: Chứa Tab và Nút Điều Khiển
        # ---------------------------------------------------------------------
        bottom_frame = tk.Frame(self.root, pady=5)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        # 1. ttk.Notebook cho 4 thuật toán
        self.notebook = ttk.Notebook(bottom_frame)
        self.notebook.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        # Tab BFS
        self.tab_bfs = tk.Frame(self.notebook, padx=10, pady=10)
        self.notebook.add(self.tab_bfs, text="BFS")
        tk.Label(self.tab_bfs, text="Thuật toán Breadth-First Search. Không cần cấu hình thêm.").pack(anchor=tk.W)
        
        # Tab DFS
        self.tab_dfs = tk.Frame(self.notebook, padx=10, pady=10)
        self.notebook.add(self.tab_dfs, text="DFS")
        tk.Label(self.tab_dfs, text="Depth Limit:").pack(side=tk.LEFT, padx=5)
        self.entry_dfs_limit = tk.Entry(self.tab_dfs, width=8)
        self.entry_dfs_limit.pack(side=tk.LEFT, padx=5)
        self.entry_dfs_limit.insert(0, "20")
        
        # Tab IDS
        self.tab_ids = tk.Frame(self.notebook, padx=10, pady=10)
        self.notebook.add(self.tab_ids, text="IDS")
        tk.Label(self.tab_ids, text="Max Depth:").pack(side=tk.LEFT, padx=5)
        self.entry_ids_max = tk.Entry(self.tab_ids, width=8)
        self.entry_ids_max.pack(side=tk.LEFT, padx=5)
        self.entry_ids_max.insert(0, "20")
        
        # Tab UCS
        self.tab_ucs = tk.Frame(self.notebook, padx=10, pady=10)
        self.notebook.add(self.tab_ucs, text="UCS")
        tk.Label(self.tab_ucs, text="Chế độ tính chi phí (Cost Mode):").pack(side=tk.LEFT, padx=5)
        self.ucs_cost_mode_var = tk.IntVar(value=2)  # Mặc định moved tile cost
        tk.Radiobutton(self.tab_ucs, text="1. Step cost = 1", variable=self.ucs_cost_mode_var, value=1).pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(self.tab_ucs, text="2. Moved tile cost", variable=self.ucs_cost_mode_var, value=2).pack(side=tk.LEFT, padx=5)
        
        # 2. Khung nút bấm điều khiển
        ctrl_frame = tk.Frame(bottom_frame)
        ctrl_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        self.btn_run = tk.Button(ctrl_frame, text="Run Search", font=("Helvetica", 10, "bold"), bg="#D9EAD3", fg="#274E13", width=12, command=self.click_run_search)
        self.btn_run.pack(side=tk.LEFT, padx=3)
        
        self.btn_prev = tk.Button(ctrl_frame, text="Previous Step", width=12, command=self.click_prev_step)
        self.btn_prev.pack(side=tk.LEFT, padx=3)
        
        self.btn_next = tk.Button(ctrl_frame, text="Next Step", width=12, command=self.click_next_step)
        self.btn_next.pack(side=tk.LEFT, padx=3)
        
        self.btn_auto = tk.Button(ctrl_frame, text="Auto Play", bg="#CFE2F3", fg="#0B5394", width=12, command=self.click_auto_play)
        self.btn_auto.pack(side=tk.LEFT, padx=3)
        
        self.btn_pause = tk.Button(ctrl_frame, text="Pause", bg="#FCE5CD", fg="#B45F06", width=12, command=self.click_pause)
        self.btn_pause.pack(side=tk.LEFT, padx=3)
        
        self.btn_reset = tk.Button(ctrl_frame, text="Reset", width=12, command=self.click_reset)
        self.btn_reset.pack(side=tk.LEFT, padx=3)
        
        self.btn_clear = tk.Button(ctrl_frame, text="Clear Log", width=12, command=self.click_clear_log)
        self.btn_clear.pack(side=tk.LEFT, padx=3)
        
        # Trạng thái ban đầu: Vô hiệu các nút điều khiển bước khi chưa tìm kiếm
        self.update_control_states()
        
        # 3. Thanh trạng thái dưới cùng
        self.status_var = tk.StringVar(value="Sẵn sàng. Vui lòng nhấn Run Search để thực thi tìm kiếm.")
        self.lbl_status = tk.Label(bottom_frame, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, font=("Helvetica", 9, "italic"))
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X, pady=2)
        
    # =============================================================================
    # XỬ LÝ HÀNH VI CỦA NÚT BẤM
    # =============================================================================
    
    def load_example_state(self):
        """Khôi phục trạng thái Start & Goal ví dụ mặc định."""
        self.entry_start.delete(0, tk.END)
        self.entry_start.insert(0, "1 2 3 4 0 6 7 5 8")
        
        self.entry_goal.delete(0, tk.END)
        self.entry_goal.insert(0, "1 2 3 4 5 6 7 8 0")
        
        # Hiển thị bàn cờ start lên 3x3
        self.draw_custom_board(self.default_start)
        self.click_clear_log()
        self.status_var.set("Đã tải trạng thái mặc định của ví dụ.")
        
    def draw_custom_board(self, state):
        """Vẽ trạng thái state lên bàn cờ hiển thị 3x3 ở cột trái."""
        for r in range(3):
            for c in range(3):
                val = state[r*3 + c]
                if val == 0:
                    self.tiles[r][c].config(text="", bg="#D0D0D0")
                else:
                    self.tiles[r][c].config(text=str(val), bg="#FFFFFF")
                    
    def click_clear_log(self):
        """Xoá toàn bộ log và các bước chạy hiện tại."""
        self.auto_playing = False
        self.steps = []
        self.current_step_idx = -1
        self.result = None
        
        self.text_log.config(state=tk.NORMAL)
        self.text_log.delete("1.0", tk.END)
        self.text_log.config(state=tk.DISABLED)
        
        # Cập nhật lại bàn cờ theo Start State hiện tại
        start_state = parse_state(self.entry_start.get())
        if start_state and len(start_state) == 9:
            self.draw_custom_board(start_state)
            
        self.update_control_states()
        self.status_var.set("Đã xoá sạch log. Trạng thái sẵn sàng.")
        
    def update_control_states(self):
        """Bật/tắt các nút điều khiển tùy thuộc vào việc đã chạy thuật toán thành công chưa."""
        has_steps = len(self.steps) > 0
        state = tk.NORMAL if has_steps else tk.DISABLED
        
        self.btn_prev.config(state=state)
        self.btn_next.config(state=state)
        self.btn_auto.config(state=state)
        self.btn_pause.config(state=state)
        self.btn_reset.config(state=state)

    def click_run_search(self):
        """Thực thi chạy thuật toán tìm kiếm khi click Run Search."""
        # Dừng tự động phát nếu có
        self.auto_playing = False
        
        # 1. Thu thập dữ liệu và chuyển đổi
        start_txt = self.entry_start.get()
        goal_txt = self.entry_goal.get()
        
        start = parse_state(start_txt)
        goal = parse_state(goal_txt)
        
        if start is None or goal is None:
            messagebox.showwarning("Lỗi định dạng", "Trạng thái nhập không hợp lệ. Vui lòng nhập 9 số cách nhau bằng khoảng trắng.")
            return
            
        # 2. Kiểm tra tính hợp lệ
        ok, msg = validate_state(start)
        if not ok:
            messagebox.showwarning("Lỗi Start State", f"Start State không hợp lệ: {msg}")
            return
            
        ok, msg = validate_state(goal)
        if not ok:
            messagebox.showwarning("Lỗi Goal State", f"Goal State không hợp lệ: {msg}")
            return
            
        # 3. Kiểm tra tính giải được
        if not is_solvable(start, goal):
            messagebox.showerror("Không thể giải", "This puzzle is not solvable.\nHai trạng thái có tính chẵn lẻ của số lượng cặp nghịch thế không khớp nhau.")
            self.status_var.set("This puzzle is not solvable.")
            self.click_clear_log()
            return
            
        # 4. Xác định thuật toán từ Tab đang được chọn
        tab_idx = self.notebook.index(self.notebook.select())
        
        self.status_var.set("Đang chạy tìm kiếm...")
        self.root.update()
        
        start_time = time.perf_counter()
        
        if tab_idx == 0:  # BFS
            result = run_bfs(start, goal)
        elif tab_idx == 1:  # DFS
            # Đọc depth limit
            try:
                limit = int(self.entry_dfs_limit.get())
            except ValueError:
                limit = 20
                self.entry_dfs_limit.delete(0, tk.END)
                self.entry_dfs_limit.insert(0, "20")
            result = run_dfs(start, goal, depth_limit=limit)
        elif tab_idx == 2:  # IDS
            # Đọc max depth
            try:
                max_d = int(self.entry_ids_max.get())
            except ValueError:
                max_d = 20
                self.entry_ids_max.delete(0, tk.END)
                self.entry_ids_max.insert(0, "20")
            result = run_ids(start, goal, max_depth=max_d)
        else:  # UCS
            cost_mode = self.ucs_cost_mode_var.get()
            result = run_ucs(start, goal, cost_mode=cost_mode)
            
        end_time = time.perf_counter()
        result.time_taken = end_time - start_time
        
        # 5. Lưu kết quả
        self.result = result
        self.steps = result.steps
        self.current_step_idx = 0
        
        # 6. Cập nhật giao diện
        self.update_control_states()
        self.show_current_step()
        
        if result.success:
            self.status_var.set(f"Đã tìm thấy Goal! Tổng số bước di chuyển: {result.total_steps}. Tổng cost: {result.total_cost}. Kích thước Frontier max: {result.max_frontier_size}")
        else:
            self.status_var.set(f"Tìm kiếm thất bại: {result.message}")
            
    def show_current_step(self):
        """Hiển thị bước hiện tại lên bàn cờ và Text log bên phải."""
        if not self.steps or self.current_step_idx < 0:
            return
            
        step = self.steps[self.current_step_idx]
        
        # 1. Vẽ lại bàn cờ hiện tại của bước
        self.draw_custom_board(step.current_node.state)
        
        # 2. Xây dựng chuỗi văn bản log cho bước hiện tại
        log_lines = []
        note_str = f" ({step.note})" if step.note else ""
        
        log_lines.append("==================================================")
        log_lines.append(f"STEP {step.step}{note_str}")
        log_lines.append("==================================================")
        log_lines.append("")
        
        log_lines.append("NODE:")
        log_lines.append(format_node_matrix(step.current_node))
        log_lines.append("")
        
        log_lines.append("FRONTIER:")
        if not step.frontier:
            log_lines.append("(empty)")
        else:
            # Sắp xếp các node theo ma trận 3x3
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
                    
        # 3. Nếu node hiện tại chính là đích và là bước cuối, in RESULT
        # Kiểm tra xem đây có phải là bước tìm kiếm cuối cùng và thành công không
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
        self.text_log.config(state=tk.NORMAL)
        self.text_log.delete("1.0", tk.END)
        self.text_log.insert(tk.END, "\n".join(log_lines))
        self.text_log.config(state=tk.DISABLED)
        
        # Tự động scroll về đầu log của bước
        self.text_log.see("1.0")

    def click_next_step(self):
        """Chuyển sang bước tiếp theo."""
        if not self.steps:
            return
        if self.current_step_idx < len(self.steps) - 1:
            self.current_step_idx += 1
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
            self.show_current_step()
            
    def click_reset(self):
        """Quay lại bước 0."""
        if not self.steps:
            return
        self.auto_playing = False
        self.current_step_idx = 0
        self.show_current_step()
        
    def click_auto_play(self):
        """Tự động chạy liên tiếp các bước."""
        if not self.steps:
            return
        if self.current_step_idx == len(self.steps) - 1:
            self.current_step_idx = 0
            
        self.auto_playing = True
        self.run_auto_step_loop()
        
    def run_auto_step_loop(self):
        """Vòng lặp không bị block sử dụng root.after()."""
        if not self.auto_playing:
            return
            
        if self.current_step_idx < len(self.steps) - 1:
            self.current_step_idx += 1
            self.show_current_step()
            # Đợi 700ms (0.7s) rồi thực thi tiếp
            self.root.after(700, self.run_auto_step_loop)
        else:
            self.auto_playing = False
            self.status_var.set("Hoàn tất tự động phát các bước.")
            
    def click_pause(self):
        """Tạm dừng quá trình tự động phát."""
        self.auto_playing = False
        self.status_var.set("Tạm dừng tự động phát.")

# =============================================================================
# KHỞI CHẠY CHƯƠNG TRÌNH
# =============================================================================

def main():
    root = tk.Tk()
    app = SearchVisualizerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
