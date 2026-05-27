# -*- coding: utf-8 -*-
"""
Chương trình mô phỏng bài toán 8-puzzle 3x3 với 4 thuật toán tìm kiếm: BFS, DFS, IDS, UCS.
Tác giả: Python Developer
Tệp duy nhất chạy trên terminal / console của Windows và các HĐH khác.
Chỉ sử dụng thư viện chuẩn của Python.
"""

import os
import time
import heapq
from collections import deque

# Giới hạn số lượng node sinh ra tối đa để tránh tràn bộ nhớ / treo máy
MAX_NODES = 50000

# =============================================================================
# CẤU TRÚC DỮ LIỆU CHÍNH
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
        self.gen_order = gen_order  # Thứ tự sinh ra nút này để sắp xếp khi chi phí bằng nhau
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
        self.max_frontier_size = max_frontier_size  # Kích thước frontier lớn nhất trong quá trình tìm
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

# =============================================================================
# HÀM BỔ TRỢ XỬ LÝ TRẠNG THÁI & HIỂN THỊ
# =============================================================================

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
        return False, "Invalid state. State must contain exactly 9 numbers."
    if set(state) != set(range(9)):
        return False, "Invalid state. State must contain numbers 0 to 8 exactly once."
    return True, ""

def get_inversions(state):
    """Tính số lượng cặp nghịch thế (inversions) để kiểm tra tính giải được."""
    nums = [x for x in state if x != 0]
    inv = 0
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] > nums[j]:
                inv += 1
    return inv

def is_solvable(start, goal):
    """
    Kiểm tra xem câu đố có giải được không dựa trên tính chẵn lẻ của số inversions.
    Trong 8-puzzle, vì kích thước lưới là 3x3 (chiều rộng lẻ), tính chẵn lẻ của
    số nghịch thế không thay đổi qua các bước đi hợp lệ.
    """
    return get_inversions(start) % 2 == get_inversions(goal) % 2

def pretty_board_box(state):
    """Tạo biểu diễn bàn cờ dạng khung ASCII 3x3."""
    lines = []
    lines.append("+---+---+---+")
    for i in range(3):
        row_vals = []
        for j in range(3):
            val = state[i*3 + j]
            char_val = str(val) if val != 0 else " "
            row_vals.append(char_val)
        lines.append(f"| {row_vals[0]} | {row_vals[1]} | {row_vals[2]} |")
        lines.append("+---+---+---+")
    return lines

def get_neighbors(state, move_order=('L', 'R', 'U', 'D')):
    """
    Sinh các trạng thái lân cận khi di chuyển ô trống (số 0).
    Trả về danh sách tuple: (hướng_đi, trạng_thái_mới, giá_trị_ô_di_chuyển)
    Thứ tự ưu tiên mặc định: L, R, U, D.
    """
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
            # Thực hiện tráo đổi
            lst = list(state)
            lst[blank_idx], lst[new_idx] = lst[new_idx], lst[blank_idx]
            next_state = tuple(lst)
            neighbors.append((move, next_state, moved_tile))

    return neighbors

def format_node(node):
    """Định dạng thông tin node theo mẫu trong vở."""
    if hasattr(node, 'h') and (node.h > 0 or getattr(node, 'f', 0) > 0):
        parent_part = f"({node.parent_id}, {node.move}, g={node.cost}, h={node.h}, f={node.f})" if node.parent_id else f"Start (g=0, h={node.h}, f={node.f})"
        header = f"{node.id} = {parent_part}"
    else:
        parent_part = f"{node.parent_id}, {node.move}, {node.cost}" if node.parent_id else "Start"
        if parent_part == "Start":
            header = f"{node.id} = Start"
        else:
            header = f"{node.id} = ({node.parent_id}, {node.move}, {node.cost})"
    
    rows = []
    for i in range(0, 9, 3):
        rows.append(f"{node.state[i]} {node.state[i+1]} {node.state[i+2]}")
    return header + "\n" + "\n".join(rows)

def format_explored_node(node):
    """Định dạng node đã duyệt rút gọn trong phần EXPLORED."""
    rows = []
    for i in range(0, 9, 3):
        rows.append(f"{node.state[i]} {node.state[i+1]} {node.state[i+2]}")
    return f"{node.id}\n" + "\n".join(rows)

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
        
        # Lấy phần tử ra khỏi Frontier đầu tiên (FIFO)
        current_node = frontier.popleft()
        frontier_states.discard(current_node.state)

        # Kiểm tra đích khi node được POP ra để xét
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

            # Truy vết kết quả đường đi
            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()

            moves = [n.move for n in path if n.move is not None]

            return SearchResult(
                success=True,
                algorithm="BFS",
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
            # Không thêm các trạng thái trùng lặp vào Frontier hoặc Explored
            if next_state not in explored_states and next_state not in frontier_states:
                # Kiểm tra giới hạn số node
                if name_gen.count >= MAX_NODES:
                    return SearchResult(
                        success=False,
                        algorithm="BFS",
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

                child_name = name_gen.get_or_create(next_state)
                generated_count += 1
                child_node = SearchNode(
                    state=next_state,
                    parent=current_node,
                    parent_id=current_node.id,
                    move=move,
                    depth=current_node.depth + 1,
                    cost=current_node.cost + 1,
                    node_id=child_name,
                    gen_order=generated_count
                )
                frontier.append(child_node)
                frontier_states.add(next_state)
                children.append(child_node)

        # Lưu bước tìm kiếm hiện tại
        steps.append(SearchStep(
            step=step_num,
            current_node=current_node,
            frontier=list(frontier),
            explored=list(explored),
            generated_children=children
        ))
        step_num += 1

    return SearchResult(
        success=False,
        algorithm="BFS",
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

def run_dfs(start, goal, move_order=('L', 'R', 'U', 'D'), depth_limit=20):
    """Thuật toán tìm kiếm theo chiều sâu (DFS) giới hạn độ sâu."""
    name_gen = NodeNameGenerator()
    start_name = name_gen.get_or_create(start)
    start_node = SearchNode(
        state=start, parent=None, parent_id=None, move=None,
        depth=0, cost=0, node_id=start_name, gen_order=0
    )

    # Stack LIFO
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

        # Lấy phần tử ở cuối stack ra xét
        current_node = frontier.pop()
        frontier_states.discard(current_node.state)

        # Kiểm tra đích khi node được POP ra để xét
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

            # Truy vết
            path = []
            curr = current_node
            while curr:
                path.append(curr)
                curr = curr.parent
            path.reverse()

            moves = [n.move for n in path if n.move is not None]

            return SearchResult(
                success=True,
                algorithm="DFS",
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
        # Chỉ sinh con nếu độ sâu hiện tại nhỏ hơn giới hạn độ sâu
        if current_node.depth < depth_limit:
            neighbors = get_neighbors(current_node.state, move_order)
            
            # Để giữ đúng thứ tự ưu tiên L, R, U, D khi pop ra từ LIFO stack,
            # chúng ta phải push các node con vào stack theo thứ tự ngược lại (D, U, R, L)
            reversed_neighbors = list(reversed(neighbors))

            for move, next_state, moved_tile in reversed_neighbors:
                # Kiểm tra tránh chu trình: tìm kiếm dọc theo đường đi từ gốc
                ancestor = current_node
                is_ancestor = False
                while ancestor:
                    if ancestor.state == next_state:
                        is_ancestor = True
                        break
                    ancestor = ancestor.parent

                # DFS đồ thị: tránh các node đã duyệt hoàn toàn trong explored_states
                if not is_ancestor and next_state not in explored_states:
                    if name_gen.count >= MAX_NODES:
                        return SearchResult(
                            success=False,
                            algorithm="DFS",
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

                    child_name = name_gen.get_or_create(next_state)
                    generated_count += 1
                    child_node = SearchNode(
                        state=next_state,
                        parent=current_node,
                        parent_id=current_node.id,
                        move=move,
                        depth=current_node.depth + 1,
                        cost=current_node.cost + 1,
                        node_id=child_name,
                        gen_order=generated_count
                    )
                    frontier.append(child_node)
                    frontier_states.add(next_state)
                    # Chèn lên đầu danh sách children để hiển thị đúng thứ tự L, R, U, D
                    children.insert(0, child_node)

        # Lưu bước tìm kiếm hiện tại
        steps.append(SearchStep(
            step=step_num,
            current_node=current_node,
            frontier=list(frontier),
            explored=list(explored),
            generated_children=children
        ))
        step_num += 1

    return SearchResult(
        success=False,
        algorithm="DFS",
        steps=steps,
        solution_path=[],
        moves=[],
        total_cost=0,
        total_steps=0,
        expanded_nodes=len(explored),
        generated_nodes=name_gen.count,
        max_frontier_size=max_frontier_size,
        time_taken=0.0,
        message=f"No solution found within depth limit of {depth_limit}."
    )

def run_ids(start, goal, move_order=('L', 'R', 'U', 'D'), max_depth=20):
    """Thuật toán tìm kiếm sâu dần (IDS - Iterative Deepening Search)."""
    global_steps = []
    name_gen = NodeNameGenerator()
    max_frontier_size = 0
    total_expanded = 0
    generated_count = 0

    # Chạy lặp lại DLS với giới hạn độ sâu tăng dần từ 0 đến max_depth
    for limit in range(max_depth + 1):
        # Mỗi lượt tìm kiếm giới hạn độ sâu sẽ bắt đầu mới từ trạng thái Start
        start_name = name_gen.get_or_create(start)
        start_node = SearchNode(
            state=start, parent=None, parent_id=None, move=None,
            depth=0, cost=0, node_id=start_name, gen_order=0
        )

        frontier = [start_node]
        explored = []
        explored_states = set()

        # DLS cục bộ
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
                    success=True,
                    algorithm="IDS",
                    steps=global_steps,
                    solution_path=path,
                    moves=moves,
                    total_cost=current_node.cost,
                    total_steps=len(moves),
                    expanded_nodes=total_expanded,
                    generated_nodes=name_gen.count,
                    max_frontier_size=max_frontier_size,
                    time_taken=0.0,
                    message=f"Goal found at limit = {limit}."
                )

            explored.append(current_node)
            explored_states.add(current_node.state)

            children = []
            if current_node.depth < limit:
                neighbors = get_neighbors(current_node.state, move_order)
                reversed_neighbors = list(reversed(neighbors))

                for move, next_state, moved_tile in reversed_neighbors:
                    # Tránh chu trình trên nhánh hiện tại
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
                                success=False,
                                algorithm="IDS",
                                steps=global_steps,
                                solution_path=[],
                                moves=[],
                                total_cost=0,
                                total_steps=0,
                                expanded_nodes=total_expanded + len(explored),
                                generated_nodes=name_gen.count,
                                max_frontier_size=max_frontier_size,
                                time_taken=0.0,
                                message="Search stopped because node limit was reached."
                            )

                        child_name = name_gen.get_or_create(next_state)
                        generated_count += 1
                        child_node = SearchNode(
                            state=next_state,
                            parent=current_node,
                            parent_id=current_node.id,
                            move=move,
                            depth=current_node.depth + 1,
                            cost=current_node.cost + 1,
                            node_id=child_name,
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
        success=False,
        algorithm="IDS",
        steps=global_steps,
        solution_path=[],
        moves=[],
        total_cost=0,
        total_steps=0,
        expanded_nodes=total_expanded,
        generated_nodes=name_gen.count,
        max_frontier_size=max_frontier_size,
        time_taken=0.0,
        message=f"No solution found within max depth limit of {max_depth}."
    )

def run_ucs(start, goal, move_order=('L', 'R', 'U', 'D'), cost_mode=1):
    """
    Thuật toán tìm kiếm chi phí đồng nhất (UCS).
    - Dùng heapq.
    - Sắp xếp ưu tiên: 1. Tổng cost g(n), 2. Thứ tự sinh nút (generation order).
    - g(n) = tổng cost từ Start đến node hiện tại.
    - Cost mode:
      + 1: Step cost = 1
      + 2: Moved tile cost (bằng giá trị số ô tráo đổi với ô trống)
    """
    name_gen = NodeNameGenerator()
    start_name = name_gen.get_or_create(start)
    start_node = SearchNode(
        state=start, parent=None, parent_id=None, move=None,
        depth=0, cost=0, node_id=start_name, gen_order=0
    )

    # Priority queue lưu tuple (cost, gen_order, node)
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

        # Lấy nút có cost nhỏ nhất (nếu bằng nhau thì theo gen_order nhỏ nhất)
        cost, order, current_node = heapq.heappop(pq)

        # Bỏ qua nếu trạng thái này đã được duyệt trước đó với chi phí rẻ hơn
        if current_node.state in explored_states:
            continue

        # Dừng khi Goal được POP khỏi priority queue
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
                success=True,
                algorithm="UCS",
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
            # Chi phí cho bước đi hiện tại
            step_cost = 1 if cost_mode == 1 else moved_tile
            next_cost = current_node.cost + step_cost

            # Kiểm tra và cập nhật chi phí tối ưu nhất cho trạng thái con
            if next_state not in explored_states:
                if next_state not in best_costs or next_cost < best_costs[next_state]:
                    if name_gen.count >= MAX_NODES:
                        return SearchResult(
                            success=False,
                            algorithm="UCS",
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

                    best_costs[next_state] = next_cost
                    child_name = name_gen.get_or_create(next_state)
                    generated_count += 1
                    child_node = SearchNode(
                        state=next_state,
                        parent=current_node,
                        parent_id=current_node.id,
                        move=move,
                        depth=current_node.depth + 1,
                        cost=next_cost,
                        node_id=child_name,
                        gen_order=generated_count
                    )
                    heapq.heappush(pq, (next_cost, generated_count, child_node))
                    children.append(child_node)

        # Lấy danh sách Frontier đã sắp xếp theo thứ tự ưu tiên g(n) -> gen_order để hiển thị
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
        success=False,
        algorithm="UCS",
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

# =============================================================================
# GIAO DIỆN HIỂN THỊ CHI TIẾT BƯỚC TÌM KIẾM
# =============================================================================

def render_step(step, result, current_index):
    """Xóa màn hình và in thông tin bước hiện tại dạng side-by-side."""
    # Xóa màn hình tùy hệ điều hành
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

    note_header = f" | {step.note}" if step.note else ""
    print("=" * 90)
    print(f"STEP {step.step}{note_header}")
    print("=" * 90)
    print()

    # Tạo các dòng cho CURRENT BOARD (bên trái)
    left_lines = []
    left_lines.append("CURRENT BOARD:")
    left_lines.extend(pretty_board_box(step.current_node.state))

    # Tạo các dòng cho STEP DETAIL (bên phải)
    right_lines = []
    right_lines.append("STEP DETAIL:")
    
    right_lines.append("NODE:")
    # In node hiện tại bằng ma trận 3x3
    right_lines.extend(format_node(step.current_node).split('\n'))
    right_lines.append("")

    right_lines.append("FRONTIER:")
    if not step.frontier:
        right_lines.append("(empty)")
    else:
        # Nếu frontier nhỏ hơn hoặc bằng 10, in dạng ma trận đầy đủ
        if len(step.frontier) <= 10:
            for node in step.frontier:
                right_lines.extend(format_node(node).split('\n'))
                right_lines.append("")
        else:
            # Nếu quá dài, in 10 nút đầu đầy đủ và phần còn lại in rút gọn trên một hàng
            for node in step.frontier[:10]:
                right_lines.extend(format_node(node).split('\n'))
                right_lines.append("")
            
            remaining = step.frontier[10:]
            right_lines.append(f"+ {len(remaining)} more nodes in frontier:")
            
            concise_parts = []
            for node in remaining:
                parent_part = f"{node.parent_id},{node.move},{node.cost}" if node.parent_id else "Start"
                concise_parts.append(f"{node.id}=({parent_part})")
            
            concise_str = ", ".join(concise_parts)
            # Tự động cắt dòng dài
            chunk_size = 50
            for idx in range(0, len(concise_str), chunk_size):
                right_lines.append(concise_str[idx:idx+chunk_size])
            right_lines.append("")

    right_lines.append("EXPLORED:")
    if not step.explored:
        right_lines.append("(empty)")
    else:
        # Nếu Explored dài, giới hạn hiển thị 10 node gần nhất đầy đủ
        if len(step.explored) <= 10:
            for node in step.explored:
                right_lines.extend(format_explored_node(node).split('\n'))
                right_lines.append("")
        else:
            earlier_nodes = step.explored[:-10]
            earlier_names = ", ".join(node.id for node in earlier_nodes)
            
            right_lines.append("... (earlier nodes):")
            chunk_size = 50
            for idx in range(0, len(earlier_names), chunk_size):
                right_lines.append(earlier_names[idx:idx+chunk_size])
            right_lines.append("")

            # 10 node cuối cùng in đầy đủ ma trận 3x3
            for node in step.explored[-10:]:
                right_lines.extend(format_explored_node(node).split('\n'))
                right_lines.append("")

    # Kết hợp ghép hai bên trái và phải
    max_lines = max(len(left_lines), len(right_lines))
    for i in range(max_lines):
        left_text = left_lines[i] if i < len(left_lines) else ""
        right_text = right_lines[i] if i < len(right_lines) else ""
        # Căn lề trái 38 kí tự để cân đối giao diện terminal
        print(f"{left_text:<38} {right_text}")

    print()
    print("=" * 90)
    print("CONTROLS:")
    print("[N] Next step | [P] Previous step | [A] Auto play | [R] Reset | [Q] Quit")
    print("=" * 90)

# =============================================================================
# HÀM PHÁT LẠI TỪNG BƯỚC
# =============================================================================

def replay_steps(result):
    """Vòng lặp phát lại các bước và tương tác với người dùng."""
    if not result.steps:
        print("Không tìm thấy các bước nào để chạy hoặc thuật toán dừng ngay lập tức.")
        input("Nhấn Enter để tiếp tục...")
        return

    current_idx = 0
    auto_play = False

    while True:
        render_step(result.steps[current_idx], result, current_idx)

        # Dừng tự động khi phát đến cuối
        if auto_play and current_idx == len(result.steps) - 1:
            auto_play = False
            print("Đã phát hết tất cả các bước.")

        if auto_play:
            try:
                time.sleep(0.7)
                current_idx += 1
            except KeyboardInterrupt:
                auto_play = False
                print("\nĐã dừng chế độ tự động chạy!")
                time.sleep(1)
        else:
            choice = input("Nhập lệnh điều khiển: ").strip().upper()
            if choice == 'Q':
                break
            elif choice == 'N' or choice == '':
                if current_idx < len(result.steps) - 1:
                    current_idx += 1
                else:
                    print("Đang ở bước cuối cùng!")
                    time.sleep(0.8)
            elif choice == 'P':
                if current_idx > 0:
                    current_idx -= 1
                else:
                    print("Đang ở bước đầu tiên!")
                    time.sleep(0.8)
            elif choice == 'R':
                current_idx = 0
            elif choice == 'A':
                if current_idx == len(result.steps) - 1:
                    current_idx = 0
                auto_play = True

    # Khi thoát ra ngoài, hiển thị tóm tắt thống kê thuật toán
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')

    if result.success:
        print("=" * 45)
        print("GOAL FOUND")
        print("=" * 45)
        print(f"Algorithm: {result.algorithm}")
        
        path_str = " -> ".join(n.id for n in result.solution_path)
        print(f"Path nodes: {path_str}")
        
        moves_str = " -> ".join(result.moves)
        print(f"Moves: {moves_str}")
        
        print(f"Total steps: {result.total_steps}")
        print(f"Total cost: {result.total_cost}")
        print(f"Expanded nodes: {result.expanded_nodes}")
        print(f"Generated nodes: {result.generated_nodes}")
        print(f"Max frontier size: {result.max_frontier_size}")
        print(f"Time taken: {result.time_taken:.5f} seconds")
    else:
        print("=" * 45)
        print("NO SOLUTION FOUND")
        print("=" * 45)
        print(f"Algorithm: {result.algorithm}")
        print(f"Message: {result.message}")
        print(f"Expanded nodes: {result.expanded_nodes}")
        print(f"Generated nodes: {result.generated_nodes}")
        print(f"Max frontier size: {result.max_frontier_size}")
        print(f"Time taken: {result.time_taken:.5f} seconds")

    print("=" * 45)
    input("\nNhấn Enter để quay lại Menu chính...")

# =============================================================================
# CẤU HÌNH MẶC ĐỊNH & THÔNG SỐ TOÀN CỤC
# =============================================================================

# Trạng thái mặc định đề bài
DEFAULT_START = (1, 2, 3, 4, 0, 6, 7, 5, 8)
DEFAULT_GOAL  = (1, 2, 3, 4, 5, 6, 7, 8, 0)

current_start = DEFAULT_START
current_goal = DEFAULT_GOAL
current_algorithm = "BFS"

# Tham số mặc định cho từng thuật toán
dfs_limit = 20
ids_max_depth = 20
ucs_cost_mode = 2  # 1: step cost = 1 | 2: moved tile cost (Mặc định moved tile cost để khớp đề bài)
astar_heuristic_mode = 1  # 1: Manhattan | 2: Misplaced Tiles
astar_cost_mode = 2       # 1: step cost = 1 | 2: moved tile cost

# =============================================================================
# MENU LỰA CHỌN THUẬT TOÁN
# =============================================================================

def choose_algorithm_menu():
    global current_algorithm, dfs_limit, ids_max_depth, ucs_cost_mode, astar_heuristic_mode, astar_cost_mode
    while True:
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')

        print("=" * 40)
        print("CHOOSE ALGORITHM")
        print("=" * 40)
        print("1. BFS")
        print("2. DFS")
        print("3. IDS")
        print("4. UCS")
        print("5. A*")
        print("=" * 40)
        
        choice = input("Choose algorithm (1-5): ").strip()
        if choice == '1':
            current_algorithm = "BFS"
            break
        elif choice == '2':
            current_algorithm = "DFS"
            limit_in = input("Enter Depth Limit (bỏ trống mặc định là 20): ").strip()
            if limit_in == "":
                dfs_limit = 20
            else:
                try:
                    dfs_limit = int(limit_in)
                except ValueError:
                    print("Lỗi: Vui lòng nhập số nguyên hợp lệ. Sử dụng 20.")
                    dfs_limit = 20
                    time.sleep(1.5)
            break
        elif choice == '3':
            current_algorithm = "IDS"
            max_in = input("Enter Max Depth (bỏ trống mặc định là 20): ").strip()
            if max_in == "":
                ids_max_depth = 20
            else:
                try:
                    ids_max_depth = int(max_in)
                except ValueError:
                    print("Lỗi: Vui lòng nhập số nguyên hợp lệ. Sử dụng 20.")
                    ids_max_depth = 20
                    time.sleep(1.5)
            break
        elif choice == '4':
            current_algorithm = "UCS"
            while True:
                print("\nUCS Cost Mode:")
                print("1. Step cost = 1")
                print("2. Moved tile cost")
                c_mode = input("Choose cost mode (1-2): ").strip()
                if c_mode == '1':
                    ucs_cost_mode = 1
                    break
                elif c_mode == '2':
                    ucs_cost_mode = 2
                    break
                else:
                    print("Lựa chọn không hợp lệ!")
            break
        elif choice == '5':
            current_algorithm = "A*"
            while True:
                print("\nA* Heuristic Mode:")
                print("1. Manhattan Distance")
                print("2. Misplaced Tiles")
                h_choice = input("Choose heuristic mode (1-2): ").strip()
                if h_choice == '1':
                    astar_heuristic_mode = 1
                    break
                elif h_choice == '2':
                    astar_heuristic_mode = 2
                    break
                else:
                    print("Lựa chọn không hợp lệ!")
            while True:
                print("\nA* Cost Mode:")
                print("1. Step cost = 1")
                print("2. Moved tile cost")
                c_mode = input("Choose cost mode (1-2): ").strip()
                if c_mode == '1':
                    astar_cost_mode = 1
                    break
                elif c_mode == '2':
                    astar_cost_mode = 2
                    break
                else:
                    print("Lựa chọn không hợp lệ!")
            break
        else:
            print("Lựa chọn sai, vui lòng chọn lại từ 1 đến 5.")
            time.sleep(1.5)

# =============================================================================
# MENU CHÍNH
# =============================================================================

def main_menu():
    global current_start, current_goal, current_algorithm
    while True:
        if os.name == 'nt':
            os.system('cls')
        else:
            os.system('clear')

        print("=" * 40)
        print("8-PUZZLE SEARCH VISUALIZER")
        print("=" * 40)
        print("1. Load example")
        print("2. Enter start state")
        print("3. Enter goal state")
        print("4. Choose algorithm")
        print("5. Run algorithm")
        print("6. Exit")
        print("-" * 40)
        
        # Định dạng in một dòng trạng thái start/goal
        start_str = " ".join(map(str, current_start))
        goal_str = " ".join(map(str, current_goal))
        print(f"Current start: {{{start_str}}}")
        print(f"Current goal : {{{goal_str}}}")
        
        alg_param = ""
        if current_algorithm == "DFS":
            alg_param = f" (Limit: {dfs_limit})"
        elif current_algorithm == "IDS":
            alg_param = f" (Max depth: {ids_max_depth})"
        elif current_algorithm == "UCS":
            mode_name = "Step cost=1" if ucs_cost_mode == 1 else "Moved tile cost"
            alg_param = f" (Cost Mode: {mode_name})"
        elif current_algorithm == "A*":
            h_name = "Manhattan" if astar_heuristic_mode == 1 else "Misplaced Tiles"
            mode_name = "Step cost=1" if astar_cost_mode == 1 else "Moved tile cost"
            alg_param = f" (Heuristic: {h_name}, Cost: {mode_name})"
            
        print(f"Current algorithm: {current_algorithm}{alg_param}")
        print("=" * 40)

        option = input("Choose option: ").strip()
        
        if option == '1':
            current_start = DEFAULT_START
            current_goal = DEFAULT_GOAL
            print("Đã tải ví dụ mặc định thành công.")
            time.sleep(1)
            
        elif option == '2':
            input_text = input("Enter start state (9 số từ 0 đến 8 cách nhau bởi khoảng trắng hoặc dấu phẩy): ").strip()
            state = parse_state(input_text)
            if state is None:
                print("Lỗi định dạng. Trạng thái không hợp lệ.")
                time.sleep(1.5)
            else:
                ok, msg = validate_state(state)
                if not ok:
                    print(f"Lỗi: {msg}")
                    time.sleep(1.5)
                else:
                    current_start = state
                    print("Cập nhật Start State thành công.")
                    time.sleep(1)
                    
        elif option == '3':
            input_text = input("Enter goal state (9 số từ 0 đến 8 cách nhau bởi khoảng trắng hoặc dấu phẩy): ").strip()
            state = parse_state(input_text)
            if state is None:
                print("Lỗi định dạng. Trạng thái không hợp lệ.")
                time.sleep(1.5)
            else:
                ok, msg = validate_state(state)
                if not ok:
                    print(f"Lỗi: {msg}")
                    time.sleep(1.5)
                else:
                    current_goal = state
                    print("Cập nhật Goal State thành công.")
                    time.sleep(1)
                    
        elif option == '4':
            choose_algorithm_menu()
            
        elif option == '5':
            # 1. Kiểm tra tính giải được
            if not is_solvable(current_start, current_goal):
                print("\n" + "!" * 40)
                print("LỖI: This puzzle is not solvable.")
                print("Lưu ý: Hai trạng thái có độ chẵn lẻ số inversions không trùng khớp.")
                print("!" * 40)
                input("\nNhấn Enter để quay lại...")
                continue
            
            # 2. Chạy thuật toán tìm kiếm
            print(f"\nĐang chạy thuật toán {current_algorithm}...")
            start_time = time.perf_counter()
            
            if current_algorithm == "BFS":
                result = run_bfs(current_start, current_goal)
            elif current_algorithm == "DFS":
                result = run_dfs(current_start, current_goal, depth_limit=dfs_limit)
            elif current_algorithm == "IDS":
                result = run_ids(current_start, current_goal, max_depth=ids_max_depth)
            elif current_algorithm == "UCS":
                result = run_ucs(current_start, current_goal, cost_mode=ucs_cost_mode)
            elif current_algorithm == "A*":
                result = run_astar(current_start, current_goal, cost_mode=astar_cost_mode, heuristic_mode=astar_heuristic_mode)
                
            end_time = time.perf_counter()
            result.time_taken = end_time - start_time
            
            # 3. Phát lại các bước trực quan hóa
            replay_steps(result)
            
        elif option == '6':
            print("Đang thoát chương trình. Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ. Vui lòng chọn lại (1-6).")
            time.sleep(1)

if __name__ == "__main__":
    main_menu()
