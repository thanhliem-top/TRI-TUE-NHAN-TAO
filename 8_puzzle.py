import random
state = [1, 2, 3, 4, 5, 6, 8, 7, 0] 
history = {tuple(state)}           
goal = [1, 2, 3, 4, 5, 6, 7, 8, 0] 
def model_based_reflex_agent(current_board):
    global history
    
    idx = current_board.index(0)
    moves = []
    if idx >= 3: moves.append(-3) 
    if idx <= 5: moves.append(3)  
    if idx % 3 != 0: moves.append(-1) 
    if idx % 3 != 2: moves.append(1)  
    
    random.shuffle(moves) 

    
    for m in moves:
        
        next_s = list(current_board)
        next_s[idx], next_s[idx+m] = next_s[idx+m], next_s[idx]
        
        
        if tuple(next_s) not in history:
            history.add(tuple(next_s)) 
            return next_s #
            
    return None 

print("trạng thái bắt đầu:", state)
steps = 0

while state != goal:
    steps += 1
    new_state = model_based_reflex_agent(state)
    
    if new_state is None:
        break
        
    state = new_state
    print(f"Bước {steps}: {state}")
    
    if steps > 100:
        print("Dừng lại vì quá nhiều bước.")
        break
if state == goal:
    print("Mục tiêu đã hoàn thành!")