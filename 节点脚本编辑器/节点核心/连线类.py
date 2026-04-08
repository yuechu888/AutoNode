from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QPen, QPainterPath
from PySide6.QtCore import QPointF, QRectF

class Connection(QGraphicsItem):
    def __init__(self, start_port, end_port=None):
        super().__init__()
        # 选中状态
        self.is_selected = False
        # 检查端口类型和变量类型是否匹配
        if end_port:
            # 简化连接逻辑，只要是从output到input就允许连接
            if start_port.port_type == "output" and end_port.port_type == "input":
                # 允许任何类型的连接
                self.start_port = start_port
                self.end_port = end_port
                self.setZValue(2)  # 连线在节点上方
                
                # 初始化端口的connections属性
                if not hasattr(start_port, 'connections'):
                    start_port.connections = []
                
                if not hasattr(end_port, 'connections'):
                    end_port.connections = []
                
                # 移除同一输入端口的旧连接（实现单一连接线）
                try:
                    for old_connection in list(end_port.connections):
                        # 从画布视图的connections列表中移除旧连接
                        if old_connection.scene():
                            for view in old_connection.scene().views():
                                if hasattr(view, 'connections') and old_connection in view.connections:
                                    view.connections.remove(old_connection)
                        old_connection.delete_connection()
                except Exception as e:
                    print(f"删除输入端口旧连接时出错: {e}")
                    # 即使出错，也要确保connections列表被清理
                    try:
                        end_port.connections.clear()
                    except Exception:
                        pass
                
                # 移除同一输出端口的旧连接（实现重新拉线功能）
                try:
                    for old_connection in list(start_port.connections):
                        # 从画布视图的connections列表中移除旧连接
                        if old_connection.scene():
                            for view in old_connection.scene().views():
                                if hasattr(view, 'connections') and old_connection in view.connections:
                                    view.connections.remove(old_connection)
                        old_connection.delete_connection()
                except Exception as e:
                    print(f"删除输出端口旧连接时出错: {e}")
                    # 即使出错，也要确保connections列表被清理
                    try:
                        start_port.connections.clear()
                    except Exception:
                        pass
                
                # 确保新连接被添加到端口的connections列表中，使用NodePort的add_connection方法
                try:
                    start_port.add_connection(self)
                    end_port.add_connection(self)
                except Exception as e:
                    print(f"添加新连接到端口时出错: {e}")
                
                # 设置节点之间的依赖关系
                # 所有连接都设置依赖关系，不再区分执行流连接和数据连接
                try:
                    start_node = start_port.parentItem()
                    end_node = end_port.parentItem()
                    if start_node and end_node:
                        end_node.add_dependency(start_node)
                except Exception as e:
                    print(f"设置依赖关系时出错: {e}")
            else:
                # 端口类型不匹配，不创建连接
                self.start_port = None
                self.end_port = None
        else:
            # 没有end_port，暂时创建连接（用于拖拽预览）
            self.start_port = start_port
            self.end_port = None
            self.setZValue(-1)  # 连线在节点下方
    
    def boundingRect(self):
        if not self.end_port and not hasattr(self, 'temp_end_pos'):
            # 还没有开始拖拽的连线
            return QRectF(0, 0, 1, 1)
        
        # 计算连线的实际起点和终点，使用端口中心位置
        if self.start_port.port_type == "output":
            # 输出端口：使用端口中心作为起点
            start_pos = self.start_port.mapToScene(QPointF(8, 0))
        else:
            # 输入端口：使用端口中心作为起点
            start_pos = self.start_port.mapToScene(QPointF(-8, 0))
        
        if self.end_port:
            if self.end_port.port_type == "input":
                # 输入端口：使用端口中心作为终点
                end_pos = self.end_port.mapToScene(QPointF(-8, 0))
            else:
                # 输出端口：使用端口中心作为终点
                end_pos = self.end_port.mapToScene(QPointF(8, 0))
        else:
            # 正在拖拽的连线，使用临时位置
            end_pos = self.temp_end_pos
        
        min_x = min(start_pos.x(), end_pos.x())
        max_x = max(start_pos.x(), end_pos.x())
        min_y = min(start_pos.y(), end_pos.y())
        max_y = max(start_pos.y(), end_pos.y())
        
        # 缩小点击判断范围，只在线条本身附近，避免影响端口点击
        # 向外扩展1像素，确保线条本身可点击但不影响端口
        return QRectF(min_x - 1, min_y - 1, max_x - min_x + 2, max_y - min_y + 2)
    
    def paint(self, painter, option, widget):
        # 只有当连接成功（有end_port）时才绘制连线
        if not self.end_port or not self.start_port:
            return
        
        # 检查端口是否仍然在场景中
        if not self.start_port.scene() or not self.end_port.scene():
            return
        
        # 根据连接类型设置不同的颜色
        # 检查是否是完成连接（执行流端口）
        is_completion_connection = False
        if self.start_port.port_type == "output" and self.end_port.port_type == "input":
            # 检查端口位置是否是执行流端口的位置（y=60）
            if abs(self.start_port.pos().y() - 60) < 5 and abs(self.end_port.pos().y() - 60) < 5:
                is_completion_connection = True
        
        # 设置连线颜色
        if self.is_selected:
            # 选中状态使用黄色
            pen = QPen("#F1C40F")
            pen.setWidth(3)  # 选中时线宽增加
        elif is_completion_connection:
            # 完成连接使用蓝色
            pen = QPen("#3498DB")
        else:
            # 其他连接使用浅蓝色，更清晰可见
            pen = QPen("#87CEEB")
        
        pen.setWidth(2)
        if self.is_selected:
            pen.setWidth(3)  # 选中时线宽增加
        painter.setPen(pen)
        
        try:
            # 根据端口类型计算不同的起点和终点位置
            if self.start_port.port_type == "output":
                # 输出端口：使用端口中心作为起点，确保在节点内部
                start_pos = self.start_port.mapToScene(QPointF(8, 0))
            else:
                # 输入端口：使用端口中心作为起点，确保在节点内部
                start_pos = self.start_port.mapToScene(QPointF(-8, 0))
            
            if self.end_port.port_type == "input":
                # 输入端口：使用端口中心作为终点，确保在节点内部
                end_pos = self.end_port.mapToScene(QPointF(-8, 0))
            else:
                # 输出端口：使用端口中心作为终点，确保在节点内部
                end_pos = self.end_port.mapToScene(QPointF(8, 0))
            
            # 绘制贝塞尔曲线
            path = QPainterPath(start_pos)
            # 计算控制点
            control_point1 = QPointF(start_pos.x() + 50, start_pos.y())
            control_point2 = QPointF(end_pos.x() - 50, end_pos.y())
            path.cubicTo(control_point1, control_point2, end_pos)
            painter.drawPath(path)
        except Exception:
            # 忽略绘制错误，避免程序崩溃
            pass
    
    def update_position(self):
        # 先准备几何变化，确保边界矩形会重新计算
        self.prepareGeometryChange()
        # 然后更新重绘
        self.update()
        # 触发场景更新，消除残影（参考开源）
        if self.scene():
            self.scene().update()
    
    def set_end_port(self, end_port):
        """设置结束端口"""
        if not end_port:
            return
        
        # 简化连接逻辑，只要是从output到input就允许连接
        if self.start_port.port_type == "output" and end_port.port_type == "input":
            # 允许任何类型的连接
            self.end_port = end_port
            if not hasattr(end_port, 'connections'):
                end_port.connections = []
            
            # 移除同一输入端口的旧连接（实现单一连接线）
            try:
                for old_connection in list(end_port.connections):
                    # 从画布视图的connections列表中移除旧连接
                    if old_connection.scene():
                        for view in old_connection.scene().views():
                            if hasattr(view, 'connections') and old_connection in view.connections:
                                view.connections.remove(old_connection)
                    old_connection.delete_connection()
            except Exception as e:
                print(f"删除输入端口旧连接时出错: {e}")
                # 即使出错，也要确保connections列表被清理
                try:
                    end_port.connections.clear()
                except Exception:
                    pass
            
            # 移除同一输出端口的旧连接（实现重新拉线功能）
            try:
                for old_connection in list(self.start_port.connections):
                    # 从画布视图的connections列表中移除旧连接
                    if old_connection.scene():
                        for view in old_connection.scene().views():
                            if hasattr(view, 'connections') and old_connection in view.connections:
                                view.connections.remove(old_connection)
                    old_connection.delete_connection()
            except Exception as e:
                print(f"删除输出端口旧连接时出错: {e}")
                # 即使出错，也要确保connections列表被清理
                try:
                    self.start_port.connections.clear()
                except Exception:
                    pass
            
            # 确保新连接被添加到端口的connections列表中，使用NodePort的add_connection方法
            try:
                end_port.add_connection(self)
                self.start_port.add_connection(self)
            except Exception as e:
                print(f"添加新连接到端口时出错: {e}")
            
            self.update()
            
            # 设置节点之间的依赖关系
            # 所有连接都设置依赖关系，不再区分执行流连接和数据连接
            try:
                start_node = self.start_port.parentItem()
                end_node = end_port.parentItem()
                if start_node and end_node:
                    end_node.add_dependency(start_node)
            except Exception as e:
                print(f"设置依赖关系时出错: {e}")
        else:
            # 端口类型不匹配，不设置结束端口
            self.end_port = None
    
    def set_temp_end_pos(self, pos):
        self.temp_end_pos = pos
        # 手动更新边界矩形和重绘
        self.prepareGeometryChange()
        self.update()
    
    def flags(self):
        """设置项目标志"""
        return super().flags() | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable | QGraphicsItem.ItemIsContextMenuEnabled
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        # 取消其他连线的选中状态
        if self.scene():
            for item in self.scene().items():
                if isinstance(item, Connection) and item != self:
                    item.is_selected = False
                    item.update()
        
        # 标记当前连线为选中
        self.is_selected = True
        self.update()
        
        # 调用父类方法
        super().mousePressEvent(event)
    
    def keyPressEvent(self, event):
        """键盘事件"""
        from PySide6.QtCore import Qt
        if event.key() == Qt.Key_Delete:
            # 按Delete键删除连线
            self.delete_connection()
        
        # 调用父类方法
        super().keyPressEvent(event)
    
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        from PySide6.QtWidgets import QMenu
        menu = QMenu()
        delete_action = menu.addAction("删除连线")
        action = menu.exec_(event.screenPos())
        if action == delete_action:
            self.delete_connection()
    
    def delete_connection(self):
        """删除连线"""
        try:
            # 移除节点依赖关系
            # 所有连接都移除依赖关系，不再区分执行流连接和数据连接
            if self.start_port and self.end_port:
                start_node = self.start_port.parentItem()
                end_node = self.end_port.parentItem()
                if start_node and end_node:
                    end_node.remove_dependency(start_node)
            
            # 从端口的connections列表中移除，使用NodePort的remove_connection方法
            if self.start_port:
                self.start_port.remove_connection(self)
            
            if self.end_port:
                self.end_port.remove_connection(self)
            
            # 从场景中移除
            if self.scene():
                self.scene().removeItem(self)
        except Exception as e:
            print(f"删除连线时出错: {e}")
            # 即使出错，也要确保从端口的connections列表中移除
            try:
                if self.start_port:
                    self.start_port.remove_connection(self)
                
                if self.end_port:
                    self.end_port.remove_connection(self)
            except Exception as e2:
                print(f"清理端口连接时出错: {e2}")
    
    def itemChange(self, change, value):
        """处理项目变化事件"""
        if change == QGraphicsItem.ItemSelectedChange:
            # 同步QGraphicsItem的选中状态与自定义is_selected属性
            self.is_selected = value
        return super().itemChange(change, value)