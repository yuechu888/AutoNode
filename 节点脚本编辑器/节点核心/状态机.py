from PySide6.QtCore import QObject, Signal

class EditorStateMachine(QObject):
    """编辑器状态机"""
    # 状态定义
    IDLE = "idle"  # 空闲状态
    NODE_SELECTED = "node_selected"  # 节点选中状态
    CONNECTION_SELECTED = "connection_selected"  # 连线选中状态
    DRAGGING_CONNECTION = "dragging_connection"  # 拖拽连线状态
    DRAGGING_NODE = "dragging_node"  # 拖拽节点状态
    
    # 状态变化信号
    state_changed = Signal(str, str)  # 旧状态, 新状态
    
    def __init__(self):
        super().__init__()
        self.current_state = self.IDLE
        self.previous_state = self.IDLE
    
    def transition(self, new_state):
        """状态转换"""
        if new_state != self.current_state:
            old_state = self.current_state
            self.previous_state = old_state
            self.current_state = new_state
            # 发射状态变化信号
            self.state_changed.emit(old_state, new_state)
    
    def get_state(self):
        """获取当前状态"""
        return self.current_state
    
    def get_previous_state(self):
        """获取上一个状态"""
        return self.previous_state
    
    def reset_to_idle(self):
        """重置到空闲状态"""
        self.transition(self.IDLE)