# Ke hoach cap nhat 8-Puzzle Search Visualizer

File chinh: `search_visualizer_gui.py`

Muc tieu cua plan nay la dong bo tai lieu thiet ke voi cac nhom thuat toan moi da duoc dua vao GUI. Bai toan van la 8-puzzle, nhung ngoai cac thuat toan tim kiem trang thai co ban, chuong trinh can the hien them hai nhom:

- Constraint satisfaction problems
- Searching in complex environments

## 1. Danh sach nhom thuat toan trong GUI

### Standard search algorithms

Nhom nay giu vai tro nen tang de so sanh:

- BFS
- DFS
- IDS
- UCS
- A*
- Simple Hill Climbing
- Steepest Ascent Hill Climbing
- Stochastic Hill Climbing
- Random Restart Hill Climbing
- Local Beam Search

### Constraint satisfaction problems

Nhom CSP ap dung cho 8-puzzle bang cach xem loi giai la mot chuoi trang thai/hang dong co rang buoc. Cac rang buoc chinh gom:

- Moi trang thai phai la hoan vi hop le cua cac so 0..8.
- Moi buoc di phai la mot phep truot hop le cua o trong.
- Duong di khong nen lap lai trang thai vua xet.
- Trang thai cuoi phai tien gan hoac dat goal trong gioi han do sau / so vong lap.

Danh sach thuat toan CSP hien tai:

- CSP: Path Consistency
- CSP: Global Constraints
- CSP: Backtracking Search
- CSP: Forward Checking
- CSP: AC-3
- CSP: Min-Conflicts

### Searching in complex environments

Nhom nay mo phong cac moi truong khong hoan toan xac dinh hoac khong quan sat day du:

- Complex Env: AND-OR Search
- Complex Env: No Observation
- Complex Env: Partial Observation

## 2. Anh xa CSP vao 8-puzzle

### CSP: Path Consistency

Y tuong: kiem tra tinh nhat quan cua toan bo duong di dang xay dung.

- Moi cap trang thai lien tiep phai duoc sinh ra bang mot nuoc di hop le.
- Khong chap nhan trang thai da xuat hien trong cung duong di hien tai.
- Dung heuristic Manhattan de loai nhanh nhanh cac nhanh khong con kha nang dat dich trong gioi han con lai.
- Tham so UI: `Gioi han Do sau`, mac dinh 20.

### CSP: Global Constraints

Y tuong: ap dung cac rang buoc toan cuc cua 8-puzzle truoc va trong qua trinh giai.

- Rang buoc all-different: start va goal phai chua dung cac so 0..8, khong trung lap.
- Rang buoc parity: start va goal phai cung tinh chan/le inversion de co loi giai.
- Rang buoc do sau: loi giai tim duoc khong vuot qua gioi han nguoi dung nhap.
- Engine hien tai dung A* Manhattan sau khi cac rang buoc toan cuc hop le.
- Tham so UI: `Gioi han Do sau`, mac dinh 40.

### CSP: Backtracking Search

Y tuong: thu lan luot cac nuoc di nhu gan gia tri cho bien hanh dong.

- Moi nut la mot trang thai sau khi gan them mot hanh dong.
- Neu dat goal thi dung.
- Neu vuot gioi han do sau thi quay lui.
- Bo qua trang thai da co trong duong di hien tai de tranh lap vo nghia.
- Tham so UI: `Gioi han Do sau`, mac dinh 10.

### CSP: Forward Checking

Y tuong: Backtracking co cat tia som bang heuristic.

- Sau moi buoc, tinh Manhattan tu trang thai hien tai den goal.
- Neu Manhattan lon hon so buoc con lai, nhanh do khong the toi goal trong gioi han hien tai.
- Nhanh do bi loai truoc khi tiep tuc mo rong.
- Tham so UI: `Gioi han Do sau`, mac dinh 10.

### CSP: AC-3

Y tuong: dung arc consistency de rut gon mien hanh dong truoc khi backtracking.

- Moi bien `A_i` dai dien cho mot hanh dong trong chuoi loi giai.
- Domain ban dau cua moi bien la `{L, R, U, D}`.
- AC-3 duyet cac cung lien tiep `(A_i, A_{i+1})`.
- Rang buoc chinh: hai hanh dong lien tiep khong nen la cap nguoc nhau, vi se dua puzzle quay lai trang thai cu.
- Sau khi domain duoc rut gon, engine tiep tuc backtracking tren cac nuoc di hop le cua 8-puzzle.
- Ket hop them Manhattan pruning de loai nhanh nhanh khong the dat goal trong so buoc con lai.
- Tham so UI: `Gioi han Do sau`, mac dinh 20.

### CSP: Min-Conflicts

Y tuong: sua cuc bo trang thai hien tai bang cach chon nuoc di lam giam xung dot.

- Xung dot duoc tinh tu so o sai vi tri ket hop voi Manhattan distance.
- O moi vong lap, sinh cac trang thai lan can hop le.
- Chon ung vien co so xung dot thap nhat, uu tien trang thai chua tham neu co.
- Khong dam bao toi uu, nhung phu hop de minh hoa local repair trong CSP.
- Tham so UI: `Max Iterations`, mac dinh 100.

## 3. Anh xa complex environments vao 8-puzzle

### Complex Env: AND-OR Search

Y tuong: mo phong moi truong nondeterministic, trong do mot hanh dong co the tao nhieu ket qua.

- OR node: chon hanh dong.
- AND node: phai xu ly tat ca ket qua co the xay ra cua hanh dong.
- Ket qua thanh cong la mot conditional plan thay vi chi mot duong di don.
- Tham so UI: `Do sau toi da / So buoc`, mac dinh 5.

### Complex Env: No Observation

Y tuong: tim kiem tren belief state khi agent khong quan sat duoc trang thai chinh xac.

- Mot nut dai dien cho tap cac trang thai co the.
- Moi hanh dong duoc ap dung cho toan bo belief state.
- Goal dat duoc khi tat ca trang thai trong belief deu hoi tu ve goal.
- Tham so UI: `Do sau toi da / So buoc`, mac dinh 10.

### Complex Env: Partial Observation

Y tuong: agent chi quan sat mot phan thong tin cua bang.

- Belief state duoc loc sau moi hanh dong dua tren observation.
- Observation hien tai gom vi tri o trong va hang dau tien.
- Engine dung duong di A* tren actual state de mo phong chuoi hanh dong, sau do cap nhat belief.
- Tham so UI: `Do sau toi da / So buoc`, mac dinh 12.

## 4. Yeu cau UI va tich hop

GUI can tiep tuc dung mot combobox chung lay tu `ALGORITHM_CHOICES`, gom:

- `STANDARD_SEARCH_ALGORITHMS`
- `CSP_ALGORITHMS`
- `COMPLEX_ENV_ALGORITHMS`

Khi nguoi dung chon thuat toan:

- Nhom DFS/IDS hien thi depth/max-depth nhu cu.
- UCS/A* hien thi cost/heuristic nhu cu.
- Hill Climbing va Local Beam Search hien thi heuristic va tham so lap.
- CSP hien thi `Gioi han Do sau` hoac `Max Iterations` voi Min-Conflicts.
- Complex environments hien thi `Do sau toi da / So buoc`.

Bang so sanh thuat toan can chay duoc ca ba nhom, gom cac thuat toan CSP va complex environments moi.

## 5. Quy uoc to mau CSP tren bang 8-puzzle

Vi nhom CSP thuong duoc giang day qua bai toan to mau, visualizer ap dung cung tu duy mau len bang 8-puzzle:

- Green: o so da thoa rang buoc vi tri, dang dung voi goal.
- Red: o so dang xung dot / chua thoa rang buoc vi tri.
- Orange: bien hien tai vua duoc gan, tuong ung voi o so vua di chuyen trong buoc do.
- Cyan: cac gia tri mien ung vien, tuong ung voi nhung o co the di chuyen o nhanh tiep theo.
- Dark gray: o trong `0`.
- Gray with `?`: o chua chac chan trong belief state cua nhom moi truong phuc tap.

Quy uoc nay chi bat khi `result.algorithm` bat dau bang `CSP:`. Cac thuat toan search khac van dung mau cu: xanh la cho o dung vi tri, xanh duong cho o chua dung.

## 6. Trang thai hien tai

`search_visualizer_gui.py` da co cac hang so nhom thuat toan:

- `STANDARD_SEARCH_ALGORITHMS`
- `CSP_ALGORITHMS`
- `COMPLEX_ENV_ALGORITHMS`
- `ALGORITHM_CHOICES`

Da co cac ham engine cho nhom moi:

- `run_csp_path_consistency_puzzle`
- `run_csp_global_constraints_puzzle`
- `run_csp_backtracking_search_puzzle`
- `run_csp_backtracking_puzzle` voi `forward_checking=True`
- `run_csp_ac3_puzzle`
- `run_csp_min_conflicts_puzzle`
- `run_and_or_search_puzzle`
- `run_no_observation_search_puzzle`
- `run_partially_observable_search_puzzle`

Can tiep tuc uu tien kiem tra runtime GUI sau khi moi truong co dependency `ttkbootstrap`.
