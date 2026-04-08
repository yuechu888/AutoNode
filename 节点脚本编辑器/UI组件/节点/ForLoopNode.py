from 节点核心.节点基类端口 import BaseNode
from PySide6.QtGui import QFont, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QRectF, QPointF

class ForLoopNode(BaseNode):
    """循环节点
    
    设计特点：
    1. 有输入和输出执行端口
    2. 参数从属性面板控制
    3. 数据通过执行上下文传递
    4. 可以包含内部节点并循环执行它们
    """
    
    def __init__(self, width=200, height=60, x=0, y=0):
        super().__init__("循环", QColor("#2E86AB"), width, height, x, y)
        # 最小大小
        self.min_width = 200
        self.min_height = 60
        # 存储内部节点
        self.internal_nodes = []
        self.init_ports()
        self.update_variables()

    def init_ports(self):
        # 清空端口列表
        self.ports.clear()
        # 添加执行端口
        self.add_port("input", "exec", 16, 30, max_connections=-1, label="输入")  # 输入端口
        self.add_port("output", "exec", self.width - 16, 5, max_connections=-1, label="循环")  # 循环体输出端口（用于循环执行）
        self.add_port("output", "exec", self.width - 16, 55, max_connections=-1, label="循环完成")  # 循环完成输出端口（用于循环结束后执行）

    def boundingRect(self):
        """返回节点的边界矩形"""
        # 扩大边界矩形，确保端口不被遮挡
        return QRectF(-10, -10, self.width + 20, self.height + 20)

    def paint(self, painter, option, widget):
        # 检查painter是否有效
        if not painter:
            return
        
        try:
            # 确保节点可见
            if not self.isVisible():
                self.setVisible(True)
            
            # 确保zValue合理
            if self.zValue() < 1:
                self.setZValue(1)
            
            # 确保内部节点也可见
            for node in getattr(self, 'internal_nodes', []):
                if node and not node.isVisible():
                    node.setVisible(True)
                if node and node.zValue() <= self.zValue():
                    node.setZValue(self.zValue() + 1)
            
            # 确保所有端口可见且在循环体上方
            for port in self.ports:
                if not port.isVisible():
                    port.setVisible(True)
                if port.zValue() <= self.zValue():
                    port.setZValue(self.zValue() + 1)
            
            # 调用父类的paint方法，确保外观与其他节点一致
            super().paint(painter, option, widget)
        except Exception:
            # 忽略绘制错误，确保程序不会崩溃
            pass

    def update_variables(self):
        """更新内置变量
        
        这里定义的变量会在属性面板中显示，用户可以直接修改
        """
        super().update_variables()
        
        # 保留现有的输入变量值
        current_inputs = self.variables.get('inputs', [])
        loop_count = '1'  # 默认只执行一次
        
        # 检查是否已有输入变量
        for input_var in current_inputs:
            input_name = input_var.get('name')
            if input_name == '循环次数':
                value = input_var.get('value', '1')
                if value != '':
                    loop_count = value
            elif input_name == '结束值':
                # 兼容旧的结束值，转换为循环次数
                value = input_var.get('value', '1')
                if value != '':
                    try:
                        loop_count = str(int(value))
                    except:
                        pass
        
        # 输入变量：在属性面板中可修改
        self.variables['inputs'] = [
            {'name': '循环次数', 'type': 'int', 'value': loop_count, 'description': '循环执行的次数'}
        ]
        
        # 输出变量
        self.variables['outputs'] = [
            {'name': 'index', 'type': 'int', 'description': '当前循环的索引值'}
        ]

    def add_internal_node(self, node):
        """添加内部节点"""
        # 将节点添加为子节点
        node.setParentItem(self)
        # 确保节点可见
        node.setVisible(True)
        # 确保节点zValue合理，显示在循环体上方
        node.setZValue(self.zValue() + 1)
        # 调整节点位置，使其在容器内部
        # 计算位置，避免重叠
        base_y = 80
        for existing_node in self.internal_nodes:
            if existing_node:
                base_y = max(base_y, existing_node.y() + existing_node.height + 20)
        node.setPos(40, base_y)
        # 初始化内部节点的 last_mouse_scene_pos 属性
        node.last_mouse_scene_pos = node.mapToScene(node.pos())
        # 确保内部节点不是选中状态
        node.is_selected = False
        node.setSelected(False)
        # 添加到内部节点列表
        self.internal_nodes.append(node)
        # 确保节点被添加到场景中
        if self.scene() and node.scene() != self.scene():
            self.scene().addItem(node)
        # 调整容器大小
        self.adjust_size()
        # 触发重绘
        self.update()
        # 触发场景重绘
        if self.scene():
            self.scene().update()

    def remove_internal_node(self, node):
        """移除内部节点"""
        if node in self.internal_nodes:
            # 从场景中移除节点
            if node.scene():
                node.scene().removeItem(node)
            # 从内部节点列表中移除
            self.internal_nodes.remove(node)
            # 清理无效的内部节点引用
            self.internal_nodes = [n for n in self.internal_nodes if n and n.scene()]
            # 调整容器大小
            self.adjust_size()
            # 触发重绘
            self.update()
            # 触发场景重绘
            if self.scene():
                self.scene().update()

    def adjust_size(self):
        """调整容器大小以适应内部节点"""
        # 确保最小大小有默认值
        if not hasattr(self, 'min_width') or self.min_width <= 0:
            self.min_width = 200
        if not hasattr(self, 'min_height') or self.min_height <= 0:
            self.min_height = 60
            
        # 清理无效的内部节点引用
        self.internal_nodes = [node for node in self.internal_nodes if node and node.scene()]
            
        if not self.internal_nodes:
            # 没有内部节点时使用最小大小
            self.width = self.min_width
            self.height = self.min_height
            # 更新端口位置
            for port in self.ports:
                if port.port_type == "output":
                    if port.label == "循环":
                        # 循环体输出端口（用于循环执行）
                        port.setPos(self.width - 20, 10)
                    elif port.label == "循环完成":
                        # 循环完成输出端口（用于循环结束后执行）
                        port.setPos(self.width - 20, 55)
                elif port.port_type == "input" and port.label == "输入":
                    # 循环体输入端口
                    port.setPos(20, 30)
            # 触发重绘
            self.update()
            # 触发场景重绘
            if self.scene():
                self.scene().update()
            return
        
        # 计算所需的最小宽度和高度
        min_width = self.min_width
        min_height = self.min_height
        
        # 计算节点的最小和最大位置
        min_node_x = float('inf')
        min_node_y = float('inf')
        max_node_x = float('-inf')
        max_node_y = float('-inf')
        
        for node in self.internal_nodes:
            # 确保节点有宽度和高度属性
            if not hasattr(node, 'width') or not hasattr(node, 'height'):
                continue
            # 确保节点可见
            if not node.isVisible():
                node.setVisible(True)
            # 确保节点zValue合理
            if node.zValue() <= self.zValue():
                node.setZValue(self.zValue() + 1)
                
            # 计算节点的边界
            node_left = node.x()
            node_top = node.y()
            node_right = node.x() + node.width
            node_bottom = node.y() + node.height
            
            # 更新节点的最小和最大位置
            min_node_x = min(min_node_x, node_left)
            min_node_y = min(min_node_y, node_top)
            max_node_x = max(max_node_x, node_right)
            max_node_y = max(max_node_y, node_bottom)
        
        # 计算偏移量，确保节点在循环体内部，范围判断为内部+50
        x_offset = 0
        y_offset = 0
        padding = 50  # 内部+50的范围判断
        
        # 当节点拖动到左边边缘外时，计算需要的偏移量
        if min_node_x < padding:
            x_offset = padding - min_node_x
        
        # 当节点拖动到上边边缘外时，计算需要的偏移量
        if min_node_y < padding:
            y_offset = padding - min_node_y
        
        # 如果有偏移量，调整所有内部节点的位置
        if x_offset > 0 or y_offset > 0:
            for node in self.internal_nodes:
                # 确保节点可见
                if not node.isVisible():
                    node.setVisible(True)
                # 调整节点位置，使其保持在边界内
                node.setPos(node.x() + x_offset, node.y() + y_offset)
            # 重新计算节点的边界
            min_node_x = float('inf')
            min_node_y = float('inf')
            max_node_x = float('-inf')
            max_node_y = float('-inf')
            
            for node in self.internal_nodes:
                if hasattr(node, 'width') and hasattr(node, 'height'):
                    node_left = node.x()
                    node_top = node.y()
                    node_right = node.x() + node.width
                    node_bottom = node.y() + node.height
                    
                    min_node_x = min(min_node_x, node_left)
                    min_node_y = min(min_node_y, node_top)
                    max_node_x = max(max_node_x, node_right)
                    max_node_y = max(max_node_y, node_bottom)
        
        # 计算循环体需要的最小宽度和高度，考虑内部+50的范围
        required_width = max_node_x + padding  # 右边留50像素边距
        required_height = max_node_y + padding  # 下边留50像素边距
        
        # 更新最小宽度和高度
        min_width = max(min_width, required_width)
        min_height = max(min_height, required_height)
        
        # 确保宽度和高度不为0
        self.width = max(min_width, 100)  # 确保最小宽度为100
        self.height = max(min_height, 100)  # 确保最小高度为100
        
        # 更新端口位置
        for port in self.ports:
            if port.port_type == "output":
                # 根据标签更新端口位置
                if port.label == "循环":
                    # 循环体输出端口
                    port.setPos(self.width - 20, 10)
                elif port.label == "循环完成":
                    # 循环完成输出端口
                    port.setPos(self.width - 20, 55)
            elif port.port_type == "input" and port.label == "输入":
                # 输入端口位置保持不变
                port.setPos(20, 30)
        
        # 触发重绘
        self.update()
        # 触发场景重绘
        if self.scene():
            self.scene().update()

    def contains_point(self, point):
        """检查点是否在容器内部"""
        return QRectF(0, 0, self.width, self.height).contains(point)

    def _execute(self, context, resolved_inputs=None, all_nodes=None):
        """执行循环逻辑"""
        # 获取循环参数
        start = 0
        end = 100
        step = 1
        index_var_name = "index"
        
        # 从解析后的输入值获取参数
        if resolved_inputs:
            for input_var in resolved_inputs:
                if input_var.get('name') == '循环次数':
                    try:
                        loop_count = int(input_var.get('value', '1'))
                        # 转换为range参数：从0开始，执行loop_count次
                        start = 0
                        end = loop_count
                        step = 1
                    except:
                        pass
                elif input_var.get('name') == '结束值':
                    # 兼容旧的结束值
                    try:
                        end = int(input_var.get('value', '1'))
                        start = 0
                        step = 1
                    except:
                        pass
        else:
            # 回退到原始变量
            for input_var in self.variables.get('inputs', []):
                if input_var.get('name') == '循环次数':
                    try:
                        loop_count = int(input_var.get('value', '1'))
                        # 转换为range参数：从0开始，执行loop_count次
                        start = 0
                        end = loop_count
                        step = 1
                    except:
                        pass
                elif input_var.get('name') == '结束值':
                    # 兼容旧的结束值
                    try:
                        end = int(input_var.get('value', '1'))
                        start = 0
                        step = 1
                    except:
                        pass
        
        # 找到循环体输出端口（通过标签识别）
        loop_port = None
        for port in self.ports:
            if port.port_type == "output" and port.label == "循环":
                loop_port = port
                break
        
        # 打印循环参数
        print(f"循环参数: start={start}, end={end}, step={step}")
        print(f"循环次数: {len(range(start, end, step))}")
        
        # 设置循环内部执行标志，启用快速模式
        context.is_inside_loop = True
        
        # 执行循环
        for i in range(start, end, step):
            # 检查是否请求停止
            if hasattr(context, 'is_stop_requested') and context.is_stop_requested():
                print("循环执行被用户停止")
                return
            
            print(f"执行第 {i - start + 1} 次循环")
            # 将索引值存储到上下文
            context.set_variable(index_var_name, i)
            # 存储当前循环索引作为节点输出
            context.set_node_output(self.id, i)
            
            # 执行内部节点
            for node in self.internal_nodes:
                # 检查是否请求停止
                if hasattr(context, 'is_stop_requested') and context.is_stop_requested():
                    print("内部节点执行被用户停止")
                    return
                
                if hasattr(node, 'execute'):
                    print(f"执行内部节点: {node.title} (id: {node.id})")
                    node.execute(context, all_nodes)
                    # 标记为已执行
                    node.executed = True
            
            # 触发循环体输出端口的后续节点执行（每次循环都执行）
            if loop_port:
                for connection in loop_port.connections:
                    # 检查是否请求停止
                    if hasattr(context, 'is_stop_requested') and context.is_stop_requested():
                        print("循环体输出节点执行被用户停止")
                        return
                    
                    if connection.end_port:
                        end_node = connection.end_port.parentItem()
                        if end_node and hasattr(end_node, 'execute'):
                            print(f"执行循环体输出节点: {end_node.title} (id: {end_node.id})")
                            end_node.execute(context, all_nodes)
                            # 标记为已执行
                            end_node.executed = True
        
        # 取消循环内部执行标志
        context.is_inside_loop = False
        
        # 触发循环完成输出端口的后续节点执行
        # 找到循环完成输出端口（通过标签识别）
        completion_port = None
        for port in self.ports:
            if port.port_type == "output" and port.label == "循环完成":
                completion_port = port
                break
        
        # 触发循环完成输出端口的后续节点
        if completion_port:
            for connection in completion_port.connections:
                # 检查是否请求停止
                if hasattr(context, 'is_stop_requested') and context.is_stop_requested():
                    print("循环完成输出节点执行被用户停止")
                    return
                
                if connection.end_port:
                    end_node = connection.end_port.parentItem()
                    if end_node and hasattr(end_node, 'execute'):
                        print(f"执行循环完成输出节点: {end_node.title} (id: {end_node.id})")
                        end_node.execute(context, all_nodes)
                        # 标记为已执行
                        end_node.executed = True
        
        return None