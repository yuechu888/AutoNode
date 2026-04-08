from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsLineItem, QMenu, QInputDialog, QMessageBox, QFileDialog, QStyleOptionGraphicsItem
from PySide6.QtGui import QColor, QPen, QPainter, QWheelEvent, QBrush, QMouseEvent, QAction, QTransform, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QLineF, QTimer
from 节点核心.连线类 import Connection
from 节点核心.状态机 import EditorStateMachine
from 节点核心.节点管理器 import node_manager
from 节点核心.节点基类端口 import signal_manager

# 定义常量
FIT_VIEW_PADDING = 50
SNAP_DISTANCE = 15

class NodeGraphicsView(QGraphicsView):
    """节点编辑器画布视图"""
    # 信号
    card_moved = Signal(int, QPointF)
    card_added = Signal(object)
    connection_added = Signal(object, object, str)
    connection_deleted = Signal(object)
    card_deleted = Signal(int)
    
    def __init__(self):
        super().__init__()
        # 场景设置
        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-500, -300, 1000, 600)  # 合理的初始大小
        self.setScene(self.scene)
        
        # 滚动条策略
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 渲染提示
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 设置默认拖动模式为 ScrollHandDrag 用于平移
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setInteractive(True)

        # 设置焦点策略，确保能接收键盘事件
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

        # 上下文菜单设置
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 启用拖放功能
        self.setAcceptDrops(True)

        # 缩放因子
        self.zoom_factor_base = 1.15

        # 连线拖动状态
        self.connections = []
        self.is_dragging_line = False
        self.drag_start_port = None
        self.temp_line = None
        self.temp_line_pen = QPen(Qt.GlobalColor.black, 1.5, Qt.PenStyle.DashLine)  # 临时线的画笔
        self.temp_line_snap_pen = QPen(QColor(0, 120, 215), 2.0, Qt.PenStyle.DashLine)  # 吸附时的画笔

        # 吸附状态
        self.is_snapped = False
        self.snapped_target_port = None

        # 存储节点
        self.nodes = {}
        self._next_node_id = 0
        self._max_loaded_id = -1  # 加载时跟踪最大ID
        
        # 状态机
        self.state_machine = EditorStateMachine()

        # 恢复右键处理的状态变量
        self._original_drag_mode = self.dragMode()
        self._right_mouse_pressed = False
        self._last_right_click_global_pos = None
        self._last_right_click_view_pos_f = None
        self.copied_card_data = None

        # 撤销系统
        self.undo_stack = []  # 撤销历史栈
        self.max_undo_steps = 50  # 最大撤销步数
        self._deleting_card = False  # 标志：正在删除卡片，防止连线删除触发额外撤销
        self._loading_workflow = False  # 标志：正在加载工作流，防止连线删除触发撤销保存
        self._updating_sequence = False  # 标志：正在更新序列显示，防止连线重建触发撤销保存
        self._undoing_operation = False  # 标志：正在执行撤销操作，防止撤销过程中的操作触发新的撤销保存
        self._modifying_connection = False  # 标志：正在修改连线，防止删除和添加连接时保存撤销状态
        self._pasting_card = False  # 标志：正在粘贴卡片，防止保存撤销状态

        # 连接滚动条信号用于动态场景扩展
        self.horizontalScrollBar().valueChanged.connect(self._handle_scroll_change)
        self.verticalScrollBar().valueChanged.connect(self._handle_scroll_change)

        # 跟踪闪烁的节点
        self.flashing_node_ids = set()
        
        # 初始化示例节点
        self.init_sample_nodes()
        
        # 初始化小地图
        self.mini_map_visible = True
        self.mini_map = None
        self.init_mini_map()
        
        # 调整场景大小以适应内容
        self.adjust_scene_size()
        
        # 连接信号，当场景内容变化时调整场景大小
        self.scene.changed.connect(self.adjust_scene_size)

    def _is_workflow_running(self):
        """检查工作流是否正在运行"""
        try:
            # 从父级查找MainWindow
            parent = self.parent()
            loop_count = 0
            max_loops = 50  # 最多向上查找50层
            while parent and not hasattr(parent, 'executor') and loop_count < max_loops:
                parent = parent.parent()
                loop_count += 1
            if loop_count >= max_loops:
                parent = None
            main_window = parent
            
            # 如果没找到，从QApplication查找
            if not main_window:
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    for widget in app.allWidgets():
                        if hasattr(widget, 'executor') and hasattr(widget, 'executor_thread'):
                            main_window = widget
                            break
            
            # 检查是否有任务正在运行
            if main_window and hasattr(main_window, 'executor') and hasattr(main_window, 'executor_thread'):
                if (main_window.executor is not None and 
                    main_window.executor_thread is not None and 
                    main_window.executor_thread.isRunning()):
                    return True
                
        except Exception as e:
            print(f"检查任务运行状态时发生错误: {e}")
            
        return False

    def _block_edit_if_running(self, operation_name):
        """如果工作流正在运行，阻止编辑操作并显示提示"""
        try:
            # 基础运行状态检查
            if self._is_workflow_running():
                QMessageBox.warning(
                    self,
                    "操作被禁止",
                    f"工作流正在执行中，暂时无法进行{operation_name}操作。\n\n请等待任务执行完成或停止任务后再试。"
                )
                return True

            # 检查是否有节点处于执行状态
            executing_nodes = []
            for node_id, node in self.nodes.items():
                if hasattr(node, 'execution_status') and node.execution_status in ['running', 'executing']:
                    executing_nodes.append(node_id)

            if executing_nodes:
                QMessageBox.warning(self, "操作被阻止",
                                  f"发现正在执行的节点，请等待完成后再进行{operation_name}操作")
                return True

            return False

        except Exception as e:
            print(f"检查运行状态时发生错误: {e}")
            # 出错时采用保守策略，阻止操作
            QMessageBox.warning(self, "安全检查失败",
                              f"无法确定当前状态，为安全起见阻止{operation_name}操作")
            return True

    def init_sample_nodes(self):
        """初始化示例节点"""
        # 不再自动创建示例节点，只通过主界面创建开始节点和找图节点
        pass

    def add_node(self, node_type, pos):
        """添加节点"""
        # 检查是否正在运行，如果是则阻止添加
        if self._block_edit_if_running("添加节点"):
            return None

        # 将视图坐标转换为场景坐标
        scene_pos = self.mapToScene(pos)
        x = scene_pos.x()
        y = scene_pos.y()
        
        # 检查是否在循环节点内部
        target_container = None
        for item in self.scene.items():
            if hasattr(item, 'title') and item.title == "循环体" and hasattr(item, 'contains_point'):
                if item.contains_point(scene_pos - item.pos()):
                    target_container = item
                    break
        
        # 使用节点管理器创建节点
        if target_container:
            # 在循环节点内部创建节点
            node = node_manager.create_node(node_type, x=0, y=0)
            if node:
                node.setVisible(True)
                node.setZValue(target_container.zValue() + 1)
                target_container.add_internal_node(node)
                node.is_selected = False
                node.setSelected(False)
                # 连接信号
                node.delete_requested.connect(self.delete_node)
                node.copy_requested.connect(self.handle_copy_node)
                node.edit_settings_requested.connect(self.edit_node_settings)
                node.card_clicked.connect(self.handle_card_clicked)
                # 存储节点
                self.nodes[node.id] = node
                # 发射信号
                self.card_added.emit(node)
                # 保存添加节点状态用于撤销
                if not self._loading_workflow and not self._undoing_operation:
                    self._save_add_node_state_for_undo(node.id, node_type, x, y, {})
                # 触发场景重绘
                self.scene.update()
                return node
        else:
            # 在画布上创建节点
            node = node_manager.create_node(node_type, x=x, y=y)
            if node:
                # 确保新节点状态正确
                node.is_selected = False
                node.setSelected(False)
                node.setVisible(True)
                node.setZValue(1)
                
                # 取消所有其他节点的选中状态
                for item in self.scene.items():
                    if hasattr(item, 'is_selected') and item != node:
                        item.is_selected = False
                        item.setSelected(False)
                        item.update()
                    # 确保所有现有节点可见
                    if hasattr(item, 'title') and hasattr(item, 'ports'):
                        if not item.isVisible():
                            item.setVisible(True)
                        if item.zValue() < 1:
                            item.setZValue(1)
                        item.update()
                
                # 添加新节点到场景
                self.scene.addItem(node)
                
                # 连接信号
                node.delete_requested.connect(self.delete_node)
                node.copy_requested.connect(self.handle_copy_node)
                node.edit_settings_requested.connect(self.edit_node_settings)
                node.card_clicked.connect(self.handle_card_clicked)
                
                # 存储节点
                self.nodes[node.id] = node
                
                # 发射信号
                self.card_added.emit(node)
                
                # 保存添加节点状态用于撤销
                if not self._loading_workflow and not self._undoing_operation:
                    self._save_add_node_state_for_undo(node.id, node_type, x, y, {})
                
                # 再次确保新节点可见
                node.setVisible(True)
                node.setZValue(1)
                
                # 触发场景重绘
                self.scene.update()
                return node
        return None

    def delete_node(self, node_id):
        """删除节点"""
        print(f"删除节点请求: {node_id}")
        # 检查是否正在运行，如果是则阻止删除
        if self._block_edit_if_running("删除节点"):
            print("删除操作被阻止：工作流正在运行")
            return
        
        if node_id in self.nodes:
            print(f"找到节点: {node_id}")
            node = self.nodes[node_id]
            # 防止删除开始节点
            if node.title == "开始":
                print("开始节点不允许删除")
                return
            # 保存删除节点状态用于撤销
            if not self._loading_workflow and not self._undoing_operation:
                self._save_delete_node_state_for_undo(node)
            
            # 删除节点及其所有连线
            for port in node.ports:
                # 先收集所有连接
                connections = list(port.connections)
                for connection in connections:
                    # 从场景中移除连接
                    if connection.scene():
                        connection.scene().removeItem(connection)
                    # 从另一端端口的connections列表中移除
                    if connection.start_port and connection.start_port != port:
                        if hasattr(connection.start_port, 'connections') and connection in connection.start_port.connections:
                            connection.start_port.connections.remove(connection)
                    if connection.end_port and connection.end_port != port:
                        if hasattr(connection.end_port, 'connections') and connection in connection.end_port.connections:
                            connection.end_port.connections.remove(connection)
                    # 从视图的连接列表中移除
                    if connection in self.connections:
                        self.connections.remove(connection)
                # 清空当前端口的connections列表
                if hasattr(port, 'connections'):
                    port.connections.clear()
            
            # 从场景中移除节点
            if node.scene():
                print(f"从场景中移除节点: {node_id}")
                node.scene().removeItem(node)
            else:
                print(f"节点不在场景中: {node_id}")
            
            # 从节点字典中移除
            del self.nodes[node_id]
            print(f"从节点字典中移除: {node_id}")
            
            # 发射信号
            self.card_deleted.emit(node_id)
            print(f"发射删除信号: {node_id}")
            
            # 发送信号，更新属性面板
            signal_manager.node_selected_signal.emit({})
            print("发送属性面板更新信号")
        else:
            print(f"节点不存在于字典中: {node_id}")

    def handle_copy_node(self, node_id, parameters):
        """处理复制节点"""
        # 检查是否正在运行，如果是则阻止复制
        if self._block_edit_if_running("复制节点"):
            return
        
        if node_id in self.nodes:
            self.copied_card_data = {'node_id': node_id, 'parameters': parameters}

    def handle_paste_node(self, pos):
        """处理粘贴节点"""
        if not self.copied_card_data:
            return
        
        # 检查是否正在运行，如果是则阻止粘贴
        if self._block_edit_if_running("粘贴节点"):
            return
        
        node_id = self.copied_card_data['node_id']
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node_type = node.__class__.__name__
            # 粘贴到指定位置
            self._pasting_card = True
            new_node = self.add_node(node_type, pos)
            self._pasting_card = False
            if new_node:
                # 应用复制的参数
                new_node.variables.update(self.copied_card_data['parameters'])
                new_node.update()

    def edit_node_settings(self, node_id):
        """编辑节点设置"""
        # 检查是否正在运行，如果是则阻止编辑
        if self._block_edit_if_running("编辑节点设置"):
            return
        
        if node_id in self.nodes:
            node = self.nodes[node_id]
            # 这里可以打开参数设置对话框
            print(f"编辑节点 {node_id} 的设置")

    def handle_card_clicked(self, node_id):
        """处理卡片点击"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            # 确保节点可见
            if not node.isVisible():
                node.setVisible(True)
            if node.zValue() < 1:
                node.setZValue(1)
            # 取消其他节点的选中状态
            for item in self.scene.items():
                if hasattr(item, 'is_selected') and item != node:
                    item.is_selected = False
                    item.setSelected(False)
                    item.update()
            # 标记当前节点为选中
            node.is_selected = True
            node.setSelected(True)
            node.update()
            # 更新内置变量
            node.update_variables()
            # 发射节点选中信号
            signal_manager.node_selected_signal.emit(node.variables)

    def add_connection(self, start_port, end_port):
        """添加连接"""
        # 检查是否正在运行，如果是则阻止添加连接
        if self._block_edit_if_running("添加连接"):
            return None
        
        # 验证端口有效性
        if not start_port or not end_port:
            return None
        
        # 验证端口类型匹配
        execution_types = ["exec", "运行", "执行", "完成"]
        is_execution_flow = (start_port.data_type in execution_types and end_port.data_type in execution_types)
        
        # 支持反向连接：input -> output
        if start_port.port_type == "input" and end_port.port_type == "output":
            is_data_flow = (start_port.data_type == end_port.data_type or start_port.data_type == "any")
        # 正常连接：output -> input
        elif start_port.port_type == "output" and end_port.port_type == "input":
            is_data_flow = (start_port.data_type == end_port.data_type or end_port.data_type == "any")
        else:
            is_data_flow = False
        
        if not (is_execution_flow or is_data_flow):
            return None
        
        # 检查端口连接数限制
        # 由于所有端口的max_connections都设置为-1，这里可以跳过检查
        # if start_port.port_type == "output":
        #     current_connections = len(getattr(start_port, 'connections', []))
        #     if start_port.max_connections != -1 and current_connections >= start_port.max_connections:
        #         return None
        # elif end_port.port_type == "input":
        #     current_connections = len(getattr(end_port, 'connections', []))
        #     if end_port.max_connections != -1 and current_connections >= end_port.max_connections:
        #         return None
        
        # 检查是否已存在相同连接
        for existing_conn in self.connections:
            if (existing_conn.start_port == start_port and existing_conn.end_port == end_port) or \
               (existing_conn.start_port == end_port and existing_conn.end_port == start_port):
                return existing_conn
        
        # 创建连接
        try:
            # 设置_modifying_connection标志，防止删除旧连接时保存撤销状态
            self._modifying_connection = True
            
            connection = Connection(start_port, end_port)
            if connection.start_port and connection.end_port:
                self.scene.addItem(connection)
                # 添加到连接线列表
                self.connections.append(connection)
                # 确保两个节点都可见
                start_node = start_port.parentItem()
                end_node = end_port.parentItem()
                if start_node:
                    start_node.setVisible(True)
                    start_node.setZValue(1)
                if end_node:
                    end_node.setVisible(True)
                    end_node.setZValue(1)
                # 发射信号
                self.connection_added.emit(start_port.parentItem(), end_port.parentItem(), "default")
                # 保存连接状态用于撤销
                if not self._loading_workflow and not self._updating_sequence and not self._undoing_operation:
                    self._save_add_connection_state_for_undo(start_port, end_port)
                return connection
        except Exception as e:
            print(f"创建连接时出错: {e}")
        finally:
            # 无论如何都要重置_modifying_connection标志
            self._modifying_connection = False
        return None

    def remove_connection(self, connection):
        """移除连接"""
        # 检查是否正在运行，如果是则阻止删除连接
        if self._block_edit_if_running("删除连接"):
            return
        
        # 验证连接对象的有效性
        if not connection:
            return
        
        # 检查连接是否还在连接列表中
        if connection not in self.connections:
            return
        
        # 保存连接状态用于撤销
        if (not self._deleting_card and not self._loading_workflow and not self._updating_sequence and
            not self._undoing_operation and not self._modifying_connection):
            try:
                self._save_connection_state_for_undo(connection)
            except Exception as e:
                print(f"保存连接撤销状态失败: {e}")
        
        # 调用连接的delete_connection方法，它会处理所有的清理工作
        connection.delete_connection()
        
        # 从视图的连接列表中移除
        try:
            if connection in self.connections:
                self.connections.remove(connection)
        except Exception as e:
            print(f"从视图连接列表移除连接失败: {e}")

        # 发射信号
        self.connection_deleted.emit(connection)

    def wheelEvent(self, event):
        """处理鼠标滚轮事件用于缩放"""
        delta = event.angleDelta().y()

        if delta > 0:
            # 放大
            scale_factor = self.zoom_factor_base
        elif delta < 0:
            # 缩小
            scale_factor = 1.0 / self.zoom_factor_base
        else:
            # 无垂直滚动
            super().wheelEvent(event)  # 传递给基类处理
            return

        # 应用缩放
        self.scale(scale_factor, scale_factor)
        event.accept()  # 指示事件已处理
        
        # 更新小地图
        if self.mini_map and self.mini_map_visible:
            self.update_mini_map()
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        from PySide6.QtCore import Qt
        
        if event.key() == Qt.Key_K:
            # 切换小地图显示/隐藏
            self.mini_map_visible = not self.mini_map_visible
            if self.mini_map:
                self.mini_map.setVisible(self.mini_map_visible)
        
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        try:
            # 首先清理可能存在的临时线条
            self.cleanup_temp_line()
            
            # 重置吸附状态
            self.is_snapped = False
            self.snapped_target_port = None
            
            # 重置状态机状态
            self.state_machine.reset_to_idle()
            
            # 重置拖拽相关状态
            self.drag_start_port = None
            
            # 获取点击位置的项
            item = self.itemAt(event.pos())

            # 检查是否点击了端口
            if item and hasattr(item, 'port_type'):
                # 确保端口的父节点（节点）可见
                parent_node = item.parentItem()
                if parent_node:
                    parent_node.setVisible(True)
                    # 确保父节点zValue合理
                    if parent_node.zValue() < 1:
                        parent_node.setZValue(1)
                    # 如果父节点还有父节点（循环体），也确保其可见
                    grandparent_node = parent_node.parentItem()
                    if grandparent_node:
                        grandparent_node.setVisible(True)
                        if grandparent_node.zValue() < 1:
                            grandparent_node.setZValue(1)
                
                # 检查端口是否已经达到最大连接数
                current_connections = len(getattr(item, 'connections', []))
                if item.max_connections != -1 and current_connections >= item.max_connections:
                    # 已经达到最大连接数，不允许再创建连接
                    return
                
                # 无论端口类型是input还是output，都允许开始拖拽连线
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                self.state_machine.transition(EditorStateMachine.DRAGGING_CONNECTION)
                self.drag_start_port = item
                
                # 创建临时线条
                # 根据端口类型计算不同的起点位置
                if item.port_type == "output":
                    # 输出端口：使用端口中心作为起点，确保在节点内部
                    start_pos = item.mapToScene(QPointF(8, 0))
                else:
                    # 输入端口：使用端口中心作为起点，确保在节点内部
                    start_pos = item.mapToScene(QPointF(-8, 0))
                self.temp_line = QGraphicsLineItem(
                    start_pos.x(), start_pos.y(), start_pos.x(), start_pos.y()
                )
                self.temp_line.setPen(self.temp_line_pen)
                self.temp_line.setZValue(2)  # 临时线条在节点上方
                self.scene.addItem(self.temp_line)
                
                return

            # 检查是否点击了节点的子组件
            node = item
            while node and not (hasattr(node, 'title') and hasattr(node, 'ports')):
                node = node.parentItem()

            # 点击了连线
            if not node and item:
                from 节点核心.连线类 import Connection
                if isinstance(item, Connection):
                    for scene_item in self.scene.items():
                        if hasattr(scene_item, 'is_selected'):
                            scene_item.is_selected = False
                            scene_item.update()
                    item.is_selected = True
                    item.update()
                    self.state_machine.transition(EditorStateMachine.CONNECTION_SELECTED)
                    signal_manager.node_selected_signal.emit({})
                    return

            # 点击了节点 - 切换到NoDrag，让节点可以拖动
            if node:
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                self.state_machine.transition(EditorStateMachine.NODE_SELECTED)
                
                for scene_item in self.scene.items():
                    if hasattr(scene_item, 'is_selected') and scene_item != node:
                        scene_item.is_selected = False
                        scene_item.setSelected(False)
                        scene_item.update()

                node.is_selected = True
                node.setSelected(True)
                node.update()
                node.update_variables()

                signal_manager.node_selected_signal.emit(node.variables)
            else:
                # 点击了空白处，重置到空闲状态
                self.state_machine.reset_to_idle()
                # 取消所有选中状态
                for scene_item in self.scene.items():
                    if hasattr(scene_item, 'is_selected'):
                        scene_item.is_selected = False
                        scene_item.setSelected(False)
                        scene_item.update()
                # 发射信号
                signal_manager.node_selected_signal.emit({})

            # 调用父类，让Qt处理
            super().mousePressEvent(event)
        except Exception as e:
            # 忽略事件处理错误，确保节点不会因为事件处理问题而消失
            pass

    def mouseMoveEvent(self, event):
        if self.state_machine.get_state() == EditorStateMachine.DRAGGING_CONNECTION and self.drag_start_port and self.temp_line:
            try:
                # 检查drag_start_port是否仍然有效
                if not self.drag_start_port:
                    raise RuntimeError("Start port is None")
                

                
                # 获取当前鼠标在场景中的位置
                end_pos = self.mapToScene(event.pos())
                # 尝试获取drag_start_port的位置
                # 根据端口类型计算不同的起点位置
                if self.drag_start_port.port_type == "output":
                    # 输出端口：使用端口右侧尖端作为起点
                    start_pos = self.drag_start_port.mapToScene(QPointF(16, 0))
                else:
                    # 输入端口：使用端口左侧尖端作为起点
                    start_pos = self.drag_start_port.mapToScene(QPointF(-16, 0))
                
                # 实现端口吸附功能
                target_pos = end_pos
                self.is_snapped = False
                self.snapped_target_port = None
                snap_distance_sq = SNAP_DISTANCE ** 2
                
                # 查找所有端口
                for item in self.scene.items():
                    try:
                        if hasattr(item, 'port_type') and item != self.drag_start_port:
                            # 检查端口类型是否匹配
                            execution_types = ["exec", "运行", "执行", "完成"]
                            is_execution_flow = (self.drag_start_port.data_type in execution_types and item.data_type in execution_types)
                            
                            # 支持反向连接：input -> output
                            if self.drag_start_port.port_type == "input" and item.port_type == "output":
                                is_data_flow = (self.drag_start_port.data_type == item.data_type or self.drag_start_port.data_type == "any")
                            # 正常连接：output -> input
                            elif self.drag_start_port.port_type == "output" and item.port_type == "input":
                                is_data_flow = (self.drag_start_port.data_type == item.data_type or item.data_type == "any")
                            else:
                                is_data_flow = False
                            
                            if is_execution_flow or is_data_flow:
                                # 计算距离
                                # 根据端口类型计算不同的端口位置
                                if item.port_type == "output":
                                    # 输出端口：使用端口右侧尖端作为位置
                                    port_pos = item.mapToScene(QPointF(16, 0))
                                else:
                                    # 输入端口：使用端口左侧尖端作为位置
                                    port_pos = item.mapToScene(QPointF(-16, 0))
                                delta = end_pos - port_pos
                                dist_sq = delta.x()**2 + delta.y()**2
                                
                                if dist_sq <= snap_distance_sq:
                                    target_pos = port_pos
                                    self.is_snapped = True
                                    self.snapped_target_port = item
                                    break
                    except (RuntimeError, AttributeError):
                        # 如果item已经被删除，跳过
                        continue
            
            except (RuntimeError, AttributeError):
                # 如果drag_start_port已经被删除，清理临时线条并重置状态
                self.cleanup_temp_line()
                self.state_machine.reset_to_idle()
                self.drag_start_port = None
                self.is_snapped = False
                self.snapped_target_port = None
                return
            
            # 更新临时线条
            try:
                line = QLineF(start_pos, target_pos)
                self.temp_line.setLine(line)
                
                # 根据吸附状态更新线条样式
                if self.is_snapped:
                    self.temp_line.setPen(self.temp_line_snap_pen)
                else:
                    self.temp_line.setPen(self.temp_line_pen)
                
                # 强制刷新线条和视图
                self.temp_line.update()
                self.scene.update()
            except (RuntimeError, AttributeError):
                # 如果临时线条已经被删除，清理状态
                self.cleanup_temp_line()
                self.state_machine.reset_to_idle()
                self.drag_start_port = None
                self.is_snapped = False
                self.snapped_target_port = None
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # 处理连线拖动结束
        if self.state_machine.get_state() == EditorStateMachine.DRAGGING_CONNECTION:
            try:
                # 检查drag_start_port是否仍然有效
                if not self.drag_start_port:
                    raise RuntimeError("Start port is None")

                # 尝试访问drag_start_port的属性，检查它是否仍然有效
                _ = self.drag_start_port.port_type
            except (RuntimeError, AttributeError):
                # 如果drag_start_port已经被删除，清理临时线条并重置状态
                self.cleanup_temp_line()
                self.state_machine.reset_to_idle()
                self.drag_start_port = None
                self.is_snapped = False
                self.snapped_target_port = None
                # 恢复ScrollHandDrag模式
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                return
            
            try:
                # 使用吸附的目标端口（如果有）
                target_port = self.snapped_target_port
                if not target_port:
                    item = self.itemAt(event.pos())
                    if item and hasattr(item, 'port_type'):
                        target_port = item

                if target_port and hasattr(target_port, 'port_type'):
                    try:
                        # 检查target_port是否仍然有效
                        _ = target_port.port_type
                    except (RuntimeError, AttributeError):
                        # 如果target_port已经被删除，清理临时线条并重置状态
                        self.cleanup_temp_line()
                        self.state_machine.reset_to_idle()
                        self.drag_start_port = None
                        self.is_snapped = False
                        self.snapped_target_port = None
                        # 恢复ScrollHandDrag模式
                        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                        return
                    
                    try:
                        # 定义执行流类型列表
                        execution_types = ["exec", "运行", "执行", "完成"]
                        is_execution_flow = (self.drag_start_port.data_type in execution_types and target_port.data_type in execution_types)
                        
                        # 支持反向连接：input -> output
                        if self.drag_start_port.port_type == "input" and target_port.port_type == "output":
                            is_data_flow = (self.drag_start_port.data_type == target_port.data_type or self.drag_start_port.data_type == "any")
                            # 对于反向连接，检查目标输出端口是否已经达到最大连接数
                            target_connections = len(getattr(target_port, 'connections', []))
                            if target_port.max_connections != -1 and target_connections >= target_port.max_connections:
                                # 目标端口已经达到最大连接数，不允许再创建连接
                                pass
                            elif is_execution_flow or is_data_flow:
                                try:
                                    # 对于反向连接，交换start_port和target_port
                                    self.add_connection(target_port, self.drag_start_port)
                                except Exception as e:
                                    print(f"创建连接时出错: {e}")
                        # 正常连接：output -> input
                        elif self.drag_start_port.port_type == "output" and target_port.port_type == "input":
                            is_data_flow = (self.drag_start_port.data_type == target_port.data_type or target_port.data_type == "any")
                            # 检查目标输入端口是否已经达到最大连接数
                            target_connections = len(getattr(target_port, 'connections', []))
                            if target_port.max_connections != -1 and target_connections >= target_port.max_connections:
                                # 目标端口已经达到最大连接数，不允许再创建连接
                                pass
                            elif is_execution_flow or is_data_flow:
                                try:
                                    self.add_connection(self.drag_start_port, target_port)
                                except Exception as e:
                                    print(f"创建连接时出错: {e}")
                    except (RuntimeError, AttributeError):
                        # 如果在处理过程中端口被删除，清理状态
                        pass
                else:
                    # 拉线连空显示节点创建器
                    # 保存起始端口和释放位置
                    self._drag_start_port = self.drag_start_port
                    self._drop_pos = event.pos()
                    
                    # 显示节点创建器
                    self.show_node_creator_for_wire(event.pos())
            except (RuntimeError, AttributeError):
                # 捕获其他可能的错误
                pass
            finally:
                # 移除临时线条
                self.cleanup_temp_line()

                # 重置状态
                self.state_machine.reset_to_idle()
                self.drag_start_port = None
                self.is_snapped = False
                self.snapped_target_port = None

        # 恢复ScrollHandDrag模式
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        # 强制刷新视图，避免线条残留
        try:
            self.scene.update()
        except Exception:
            pass

        super().mouseReleaseEvent(event)

    def cleanup_temp_line(self):
        """清理临时线条"""
        if self.temp_line:
            try:
                if self.temp_line.scene() == self.scene:
                    self.scene.removeItem(self.temp_line)
                    # 确保线条被完全移除
                    self.scene.update()
                    self.viewport().update()
            except Exception as e:
                print(f"清理临时线条时出错: {e}")
            finally:
                # 强制设置为None，确保引用被清理
                self.temp_line = None

    def show_context_menu(self, pos):
        """显示右键菜单"""
        # 检查点击的位置是否是空白画布
        item = self.itemAt(pos)
        
        # 检查是否点击了节点
        clicked_node = None
        if item:
            # 检查是否点击了节点的子组件
            node = item
            while node and not (hasattr(node, 'title') and hasattr(node, 'ports')):
                node = node.parentItem()
            if node:
                clicked_node = node
        
        # 检查是否有选中的节点或连线
        selected_nodes = []
        selected_connections = []
        
        for scene_item in self.scene.items():
            if hasattr(scene_item, 'is_selected') and scene_item.is_selected:
                if hasattr(scene_item, 'title') and hasattr(scene_item, 'ports'):
                    # 选中的节点
                    selected_nodes.append(scene_item)
                elif hasattr(scene_item, 'start_port') and hasattr(scene_item, 'end_port'):
                    # 选中的连线
                    selected_connections.append(scene_item)
        
        # 如果点击了节点，显示删除菜单
        if clicked_node:
            print(f"右键点击了节点: {clicked_node.id}, 标题: {clicked_node.title}")
            # 确保点击的节点被选中
            for scene_item in self.scene.items():
                if hasattr(scene_item, 'is_selected'):
                    scene_item.is_selected = (scene_item == clicked_node)
                    scene_item.update()
            # 发射节点选中信号
            clicked_node.update_variables()
            signal_manager.node_selected_signal.emit(clicked_node.variables)
            # 检查工作流是否正在运行
            is_running = self._is_workflow_running()
            print(f"工作流运行状态: {is_running}")
            # 创建菜单
            from PySide6.QtWidgets import QMenu
            from PySide6.QtGui import QAction
            menu = QMenu()
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2D2D2D;
                    color: #E0E0E0;
                    border: 1px solid #555555;
                    border-radius: 4px;
                    padding: 4px 0;
                    min-width: 200px;
                }
                QMenu::item {
                    padding: 6px 20px;
                    spacing: 10px;
                }
                QMenu::item:selected {
                    background-color: #1E90FF;
                    color: white;
                }
                QMenu::item:disabled {
                    color: #aaa;
                    background-color: transparent;
                }
                QMenu::separator {
                    height: 1px;
                    background: #555555;
                    margin-left: 10px;
                    margin-right: 10px;
                }
            """)
            # 添加删除选项
            delete_action = QAction("删除卡片", menu)
            def on_delete():
                print(f"点击了删除按钮，删除节点: {clicked_node.id}")
                self.delete_node(clicked_node.id)
            delete_action.triggered.connect(on_delete)
            delete_action.setEnabled(not is_running)
            if is_running:
                delete_action.setToolTip("工作流运行期间无法删除卡片")
            menu.addAction(delete_action)
            # 显示菜单
            global_pos = self.mapToGlobal(pos)
            print(f"显示菜单在位置: {global_pos}")
            selected_action = menu.exec(global_pos)
            print(f"选中的动作: {selected_action.text() if selected_action else '无'}")
        # 如果点击的是空白画布，显示节点创建界面
        elif not item:
            # 处理粘贴操作
            if self.copied_card_data:
                self.handle_paste_node(pos)
            else:
                # 显示节点创建界面
                self.show_node_creator(pos)

    def delete_selected_nodes(self, nodes):
        """删除选中的节点"""
        for node in nodes:
            if hasattr(node, 'id'):
                self.delete_node(node.id)

    def delete_selected_connections(self, connections):
        """删除选中的连线"""
        for connection in connections:
            self.remove_connection(connection)
    
    def create_style_builder(self, pos):
        """创建样式构造器"""
        # 将视图坐标转换为场景坐标
        scene_pos = self.mapToScene(pos)
        x = scene_pos.x()
        y = scene_pos.y()
        
        # 创建样式构造器窗口
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QColorDialog, QComboBox
        from PySide6.QtGui import QColor
        
        dialog = QDialog(self)
        dialog.setWindowTitle("样式构造器")
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # 添加标题
        title_label = QLabel("创建样式")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # 添加样式名称输入
        name_label = QLabel("样式名称:")
        layout.addWidget(name_label)
        name_input = QLineEdit()
        name_input.setPlaceholderText("输入样式名称")
        layout.addWidget(name_input)
        
        # 添加颜色选择
        color_label = QLabel("样式颜色:")
        layout.addWidget(color_label)
        color_button = QPushButton("选择颜色")
        color = QColor(100, 149, 237)  # 默认颜色
        
        def choose_color():
            nonlocal color
            new_color = QColorDialog.getColor(color, dialog, "选择颜色")
            if new_color.isValid():
                color = new_color
                color_button.setStyleSheet(f"background-color: {color.name()};")
        
        color_button.setStyleSheet(f"background-color: {color.name()};")
        color_button.clicked.connect(choose_color)
        layout.addWidget(color_button)
        
        # 添加样式类型选择
        type_label = QLabel("样式类型:")
        layout.addWidget(type_label)
        type_combo = QComboBox()
        type_combo.addItems(["节点样式", "连线样式", "界面样式"])
        layout.addWidget(type_combo)
        
        # 添加创建按钮
        create_button = QPushButton("创建样式")
        
        def create_style():
            style_name = name_input.text() or "默认样式"
            style_type = type_combo.currentText()
            
            # 这里可以添加样式创建逻辑
            print(f"创建样式: {style_name}, 类型: {style_type}, 颜色: {color.name()}")
            
            # 关闭对话框
            dialog.accept()
        
        create_button.clicked.connect(create_style)
        layout.addWidget(create_button)
        
        # 显示对话框
        dialog.exec()
    
    def show_node_creator(self, pos):
        """在画布上显示节点创建界面"""
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTreeWidget, QTreeWidgetItem, QLabel, QApplication
        from PySide6.QtCore import Qt
        
        # 创建临时界面
        self.node_creator_widget = QWidget(self)
        self.node_creator_widget.setFixedSize(300, 400)
        self.node_creator_widget.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        
        # 设置样式
        self.node_creator_widget.setStyleSheet("""
            QWidget {
                background-color: #303040;
                color: #E0E0E0;
                border: 1px solid #1E90FF;
                border-radius: 10px;
                
            }
            QLabel {
                background-color: #3498DB;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QLineEdit {
                background-color: #3D3D3D;
                color: #E0E0E0;
                border: 1px solid #1E90FF;
                border-radius: 6px;
                padding: 8px 12px;
                margin: 10px 10px 0 10px;
                font-size: 13px;
            }
            QTreeWidget {
                background-color: #303040;
                color: #E0E0E0;
                border: none;
                font-size: 13px;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QTreeWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid #444444;
            }
            QTreeWidget::item:selected {
                background-color: #1E90FF;
                color: white;
            }
            QTreeWidget::branch {
                background: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 0px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: transparent;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout(self.node_creator_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 搜索框
        search_input = QLineEdit()
        search_input.setPlaceholderText("搜索节点...")
        main_layout.addWidget(search_input)
        
        # 节点树
        node_tree = QTreeWidget()
        node_tree.setHeaderHidden(True)
        main_layout.addWidget(node_tree)
        
        # 加载节点
        node_classes = node_manager.get_node_classes()
        categories = {
            "常用节点": [],
            "流程控制": [],
            "工具": []
        }
        
        for node_name, node_class in node_classes.items():
            if node_name == "StartNode":
                continue
            
            try:
                temp_node = node_class()
                node_title = temp_node.title
                del temp_node
            except:
                node_title = node_name
            
            if node_name in ["FindImageNode", "ClickNode", "WaitNode"]:
                categories["常用节点"].append((node_name, node_title))
            elif node_name in ["ForLoopNode"]:
                categories["流程控制"].append((node_name, node_title))
            else:
                categories["工具"].append((node_name, node_title))
        
        for category, nodes in categories.items():
            if nodes:
                category_item = QTreeWidgetItem(node_tree, [category])
                category_item.setExpanded(True)
                
                for node_name, node_title in nodes:
                    node_item = QTreeWidgetItem(category_item, [node_title])
                    node_item.setData(0, Qt.UserRole, node_name)
        
        # 搜索功能
        def filter_nodes(text):
            node_tree.clear()
            
            filtered_nodes = []
            for node_name, node_class in node_classes.items():
                if node_name == "StartNode":
                    continue
                
                try:
                    temp_node = node_class()
                    node_title = temp_node.title
                    del temp_node
                except:
                    node_title = node_name
                
                # 直接比较字符串，不使用lower()，因为中文不需要大小写转换
                if text in node_title or text in node_name:
                    filtered_nodes.append((node_name, node_title))
            
            for node_name, node_title in filtered_nodes:
                node_item = QTreeWidgetItem(node_tree, [node_title])
                node_item.setData(0, Qt.UserRole, node_name)
        
        search_input.textChanged.connect(filter_nodes)
        
        # 节点选择处理
        def on_item_clicked(item, column):
            if item.childCount() == 0:
                node_type = item.data(0, Qt.UserRole)
                if node_type:
                    self.add_node(node_type, pos)
                self.node_creator_widget.close()
                del self.node_creator_widget
        
        node_tree.itemClicked.connect(on_item_clicked)
        
        # 显示位置
        global_pos = self.mapToGlobal(pos)
        self.node_creator_widget.move(global_pos)
        self.node_creator_widget.show()
        
        # 激活窗口并设置焦点，确保可以触发输入法
        self.node_creator_widget.activateWindow()
        self.node_creator_widget.setFocus()
        search_input.setFocus()
        # 模拟鼠标点击，确保输入法被触发
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QPoint
        # 创建一个鼠标点击事件并发送给搜索框
        click_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        # 发送事件
        QApplication.postEvent(search_input, click_event)
    
    def eventFilter(self, obj, event):
        """事件过滤器，用于检测点击外部"""
        # 移除对节点创建器的事件过滤，避免干扰搜索框输入
        return False
    
    def show_node_creator_for_wire(self, pos):
        """为拉线连空显示节点创建器"""
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTreeWidget, QTreeWidgetItem, QLabel, QApplication
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QPoint
        
        # 创建临时界面
        self.node_creator_widget = QWidget(self)
        self.node_creator_widget.setFixedSize(300, 400)
        self.node_creator_widget.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        
        # 设置样式
        self.node_creator_widget.setStyleSheet("""
            QWidget {
                background-color: #303040;
                color: #E0E0E0;
                border: 1px solid #1E90FF;
                border-radius: 10px;
                
            }
            QLabel {
                background-color: #3498DB;
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QLineEdit {
                background-color: #3D3D3D;
                color: #E0E0E0;
                border: 1px solid #1E90FF;
                border-radius: 6px;
                padding: 8px 12px;
                margin: 10px 10px 0 10px;
                font-size: 13px;
            }
            QTreeWidget {
                background-color: #303040;
                color: #E0E0E0;
                border: none;
                font-size: 13px;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QTreeWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid #444444;
            }
            QTreeWidget::item:selected {
                background-color: #1E90FF;
                color: white;
            }
            QTreeWidget::branch {
                background: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 0px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: transparent;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        
        # 主布局
        main_layout = QVBoxLayout(self.node_creator_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 标题
        title_label = QLabel("选择节点类型")
        title_label.setStyleSheet("padding: 8px 10px; border-bottom: 1px solid #555555;")
        main_layout.addWidget(title_label)
        
        # 搜索框
        search_input = QLineEdit()
        search_input.setPlaceholderText("搜索节点...")
        main_layout.addWidget(search_input)
        
        # 节点树
        node_tree = QTreeWidget()
        node_tree.setHeaderHidden(True)
        main_layout.addWidget(node_tree)
        
        # 加载节点
        node_classes = node_manager.get_node_classes()
        categories = {
            "常用节点": [],
            "流程控制": [],
            "工具": []
        }
        
        for node_name, node_class in node_classes.items():
            if node_name == "StartNode":
                continue
            
            try:
                temp_node = node_class()
                node_title = temp_node.title
                del temp_node
            except:
                node_title = node_name
            
            if node_name in ["FindImageNode", "ClickNode", "WaitNode"]:
                categories["常用节点"].append((node_name, node_title))
            elif node_name in ["ForLoopNode"]:
                categories["流程控制"].append((node_name, node_title))
            else:
                categories["工具"].append((node_name, node_title))
        
        for category, nodes in categories.items():
            if nodes:
                category_item = QTreeWidgetItem(node_tree, [category])
                category_item.setExpanded(True)
                
                for node_name, node_title in nodes:
                    node_item = QTreeWidgetItem(category_item, [node_title])
                    node_item.setData(0, Qt.UserRole, node_name)
        
        # 搜索功能
        def filter_nodes(text):
            node_tree.clear()
            
            filtered_nodes = []
            for node_name, node_class in node_classes.items():
                if node_name == "StartNode":
                    continue
                
                try:
                    temp_node = node_class()
                    node_title = temp_node.title
                    del temp_node
                except:
                    node_title = node_name
                
                if text in node_title or text in node_name:
                    filtered_nodes.append((node_name, node_title))
            
            for node_name, node_title in filtered_nodes:
                node_item = QTreeWidgetItem(node_tree, [node_title])
                node_item.setData(0, Qt.UserRole, node_name)
        
        search_input.textChanged.connect(filter_nodes)
        
        # 节点选择处理
        def on_item_clicked(item, column):
            if item.childCount() == 0:
                node_type = item.data(0, Qt.UserRole)
                if node_type:
                    # 创建新节点
                    new_node = self.add_node(node_type, self._drop_pos)
                    if new_node:
                        # 为新节点添加对应的端口
                        if self._drag_start_port.port_type == "output":
                            # 如果起始端口是输出，为新节点添加输入端口
                            new_port = new_node.add_input_port(self._drag_start_port.data_type, "输入")
                        else:
                            # 如果起始端口是输入，为新节点添加输出端口
                            new_port = new_node.add_output_port(self._drag_start_port.data_type, "输出")
                        
                        # 创建连接
                        try:
                            if self._drag_start_port.port_type == "output":
                                self.add_connection(self._drag_start_port, new_port)
                            else:
                                self.add_connection(new_port, self._drag_start_port)
                        except Exception as e:
                            print(f"创建连接时出错: {e}")
                # 关闭窗口
                self.node_creator_widget.close()
                del self.node_creator_widget
                # 清理临时变量
                del self._drag_start_port
                del self._drop_pos
        
        node_tree.itemClicked.connect(on_item_clicked)
        
        # 显示位置
        global_pos = self.mapToGlobal(pos)
        self.node_creator_widget.move(global_pos)
        self.node_creator_widget.show()
        
        # 激活窗口并设置焦点，确保可以触发输入法
        self.node_creator_widget.activateWindow()
        self.node_creator_widget.setFocus()
        search_input.setFocus()
        # 模拟鼠标点击，确保输入法被触发
        click_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPoint(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        # 发送事件
        QApplication.postEvent(search_input, click_event)

    def dragEnterEvent(self, event):
        """处理拖入事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """处理拖动移动事件"""
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """处理放置事件"""
        if event.mimeData().hasText():
            node_type = event.mimeData().text()
            pos = event.pos()
            self.add_node(node_type, pos)
            event.acceptProposedAction()

    def on_selection_changed(self):
        selected_items = self.scene.selectedItems()

        for scene_item in self.scene.items():
            if hasattr(scene_item, 'is_selected'):
                scene_item.is_selected = False
                scene_item.update()
            # 确保所有节点可见
            if hasattr(scene_item, 'title') and hasattr(scene_item, 'ports'):
                if not scene_item.isVisible():
                    scene_item.setVisible(True)
                if scene_item.zValue() < 1:
                    scene_item.setZValue(1)
                scene_item.update()

        node_selected = False
        for item in selected_items:
            if hasattr(item, 'is_selected'):
                item.is_selected = True
                item.update()

            if not node_selected and hasattr(item, 'title') and hasattr(item, 'ports'):
                # 确保选中的节点可见
                if not item.isVisible():
                    item.setVisible(True)
                if item.zValue() < 1:
                    item.setZValue(1)
                item.update_variables()
                signal_manager.node_selected_signal.emit(item.variables)
                node_selected = True

        if not node_selected:
            signal_manager.node_selected_signal.emit({})
        
        # 触发场景重绘
        self.scene.update()

    def _handle_scroll_change(self, value):
        """处理滚动条变化，动态扩展场景"""
        # 这里可以添加动态扩展场景的逻辑
        pass
    
    def adjust_scene_size(self):
        """根据场景内容调整场景大小"""
        try:
            # 收集所有项目的边界
            items = self.scene.items()
            if not items:
                return
            
            # 初始化边界
            min_x = float('inf')
            min_y = float('inf')
            max_x = float('-inf')
            max_y = float('-inf')
            
            # 计算所有项目的边界
            for item in items:
                if item.isVisible():
                    rect = item.boundingRect()
                    scene_rect = item.mapToScene(rect).boundingRect()
                    min_x = min(min_x, scene_rect.left())
                    min_y = min(min_y, scene_rect.top())
                    max_x = max(max_x, scene_rect.right())
                    max_y = max(max_y, scene_rect.bottom())
            
            # 添加边距
            padding = 100
            new_rect = QRectF(
                min_x - padding,
                min_y - padding,
                max_x - min_x + 2 * padding,
                max_y - min_y + 2 * padding
            )
            
            # 确保场景大小至少为默认值（设置一个合适的最小范围）
            min_width = 1500
            min_height = 1000
            if new_rect.width() < min_width:
                new_rect.setWidth(min_width)
                # 居中
                new_rect.setX((min_x + max_x) / 2 - min_width / 2)
            if new_rect.height() < min_height:
                new_rect.setHeight(min_height)
                # 居中
                new_rect.setY((min_y + max_y) / 2 - min_height / 2)
            
            # 设置场景矩形
            self.scene.setSceneRect(new_rect)
            
            # 更新小地图
            if self.mini_map and self.mini_map_visible:
                self.update_mini_map()
        except Exception as e:
            print(f"调整场景大小时出错: {e}")
    
    def init_mini_map(self):
        """初始化小地图"""
        try:
            from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
            from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
            from PySide6.QtCore import Qt, QRectF, QPointF, QSize
            
            # 创建小地图窗口
            self.mini_map = QFrame(self)
            self.mini_map.setFixedSize(250, 180)
            self.mini_map.setStyleSheet("""
                QFrame {
                    background-color: #2D2D2D;
                    border: 2px solid #555555;
                    border-radius: 6px;
                }
            """)
            
            # 创建布局
            layout = QVBoxLayout(self.mini_map)
            layout.setContentsMargins(5, 5, 5, 5)
            
            # 添加标题
            title_label = QLabel("小地图")
            title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
            title_label.setStyleSheet("color: #FFFFFF;")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title_label)
            
            # 创建小地图画布
            self.mini_map_canvas = QWidget()
            self.mini_map_canvas.setFixedSize(240, 150)
            layout.addWidget(self.mini_map_canvas)
            
            # 小地图拖动状态
            self.mini_map_dragging = False
            self.mini_map_last_pos = QPointF()
            
            # 连接事件
            self.mini_map_canvas.mousePressEvent = self.mini_map_mouse_press
            self.mini_map_canvas.mouseMoveEvent = self.mini_map_mouse_move
            self.mini_map_canvas.mouseReleaseEvent = self.mini_map_mouse_release
            self.mini_map_canvas.paintEvent = self.mini_map_paint
            
            # 放置在右下角
            self.mini_map.move(self.width() - 260, self.height() - 200)
            
            # 显示小地图
            self.mini_map.setVisible(self.mini_map_visible)
            
            # 连接窗口大小变化信号
            self.resizeEvent = self.on_resize
        except Exception as e:
            print(f"初始化小地图时出错: {e}")
    
    def on_resize(self, event):
        """窗口大小变化时调整小地图位置"""
        if self.mini_map:
            self.mini_map.move(self.width() - 260, self.height() - 200)
        super().resizeEvent(event)
    
    def mini_map_mouse_press(self, event):
        """小地图鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.mini_map_dragging = True
            self.mini_map_last_pos = event.pos()
    
    def mini_map_mouse_move(self, event):
        """小地图鼠标移动事件"""
        if self.mini_map_dragging:
            # 计算拖动偏移
            delta = event.pos() - self.mini_map_last_pos
            
            # 将小地图坐标转换为场景坐标
            scene_rect = self.scene.sceneRect()
            mini_map_rect = self.mini_map.rect()
            
            # 计算比例
            scale_x = scene_rect.width() / mini_map_rect.width()
            scale_y = scene_rect.height() / mini_map_rect.height()
            
            # 计算新的视图中心位置（直接将小地图坐标映射到场景坐标）
            # 这样拖动小地图上的位置，视图就会中心到该位置
            target_x = scene_rect.left() + (event.pos().x() / mini_map_rect.width()) * scene_rect.width()
            target_y = scene_rect.top() + (event.pos().y() / mini_map_rect.height()) * scene_rect.height()
            
            # 移动视图到新位置
            self.centerOn(target_x, target_y)
            
            # 更新小地图
            self.update_mini_map()
            
            # 更新鼠标位置
            self.mini_map_last_pos = event.pos()
    
    def mini_map_mouse_release(self, event):
        """小地图鼠标释放事件"""
        self.mini_map_dragging = False
    
    def mini_map_paint(self, event):
        """小地图绘制事件"""
        from PySide6.QtGui import QPainter, QPen, QBrush, QColor
        from PySide6.QtCore import Qt, QRectF
        
        painter = QPainter(self.mini_map_canvas)
        try:
            # 绘制背景
            painter.fillRect(self.mini_map_canvas.rect(), QBrush(QColor(45, 45, 45)))
            
            # 获取场景矩形
            scene_rect = self.scene.sceneRect()
            if scene_rect.isNull():
                return
            
            # 计算小地图的缩放比例（确保整个场景都能显示）
            mini_map_rect = self.mini_map_canvas.rect()
            scale = min(
                mini_map_rect.width() / scene_rect.width(),
                mini_map_rect.height() / scene_rect.height()
            )
            
            # 计算偏移，使场景在小地图中居中
            offset_x = (mini_map_rect.width() - scene_rect.width() * scale) / 2
            offset_y = (mini_map_rect.height() - scene_rect.height() * scale) / 2
            
            # 绘制场景内容（简化版，只绘制节点）
            for item in self.scene.items():
                if hasattr(item, 'title') and hasattr(item, 'ports'):
                    # 绘制节点
                    item_rect = item.boundingRect()
                    scene_item_rect = item.mapToScene(item_rect).boundingRect()
                    
                    # 转换为小地图坐标
                    mini_x = offset_x + (scene_item_rect.left() - scene_rect.left()) * scale
                    mini_y = offset_y + (scene_item_rect.top() - scene_rect.top()) * scale
                    mini_width = scene_item_rect.width() * scale
                    mini_height = scene_item_rect.height() * scale
                    
                    # 绘制节点
                    painter.setBrush(QBrush(QColor(231, 76, 60)))
                    painter.setPen(QPen(QColor(255, 255, 255), 1))
                    painter.drawRoundedRect(mini_x, mini_y, mini_width, mini_height, 4, 4)
            
            # 绘制当前视图框
            # 获取视图的四个角点，转换为场景坐标
            view_rect = self.viewport().rect()
            top_left = self.mapToScene(view_rect.topLeft())
            bottom_right = self.mapToScene(view_rect.bottomRight())
            
            # 计算视图在场景中的矩形
            scene_view_left = min(top_left.x(), bottom_right.x())
            scene_view_top = min(top_left.y(), bottom_right.y())
            scene_view_width = abs(bottom_right.x() - top_left.x())
            scene_view_height = abs(bottom_right.y() - top_left.y())
            
            # 转换为小地图坐标
            mini_view_x = offset_x + (scene_view_left - scene_rect.left()) * scale
            mini_view_y = offset_y + (scene_view_top - scene_rect.top()) * scale
            mini_view_width = scene_view_width * scale
            mini_view_height = scene_view_height * scale
            
            # 确保视图框在小地图范围内
            mini_view_x = max(0, min(mini_view_x, mini_map_rect.width() - 1))
            mini_view_y = max(0, min(mini_view_y, mini_map_rect.height() - 1))
            mini_view_width = max(10, min(mini_view_width, mini_map_rect.width() - mini_view_x))
            mini_view_height = max(10, min(mini_view_height, mini_map_rect.height() - mini_view_y))
            
            # 绘制视图框
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(241, 196, 15), 2))
            painter.drawRect(mini_view_x, mini_view_y, mini_view_width, mini_view_height)
        except Exception as e:
            print(f"绘制小地图时出错: {e}")
        finally:
            painter.end()
    
    def update_mini_map(self):
        """更新小地图"""
        if self.mini_map and self.mini_map.isVisible() and hasattr(self, 'mini_map_canvas'):
            self.mini_map_canvas.update()

    def _save_add_node_state_for_undo(self, node_id, node_type, x, y, parameters):
        """保存添加节点的撤销状态"""
        undo_data = {
            'type': 'add_node',
            'node_id': node_id,
            'node_type': node_type,
            'position': {'x': x, 'y': y},
            'parameters': parameters
        }
        self._add_to_undo_stack(undo_data)

    def _save_delete_node_state_for_undo(self, node):
        """保存删除节点的撤销状态"""
        if not node:
            return
        
        # 收集节点的连接
        connections = []
        for port in node.ports:
            for connection in port.connections:
                if connection not in connections:
                    connections.append(connection)
        
        undo_data = {
            'type': 'delete_node',
            'node_id': node.id,
            'node_type': node.__class__.__name__,
            'position': {'x': node.x(), 'y': node.y()},
            'parameters': node.variables.copy(),
            'connections': [{
                'start_port_id': id(conn.start_port),
                'end_port_id': id(conn.end_port)
            } for conn in connections]
        }
        self._add_to_undo_stack(undo_data)

    def _save_add_connection_state_for_undo(self, start_port, end_port):
        """保存添加连接的撤销状态"""
        undo_data = {
            'type': 'add_connection',
            'start_port_id': id(start_port),
            'end_port_id': id(end_port)
        }
        self._add_to_undo_stack(undo_data)

    def _save_connection_state_for_undo(self, connection):
        """保存连接的撤销状态"""
        if not connection or not connection.start_port or not connection.end_port:
            return
        
        undo_data = {
            'type': 'delete_connection',
            'start_port_id': id(connection.start_port),
            'end_port_id': id(connection.end_port)
        }
        self._add_to_undo_stack(undo_data)

    def _add_to_undo_stack(self, undo_data):
        """添加到撤销栈"""
        self.undo_stack.append(undo_data)
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)

    def undo(self):
        """执行撤销操作"""
        if not self.undo_stack:
            return
        
        self._undoing_operation = True
        try:
            undo_data = self.undo_stack.pop()
            if undo_data['type'] == 'add_node':
                # 撤销添加节点，删除节点
                if undo_data['node_id'] in self.nodes:
                    self.delete_node(undo_data['node_id'])
            elif undo_data['type'] == 'delete_node':
                # 撤销删除节点，重新添加节点
                node = self.add_node(undo_data['node_type'], QPointF(undo_data['position']['x'], undo_data['position']['y']))
                if node:
                    node.variables.update(undo_data['parameters'])
                    node.update()
            elif undo_data['type'] == 'add_connection':
                # 撤销添加连接，删除连接
                for conn in self.connections:
                    if id(conn.start_port) == undo_data['start_port_id'] and id(conn.end_port) == undo_data['end_port_id']:
                        self.remove_connection(conn)
                        break
            elif undo_data['type'] == 'delete_connection':
                # 撤销删除连接，重新添加连接
                # 这里需要根据端口ID找到对应的端口，可能比较复杂
                pass
        finally:
            self._undoing_operation = False