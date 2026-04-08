class Context:
    """上下文类，用于管理流程状态"""
    
    def __init__(self):
        """初始化上下文"""
        self.variables = {}  # 存储流程变量
        self.node_outputs = {}  # 存储每个节点的输出
        self.errors = []  # 存储错误信息
        self.execution_path = []  # 存储执行路径
        self.stop_requested = False  # 停止执行标志
    
    def set_variable(self, key, value):
        """设置变量"""
        self.variables[key] = value
    
    def get_variable(self, key, default=None):
        """获取变量"""
        return self.variables.get(key, default)
    
    def set_node_output(self, node_id, output):
        """存储节点输出"""
        self.node_outputs[node_id] = output
    
    def get_node_output(self, node_id, default=None):
        """获取节点输出"""
        return self.node_outputs.get(node_id, default)
    
    def add_error(self, error_message):
        """添加错误信息"""
        self.errors.append(error_message)
    
    def get_errors(self):
        """获取所有错误信息"""
        return self.errors
    
    def add_to_execution_path(self, node_id):
        """添加到执行路径"""
        self.execution_path.append(node_id)
    
    def get_execution_path(self):
        """获取执行路径"""
        return self.execution_path
    
    def clear(self):
        """清空上下文"""
        self.variables.clear()
        self.node_outputs.clear()
        self.errors.clear()
        self.execution_path.clear()
        self.stop_requested = False
    
    def set_stop_requested(self, value):
        """设置停止执行标志"""
        self.stop_requested = value
    
    def is_stop_requested(self):
        """检查是否请求停止执行"""
        return self.stop_requested