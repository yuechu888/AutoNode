from PySide6.QtWidgets import QGraphicsObject, QGraphicsTextItem, QGraphicsProxyWidget, QApplication, QMenu, QMessageBox, QToolTip, QStyleOptionGraphicsItem
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QPolygonF, QPainter, QPainterPath, QAction
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QObject, QTimer

# 信号管理器类
class SignalManager(QObject):
    # 定义节点选中信号，传递节点变量字典
    node_selected_signal = Signal(dict)

# 创建全局信号管理器实例
signal_manager = SignalManager()

# 定义端口类型
PORT_TYPE_INPUT = 'input'
PORT_TYPE_OUTPUT = 'output'

class NodePort(QGraphicsObject):
    def __init__(self, parent=None, port_type="input", data_type="str", label="", max_connections=1):
        super().__init__(parent)
        self.port_type = port_type  # input 或 output
        self.data_type = data_type  # 数据类型，如 int、float、str 等
        self.label = label  # 标签名，显示在端口旁边的文本
        self.radius = 8
        self.hovered = False  # 鼠标悬停状态
        self.max_connections = max_connections  # 最大连接数，-1表示无限制
        self.connections = []  # 存储连接
        # 设置端口颜色
        if port_type == "input":
            self.color = QColor("#99FF99")  # 左边输入端口使用绿色
        else:
            self.color = QColor("#FF9999")  # 右边输出端口使用红色
        # 确保端口可以接收鼠标事件
        self.setAcceptHoverEvents(True)
    
    def boundingRect(self):
        # 大幅增加点击判断范围，确保端口容易被点击
        if self.port_type == "output":
            # 输出端口：向右的箭头，点击区域向右扩展
            return QRectF(-15, -25, 30, 50)
        else:
            # 输入端口：向左的箭头，点击区域向左扩展
            return QRectF(-30, -25, 30, 50)
    
    def paint(self, painter, option, widget):
        # 检查painter是否有效
        if not painter:
            return
        
        try:
            # 检查端口是否有连接
            has_connection = hasattr(self, 'connections') and len(self.connections) > 0
            
            # 根据连接状态设置画笔和画刷
            if has_connection:
                # 有连接时使用实心
                painter.setBrush(QBrush(self.color))
                painter.setPen(QPen(Qt.white, 2))
            else:
                # 无连接时使用空心
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(self.color, 2))
            
            # 根据悬停状态调整端口大小
            scale = 1.5 if self.hovered else 1.0
            
            # 保存当前画家状态
            painter.save()
            
            # 移动到端口中心，进行缩放，然后移动回来
            if self.port_type == "output":
                # 输出端口：以箭头底部为中心缩放
                painter.translate(8, 0)
                painter.scale(scale, scale)
                painter.translate(-8, 0)
            else:
                # 输入端口：以箭头底部为中心缩放
                painter.translate(-8, 0)
                painter.scale(scale, scale)
                painter.translate(8, 0)
            
            # 绘制三角形带正方形尾部的箭头形状
            if self.port_type == "output":
                # 输出端口：向右的箭头
                points = [
                    QPointF(8, -6),    # 箭头顶部
                    QPointF(16, 0),    # 箭头尖端
                    QPointF(8, 6),     # 箭头底部
                    QPointF(0, 6),     # 正方形底部
                    QPointF(0, -6),    # 正方形顶部
                    QPointF(8, -6)     # 回到起点
                ]
            else:
                # 输入端口：向左的箭头
                points = [
                    QPointF(-8, -6),   # 箭头顶部
                    QPointF(-16, 0),   # 箭头尖端
                    QPointF(-8, 6),    # 箭头底部
                    QPointF(0, 6),     # 正方形底部
                    QPointF(0, -6),    # 正方形顶部
                    QPointF(-8, -6)    # 回到起点
                ]
            painter.drawPolygon(QPolygonF(points))
            
            # 恢复画家状态
            painter.restore()
        except Exception:
            # 忽略绘制错误，确保程序不会崩溃
            pass
    
    def hoverEnterEvent(self, event):
        """鼠标进入事件"""
        self.hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """鼠标离开事件"""
        self.hovered = False
        self.update()
        super().hoverLeaveEvent(event)
    
    def add_connection(self, connection):
        """添加连接"""
        if connection not in self.connections:
            self.connections.append(connection)
            self.update()
    
    def remove_connection(self, connection):
        """移除连接"""
        try:
            self.connections.remove(connection)
            self.update()
        except ValueError:
            pass

class BaseNode(QGraphicsObject):
    # 类变量，用于生成唯一ID
    _next_id = 1
    
    # 信号
    delete_requested = Signal(int)
    copy_requested = Signal(int, dict)
    edit_settings_requested = Signal(int)
    card_clicked = Signal(int)
    properties_changed = Signal(object)  # 当节点属性变化时发出信号
    
    def __init__(self, title, color=None, width=None, height=None, x=0, y=0):
        super().__init__()
        # 分配唯一ID
        self.id = BaseNode._next_id
        BaseNode._next_id += 1
        
        # 确保标题有值
        self.title = title or 'Node'
        
        # 获取节点类型
        node_type = self.__class__.__name__
        
        # 在标题后面添加ID信息，使用节点类型的2-3字母英文简写作为前缀
        # 提取类名中的大写字母作为简写
        node_abbr = ''.join([c for c in node_type if c.isupper()])
        if not node_abbr:
            # 如果没有大写字母，使用类名的前3个字符
            node_abbr = node_type[:3].lower()
        else:
            # 限制简写长度为2-3个字母
            node_abbr = node_abbr[:3].lower()
        self.title = f"{self.title} ({node_abbr}_id:{self.id})"
        
        # 使用传入的值或默认值
        self.color = color if color else QColor("#3498DB")  # 默认颜色
        # 确保宽度和高度有值
        self.width = max(100, width if width else 200)  # 参考图片中的宽度
        self.height = max(60, height if height else 60)  # 更矮的默认高度，参考图片中的高度
        
        # 使用默认基点位置，除非用户明确指定了位置
        if x == 0 and y == 0:
            x = 100  # 默认 x 位置
            y = 100  # 默认 y 位置
        
        # 初始化必要的属性
        self.ports = []
        
        # 选中状态
        self.is_selected = False
        
        # 执行状态：未执行、执行中、已完成、错误
        self.execution_status = "idle"  # idle, running, completed, error
        # 错误信息
        self.error_message = ""
        
        # 依赖管理
        self.dependencies = []  # 依赖的节点
        self.dependents = []  # 依赖此节点的节点
        
        # 内置变量容器
        self.variables = {
            'id': self.id,
            'title': self.title,
            'type': node_type,
            'position': {'x': x, 'y': y},
            'inputs': [],  # 输入变量
            'outputs': []  # 输出变量
        }
        

        
        # 设置初始位置
        self.setPos(x, y)
        
        # 确保节点可见
        self.setVisible(True)
        # 设置zValue，确保节点显示在连线下方，外部节点显示在正确层级
        self.setZValue(1)
        
        # 使用setFlag设置标志
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsFocusable)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        # 样式设置
        self.border_radius = 10
        self.card_color = QColor(30, 30, 40)  # 暗黑色背景
        self.title_color = QColor(200, 200, 220)  # 浅色文字
        self.text_padding = 8
        self.title_font = QFont("Microsoft YaHei", 12, QFont.Bold)
        self.param_font = QFont("Microsoft YaHei", 10)
        self.shadow_color = QColor(0, 0, 0, 50)  # 阴影颜色
        self.shadow_offset = QPointF(3, 3)  # 阴影偏移
        self.shadow_blur = 8  # 阴影模糊半径
        
        # 状态颜色
        self.state_colors = {
            'idle': self.card_color,
            'running': QColor(40, 60, 80),  # 深蓝色
            'completed': QColor(30, 60, 40),  # 深绿色
            'error': QColor(60, 30, 30)  # 深红色
        }
        self.state_border_pens = {
            'idle': QPen(Qt.PenStyle.NoPen),
            'running': QPen(QColor(52, 152, 219), 2),  # 蓝色边框
            'completed': QPen(QColor(39, 174, 96), 2),  # 绿色边框
            'error': QPen(QColor(192, 57, 43), 2)  # 红色边框
        }
        
        # 闪烁效果
        self._is_flashing = False
        self.flash_toggle_timer = QTimer(self)
        self.flash_toggle_timer.timeout.connect(self._toggle_flash_border)
        self.flash_interval_ms = 300
        self.flash_border_pen = QPen(QColor(0, 255, 255), 3)  # 改为青色
        self._flash_border_on = False
        self._current_border_pen = self.state_border_pens.get(self.execution_status, QPen(Qt.PenStyle.NoPen))
        self._original_border_pen_before_flash = self._current_border_pen
        
        # 悬停状态
        self.hovered_port_side = None
        self.hovered_port_type = None
        
        # 自定义名称
        self.custom_name = None
        
        # 工具提示缓存
        self._cached_tooltip = ""
        self._tooltip_needs_update = True
    
    def boundingRect(self):
        # 确保宽度和高度不为0
        width = max(100, getattr(self, 'width', 200))
        height = max(60, getattr(self, 'height', 60))  # 使用实际的节点高度
        return QRectF(0, 0, width, height)
    
    def shape(self):
        """定义精确的形状用于碰撞检测和绘制"""
        path = QPainterPath()
        path.addRoundedRect(self.boundingRect(), self.border_radius, self.border_radius)
        return path
    
    def paint(self, painter, option, widget):
        # 检查painter是否有效
        if not painter:
            return
        
        try:
            # 确保宽度和高度有值
            if not hasattr(self, 'width') or self.width <= 0:
                self.width = 200
            if not hasattr(self, 'height') or self.height <= 0:
                self.height = 160
            
            # 确保节点可见
            if not self.isVisible():
                self.setVisible(True)
            
            # 确保zValue合理
            parent_node = self.parentItem()
            if parent_node:
                self.setZValue(parent_node.zValue() + 1)
            else:
                self.setZValue(1)
            
            # 检查选中状态
            is_selected = getattr(self, 'is_selected', False)
            
            # 绘制节点主体（圆角矩形）
            rect = self.boundingRect()
            path = QPainterPath()
            path.addRoundedRect(rect, self.border_radius, self.border_radius)
            
            # 绘制阴影
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self.shadow_color))
            shadow_rect = QRectF(
                rect.x() + self.shadow_offset.x(),
                rect.y() + self.shadow_offset.y(),
                rect.width(),
                rect.height()
            )
            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(shadow_rect, self.border_radius, self.border_radius)
            painter.fillPath(shadow_path, QBrush(self.shadow_color))
            
            # 绘制背景 - 添加微妙的渐变
            painter.setPen(Qt.PenStyle.NoPen)
            bg_color = self.state_colors.get(self.execution_status, self.card_color)
            # 创建线性渐变
            from PySide6.QtGui import QLinearGradient
            gradient = QLinearGradient(0, 0, 0, self.height)
            gradient.setColorAt(0, bg_color.lighter(105))
            gradient.setColorAt(1, bg_color)
            painter.fillPath(path, QBrush(gradient))
            
            # 绘制边框 - 参考样式的边框
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if is_selected:
                # 选中状态下使用更醒目的边框
                painter.setPen(QPen(QColor(100, 149, 237), 2))
            else:
                # 使用当前的边框笔，支持闪烁效果
                painter.setPen(self._current_border_pen)
            painter.drawPath(path)
            
            # 绘制标题文字（直接显示在节点主体上）
            painter.setPen(QPen(self.title_color))
            painter.setFont(self.title_font)
            title = getattr(self, 'title', 'Node')
            # 水平居中，垂直居中，与端口在同一水平线上
            title_rect = QRectF(10, 0, self.width - 20, self.height)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, title)
            
            # 绘制错误信息（如果有）
            error_message = getattr(self, 'error_message', '')
            if self.execution_status == "error" and error_message:
                painter.setPen(QPen(QColor("#E74C3C")))
                painter.setFont(QFont("Microsoft YaHei", 8))  # 减小字体大小以适应矮节点
                # 限制错误信息长度，避免显示过长
                error_text = error_message[:20] + ("..." if len(error_message) > 20 else "")
                # 绘制在节点底部
                painter.drawText(10, self.height - 5, error_text)
            
            # 绘制变量信息
            painter.setFont(self.param_font)
            
            # 绘制输出变量（在端口左侧）
            try:
                # 只为循环节点的端口显示标签
                output_ports = []
                if hasattr(self, 'title') and '循环' in self.title:
                    output_ports = [port for port in getattr(self, 'ports', []) if port.port_type == 'output']
                else:
                    output_ports = [port for port in getattr(self, 'ports', []) if port.port_type == 'output' and port.data_type not in ['exec', '运行', '执行', '完成']]
                
                for port in output_ports:
                    # 确保端口可见
                    if not port.isVisible():
                        port.setVisible(True)
                    # 确保端口zValue高于节点
                    if port.zValue() <= self.zValue():
                        port.setZValue(self.zValue() + 1)
                    # 使用端口的 label 作为标签
                    var_text = port.label
                    # 计算文本宽度
                    text_width = painter.fontMetrics().boundingRect(var_text).width() + 10
                    # 标签位置：在端口左侧
                    label_x = port.x() - text_width - 10
                    label_y = port.y() - 10
                    # 确保标签在节点内部
                    if label_x > 20:
                        # 为输出变量添加更美观的底色，适应暗黑色主题
                                # 使用与节点标题栏匹配的颜色，添加半透明效果
                                painter.setBrush(QBrush(QColor(52, 152, 219, 100)))
                                painter.setPen(QPen(QColor(52, 152, 219, 100)))
                                painter.drawRoundedRect(label_x, label_y, text_width, 20, 6, 6)
                                painter.setPen(QPen(Qt.white))
                                painter.drawText(label_x + 6, label_y + 14, var_text)
            except:
                pass
        except Exception as e:
            # 忽略绘制错误，确保节点不会因为绘制问题而消失
            pass
    
    def mousePressEvent(self, event):
        try:
            
            # 检查是否点击了子项目（如端口）
            child_item = self.childAt(event.pos())
            if child_item:
                # 如果点击了子项目，让子项目处理事件
                # 检查子项目是否是节点（有title和ports属性）
                if hasattr(child_item, 'title') and hasattr(child_item, 'ports'):
                    # 是内部节点，将事件转换为子节点坐标系后传递
                    child_pos = child_item.mapFromParent(event.pos())
                    # 创建一个新的事件，使用子节点坐标系
                    from PySide6.QtWidgets import QGraphicsSceneMouseEvent
                    child_event = QGraphicsSceneMouseEvent(event.type())
                    child_event.setScenePos(event.scenePos())
                    child_event.setScreenPos(event.screenPos())
                    child_event.setButton(event.button())
                    child_event.setButtons(event.buttons())
                    child_event.setModifiers(event.modifiers())
                    # 调用子节点的鼠标按下事件
                    child_item.mousePressEvent(child_event)
                    # 阻止事件继续传播
                    return
                # 是端口或其他子项目，让它处理事件
                child_item.mousePressEvent(event)
                return
            
            # 取消其他节点的选中状态
            if self.scene():
                for item in self.scene().items():
                    if hasattr(item, 'is_selected') and item != self:
                        item.is_selected = False
                        item.setSelected(False)
                        item.update()
            
            # 标记当前节点为选中
            self.is_selected = True
            self.setSelected(True)
            self.update()
            
            # 确保当前节点可见
            if not self.isVisible():
                self.setVisible(True)
            if self.zValue() < 1:
                self.setZValue(1)
            
            # 更新内置变量
            self.update_variables()
            
            # 发射节点选中信号
            signal_manager.node_selected_signal.emit(self.variables)
            
            # 发射卡片点击信号
            self.card_clicked.emit(self.id)
            
            # 存储鼠标按下时的场景位置
            self.last_mouse_scene_pos = event.scenePos()
            # 存储鼠标按下时的节点位置
            self.old_pos = self.pos()
            
            # 调用父类方法
            super().mousePressEvent(event)
            
            # 触发场景重绘
            if self.scene():
                self.scene().update()
        except Exception as e:
            # 忽略事件处理错误，确保节点不会因为事件处理问题而消失
            pass
    
    def mouseMoveEvent(self, event):
        try:
            # 确保节点可见
            if not self.isVisible():
                self.setVisible(True)
            # 确保节点zValue高于父节点，确保显示在上方
            parent_node = self.parentItem()
            if parent_node:
                self.setZValue(parent_node.zValue() + 1)
            else:
                self.setZValue(1)
            
            # 检查是否有父节点（循环体）
            if parent_node and hasattr(parent_node, 'title') and parent_node.title == "循环体":
                # 确保父节点可见
                if not parent_node.isVisible():
                    parent_node.setVisible(True)
                # 确保父节点zValue合理
                if parent_node.zValue() < 1:
                    parent_node.setZValue(1)
                
                # 使用场景坐标计算位移，避免瞬移
                if hasattr(self, 'last_mouse_scene_pos'):
                    # 计算鼠标在场景中的相对位移
                    scene_delta = event.scenePos() - self.last_mouse_scene_pos
                    
                    # 获取当前节点在场景中的位置
                    current_scene_pos = self.scenePos()
                    # 计算新的场景位置
                    new_scene_pos = current_scene_pos + scene_delta
                    
                    # 检查节点是否被拖出循环体
                    parent_scene_rect = parent_node.sceneBoundingRect()
                    node_scene_rect = QRectF(new_scene_pos, QPointF(new_scene_pos.x() + self.width, new_scene_pos.y() + self.height))
                    
                    # 如果节点完全在循环体外，将其移出循环体
                    if not parent_scene_rect.intersects(node_scene_rect):
                        # 保存场景位置
                        scene_pos = self.scenePos()
                        # 从循环体的内部节点列表中移除
                        if hasattr(parent_node, 'remove_internal_node'):
                            # 先保存场景引用，因为remove_internal_node会从场景中移除节点
                            scene = self.scene()
                            parent_node.remove_internal_node(self)
                        # 设置父节点为None
                        self.setParentItem(None)
                        # 确保节点可见
                        self.setVisible(True)
                        # 设置zValue
                        self.setZValue(1)
                        # 移动到新位置
                        self.setPos(new_scene_pos)
                        # 将节点重新添加到场景中
                        if scene:
                            scene.addItem(self)
                        # 更新last_mouse_scene_pos
                        self.last_mouse_scene_pos = event.scenePos()
                        # 触发重绘
                        self.update()
                        # 触发场景重绘
                        if self.scene():
                            self.scene().update()
                        return
                    
                    # 转换为父坐标系中的位置
                    new_parent_pos = parent_node.mapFromScene(new_scene_pos)
                    
                    # 限制位置范围，确保节点在循环体内部
                    padding = 20  # 内边距
                    max_x = parent_node.width - self.width - padding
                    max_y = parent_node.height - self.height - padding
                    min_x = padding
                    min_y = padding
                    
                    # 确保节点在循环体内部
                    new_parent_pos.setX(max(min(new_parent_pos.x(), max_x), min_x))
                    new_parent_pos.setY(max(min(new_parent_pos.y(), max_y), min_y))
                    
                    # 设置新位置
                    self.setPos(new_parent_pos)
                    # 更新last_mouse_scene_pos
                    self.last_mouse_scene_pos = event.scenePos()
                    
                    # 调整循环体大小
                    if hasattr(parent_node, 'adjust_size'):
                        parent_node.adjust_size()
                    
                    # 触发父节点重绘
                    parent_node.update()
            else:
                # 没有父节点，正常移动
                super().mouseMoveEvent(event)
                # 更新last_mouse_scene_pos
                if hasattr(self, 'last_mouse_scene_pos'):
                    self.last_mouse_scene_pos = event.scenePos()
            
            # 移动节点时，更新所有连线的位置
            for port in self.ports:
                for connection in port.connections:
                    # 只调用update，不调用scene.update()，避免触发事件循环
                    try:
                        connection.update()
                    except Exception:
                        pass
            # 更新子组件的位置
            for child in self.childItems():
                if isinstance(child, QGraphicsProxyWidget):
                    # 对于QGraphicsProxyWidget，位置会自动更新
                    pass
            
            # 确保节点仍然可见
            if not self.isVisible():
                self.setVisible(True)
            # 确保节点zValue合理
            if parent_node:
                self.setZValue(parent_node.zValue() + 1)
            else:
                self.setZValue(1)
            
            # 触发重绘
            self.update()
            # 触发场景重绘
            if self.scene():
                self.scene().update()
                # 尝试调用视图的adjust_scene_size方法来调整场景大小
                try:
                    # 遍历所有视图，找到NodeGraphicsView实例
                    for view in self.scene().views():
                        if hasattr(view, 'adjust_scene_size'):
                            view.adjust_scene_size()
                            break
                except Exception:
                    # 忽略错误，确保程序不会崩溃
                    pass
        except Exception as e:
            # 忽略事件处理错误，确保节点不会因为事件处理问题而消失
            pass
    
    def mouseReleaseEvent(self, event):
        try:
            # 确保节点可见
            if not self.isVisible():
                self.setVisible(True)
            if self.zValue() < 1:
                self.setZValue(1)
            
            # 检查是否有父节点（循环体）
            parent_node = self.parentItem()
            if parent_node and hasattr(parent_node, 'title') and parent_node.title == "循环体" and hasattr(parent_node, 'adjust_size'):
                # 调整循环体大小
                parent_node.adjust_size()
            
            super().mouseReleaseEvent(event)
            # 释放鼠标时更新变量
            self.update_variables()
            
            # 确保节点可见
            if not self.isVisible():
                self.setVisible(True)
            if self.zValue() < 1:
                self.setZValue(1)
            
            # 触发重绘
            self.update()
            # 触发场景重绘
            if self.scene():
                self.scene().update()
                # 尝试调用视图的adjust_scene_size方法来调整场景大小
                try:
                    # 遍历所有视图，找到NodeGraphicsView实例
                    for view in self.scene().views():
                        if hasattr(view, 'adjust_scene_size'):
                            view.adjust_scene_size()
                            break
                except Exception:
                    # 忽略错误，确保程序不会崩溃
                    pass
        except Exception as e:
            # 忽略事件处理错误，确保节点不会因为事件处理问题而消失
            pass
    
    def itemChange(self, change, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemSelectedChange:
            self.is_selected = value
            # 确保节点可见
            self.setVisible(True)
            # 确保zValue合理
            parent_node = self.parentItem()
            if parent_node:
                self.setZValue(parent_node.zValue() + 1)
            else:
                self.setZValue(1)
            # 触发重绘，确保选中状态变化能及时显示
            self.update()
        
        # 调用父类方法，让位置改变生效
        result = super().itemChange(change, value)
        
        # 在位置改变完成后更新连线
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionChange:
            # 确保节点可见
            self.setVisible(True)
            # 确保zValue合理
            parent_node = self.parentItem()
            if parent_node:
                self.setZValue(parent_node.zValue() + 1)
            else:
                self.setZValue(1)
            for port in self.ports:
                for connection in port.connections:
                    connection.update()
            # 触发重绘，确保位置变化能及时显示
            self.update()
        
        return result
    
    def update_variables(self):
        """更新内置变量"""
        # 更新位置信息
        pos = self.pos()
        self.variables['position'] = {'x': pos.x(), 'y': pos.y()}
        
        # 更新其他通用信息
        self.variables['title'] = self.title
        self.variables['type'] = self.__class__.__name__
        
        # 发出属性变化信号
        self.properties_changed.emit(self)
    
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        # 检查工作流是否正在运行
        is_running = self._is_workflow_running()
        
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
        
        # 只添加删除选项
        delete_action = QAction("删除卡片", menu)
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.id))
        delete_action.setEnabled(not is_running)
        if is_running:
            delete_action.setToolTip("工作流运行期间无法删除卡片")
        menu.addAction(delete_action)
        
        # 显示菜单
        selected_action = menu.exec(event.screenPos())
        
        # 处理选中的动作
        if selected_action and selected_action.text() == "删除卡片":
            self.delete_requested.emit(self.id)
    
    def copy_card(self):
        """复制卡片"""
        # 检查是否正在运行，如果是则阻止复制
        if self._is_workflow_running():
            QMessageBox.warning(
                None, 
                "操作被禁止", 
                "工作流正在执行中，暂时无法进行复制卡片操作。\n\n请等待任务执行完成或停止任务后再试。"
            )
            return
            
        # 发射复制请求信号
        self.copy_requested.emit(self.id, self.variables.copy())
    
    def open_parameter_dialog(self):
        """打开参数设置对话框"""
        # 检查是否正在运行，如果是则阻止打开参数设置
        if self._is_workflow_running():
            QMessageBox.warning(
                None,
                "操作被禁止",
                "工作流正在执行中，暂时无法进行参数设置操作。\n\n请等待任务执行完成或停止任务后再试。"
            )
            return
        
        # 发射编辑设置请求信号
        self.edit_settings_requested.emit(self.id)
    
    def _is_workflow_running(self):
        """检查工作流是否正在运行"""
        try:
            # 从QApplication查找
            app = QApplication.instance()
            if app:
                for widget in app.allWidgets():
                    if (hasattr(widget, 'executor') and hasattr(widget, 'executor_thread') and
                        widget.executor is not None and widget.executor_thread is not None and
                        widget.executor_thread.isRunning()):
                        return True
        except Exception as e:
            print(f"检查任务运行状态时发生错误: {e}")
            
        return False
    
    def add_dependency(self, node):
        """添加依赖节点"""
        if node not in self.dependencies:
            self.dependencies.append(node)
            if self not in node.dependents:
                node.dependents.append(self)
    
    def remove_dependency(self, node):
        """移除依赖节点"""
        if node in self.dependencies:
            self.dependencies.remove(node)
            if self in node.dependents:
                node.dependents.remove(self)
    
    def can_execute(self):
        """检查是否可以执行"""
        # 使用拓扑排序执行模式，总是返回True
        # 执行顺序由main.py中的execute_all方法通过拓扑排序确定
        return True
    
    def reset_execution_status(self):
        """重置执行状态"""
        self.execution_status = "idle"
        self.error_message = ""
    
    def execute(self, context=None, all_nodes=None):
        """执行节点逻辑"""
        # 更新执行状态
        self.execution_status = "running"
        
        try:
            # 如果没有上下文，创建一个新的
            if context is None:
                from 节点核心.上下文 import Context
                context = Context()
            
            # 添加到执行路径
            context.add_to_execution_path(self.id)
            
            # 解析变量引用，获取解析后的值
            resolved_inputs = self._resolve_variables(context, all_nodes)
            
            # 执行节点具体逻辑，传递解析后的值
            result = self._execute(context, resolved_inputs, all_nodes)
            
            # 存储节点输出
            context.set_node_output(self.id, result)
            
            # 移除完成方法调用，根据用户需求
        except Exception as e:
            error_msg = f"{self.title} 执行错误: {str(e)}"
            # 输出到终端，方便开发调试
            print(f"开发调试: {error_msg}")
            # 输出到UI日志，方便用户查看
            from 工具类.日志管理器 import log_manager
            log_manager.ui_error(error_msg)
            self.execution_status = "error"
            self.error_message = error_msg
            if context:
                context.add_error(error_msg)
        finally:
            # 执行完成后更新状态
            if self.execution_status != "error":
                # 执行完成后恢复到idle状态，显示原始颜色
                self.execution_status = "idle"
    
    def _resolve_variables(self, context, all_nodes=None):
        """解析变量引用
        
        注意：这里返回解析后的值，而不是修改原始变量，避免变量互传
        """
        from 工具类.变量引用解析器 import VariableReferenceResolver
        
        # 解析输入变量中的引用，但不修改原始变量
        resolved_inputs = []
        if 'inputs' in self.variables:
            for input_var in self.variables['inputs']:
                if 'value' in input_var:
                    # 创建副本以避免修改原始变量
                    resolved_var = input_var.copy()
                    
                    # 使用variables中的输入值
                    input_value = input_var.get('value', '')
                    
                    resolved_var['value'] = VariableReferenceResolver.resolve_value(
                        input_value, context, all_nodes
                    )
                    resolved_inputs.append(resolved_var)
                else:
                    resolved_inputs.append(input_var)
        
        return resolved_inputs
    
    def _execute(self, context):
        """节点具体执行逻辑，子类需要实现"""
        return None
    
    def get_connected_node(self, port_label=None):
        """获取连接的前一个节点
        
        Args:
            port_label: 端口标签，可选，指定要检查的端口
        
        Returns:
            BaseNode: 连接的前一个节点，如果没有连接则返回None
        """
        for port in self.ports:
            if port.port_type == "input":
                if port_label and port.label != port_label:
                    continue
                if port.connections:
                    connection = port.connections[0]  # 只取第一个连接
                    if connection.start_port:
                        return connection.start_port.parentItem()
        return None
    
    def get_connected_node_output(self, context, port_label=None):
        """获取连接的前一个节点的输出
        
        Args:
            context: 执行上下文
            port_label: 端口标签，可选，指定要检查的端口
        
        Returns:
            Any: 前一个节点的输出值，如果没有连接则返回None
        """
        connected_node = self.get_connected_node(port_label)
        if connected_node:
            return context.get_node_output(connected_node.id)
        return None
    
    def get_connected_node_variables(self, port_label=None):
        """获取连接的前一个节点的变量
        
        Args:
            port_label: 端口标签，可选，指定要检查的端口
        
        Returns:
            dict: 前一个节点的变量字典，如果没有连接则返回空字典
        """
        connected_node = self.get_connected_node(port_label)
        if connected_node and hasattr(connected_node, 'variables'):
            return connected_node.variables
        return {}
    
    def on_completed(self, context):
        """节点执行完成后的回调方法，子类可以重写"""
        pass
    
    def add_port(self, port_type, data_type, x, y, max_connections=1, label=""):
        """添加端口到节点
        
        Args:
            port_type: 端口方向，input 或 output
            data_type: 数据类型，如 int、float、str 等
            x: 端口在节点中的 x 坐标
            y: 端口在节点中的 y 坐标
            max_connections: 最大连接数，-1表示无限制
            label: 标签名，显示在端口旁边的文本
        
        Returns:
            NodePort: 创建的端口对象
        """
        port = NodePort(self, port_type, data_type, label, max_connections=max_connections)
        port.setPos(x, y)
        # 确保端口在节点上方
        port.setZValue(self.zValue() + 10)
        self.ports.append(port)
        return port
    
    def add_input_port(self, data_type, label, y=None, max_connections=1):
        """添加输入端口到节点
        
        Args:
            data_type: 数据类型，如 int、float、str 等
            label: 标签名，显示在端口旁边的文本
            y: 端口在节点中的 y 坐标，默认在节点中心
            max_connections: 最大连接数，-1表示无限制
        
        Returns:
            NodePort: 创建的输入端口对象
        """
        if y is None:
            y = self.height // 2  # 默认在节点中心
        return self.add_port("input", data_type, 16, y, max_connections, label)
    
    def add_output_port(self, data_type, label, y=None, max_connections=1):
        """添加输出端口到节点
        
        Args:
            data_type: 数据类型，如 int、float、str 等
            label: 标签名，显示在端口旁边的文本
            y: 端口在节点中的 y 坐标，默认在节点中心
            max_connections: 最大连接数，-1表示无限制
        
        Returns:
            NodePort: 创建的输出端口对象
        """
        if y is None:
            y = self.height // 2  # 默认在节点中心
        return self.add_port("output", data_type, self.width - 16, y, max_connections, label)
    
    def flash(self, duration_ms=500):
        """开始闪烁卡片边框"""
        if self._is_flashing:
            return
        self._is_flashing = True
        # 存储当前执行状态的边框
        self._original_border_pen_before_flash = self.state_border_pens.get(self.execution_status, QPen(Qt.PenStyle.NoPen))
        self._flash_border_on = True
        self._current_border_pen = self.flash_border_pen
        self.flash_toggle_timer.start(self.flash_interval_ms)
        self.update()
    
    def stop_flash(self):
        """停止闪烁并恢复边框"""
        if not self._is_flashing:
            return
        self._is_flashing = False
        self.flash_toggle_timer.stop()
        self._current_border_pen = self._original_border_pen_before_flash
        self.update()
    
    def _toggle_flash_border(self):
        """定时器调用，切换闪烁状态"""
        if not self._is_flashing:
            self.flash_toggle_timer.stop()
            return
        self._flash_border_on = not self._flash_border_on
        if self._flash_border_on:
            self._current_border_pen = self.flash_border_pen
        else:
            self._current_border_pen = self._original_border_pen_before_flash
        self.update()
    
    def set_custom_name(self, custom_name):
        """设置卡片的自定义名称"""
        self.custom_name = custom_name
        # 更新标题显示
        # 提取类名中的大写字母作为简写
        node_type = self.__class__.__name__
        node_abbr = ''.join([c for c in node_type if c.isupper()])
        if not node_abbr:
            # 如果没有大写字母，使用类名的前3个字符
            node_abbr = node_type[:3].lower()
        else:
            # 限制简写长度为2-3个字母
            node_abbr = node_abbr[:3].lower()
        if custom_name:
            self.title = f"{custom_name} ({node_abbr}_id:{self.id})"
        else:
            self.title = f"{self.__class__.__name__} ({node_abbr}_id:{self.id})"
        self.update()
    
    def hoverEnterEvent(self, event):
        """鼠标进入事件"""
        # 生成工具提示
        if not self._cached_tooltip or self._tooltip_needs_update:
            self._cached_tooltip = self._generate_tooltip_text()
            self._tooltip_needs_update = False
        
        # 立即显示工具提示在鼠标上方
        if self._cached_tooltip:
            # 获取鼠标的全局位置
            global_pos = event.screenPos()
            # 调整位置，使提示显示在鼠标正上方
            adjusted_pos = global_pos - QPointF(10, 50)
            QToolTip.showText(adjusted_pos, self._cached_tooltip)
        
        super().hoverEnterEvent(event)
    
    def hoverMoveEvent(self, event):
        """鼠标在节点上移动事件"""
        if self._cached_tooltip:
            # 获取鼠标的全局位置
            global_pos = event.screenPos()
            # 调整位置，使提示显示在鼠标正上方
            adjusted_pos = global_pos - QPointF(10, 50)
            QToolTip.showText(adjusted_pos, self._cached_tooltip)
        
        super().hoverMoveEvent(event)
    
    def toolTip(self):
        """重写toolTip方法，返回空字符串，禁用默认工具提示"""
        return ""
    
    def hoverLeaveEvent(self, event):
        """鼠标离开事件"""
        # 清除工具提示
        self.setToolTip("")
        QToolTip.hideText()
        super().hoverLeaveEvent(event)
    
    def _generate_tooltip_text(self):
        """生成工具提示文本"""
        # 快速检查：如果没有变量，直接返回简单文本
        if not self.variables:
            return "详细参数:\n  (无参数)"
        
        param_lines = ["详细参数:"]
        
        # 生成工具提示文本
        for key, value in self.variables.items():
            # 跳过位置信息
            if key == 'position':
                continue
            
            # 格式化值
            formatted_value = self._format_tooltip_value(value)
            param_lines.append(f"  {key}: {formatted_value}")
        
        return "\n".join(param_lines)
    
    def _format_tooltip_value(self, value):
        """格式化工具提示值"""
        if value is None:
            return "None"
        if isinstance(value, bool):
            return "是" if value else "否"
        
        # 转换为字符串
        str_value = str(value)
        
        # 特殊处理多行文本
        if isinstance(value, str) and '\n' in str_value:
            lines = str_value.strip().split('\n')
            
            # 如果是路径点坐标格式（每行都是 x,y 格式）
            if len(lines) > 3 and all(',' in line.strip() for line in lines[:3] if line.strip()):
                # 显示前3个点和总数
                preview_lines = lines[:3]
                total_count = len([line for line in lines if line.strip()])
                preview_text = '\n    '.join(preview_lines)
                return f"{preview_text}\n    ... (共{total_count}个坐标点)"
            
            # 其他多行文本，限制显示行数
            elif len(lines) > 5:
                preview_lines = lines[:5]
                preview_text = '\n    '.join(preview_lines)
                return f"{preview_text}\n    ... (共{len(lines)}行)"
            else:
                # 少于5行，直接显示，但添加缩进
                return '\n    '.join(lines)
        
        # 单行文本，限制长度
        elif isinstance(value, str) and len(str_value) > 50:
            return f"{str_value[:47]}..."
        
        # 对于其他类型（int, float等），使用标准字符串转换
        return str_value