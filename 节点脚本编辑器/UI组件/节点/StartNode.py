from 节点核心.节点基类端口 import BaseNode
from PySide6.QtGui import QFont, QColor, QPen
from PySide6.QtCore import Qt

class StartNode(BaseNode):
    """开始节点
    
    设计特点：
    1. 只有一个输出执行端口
    2. 作为整个流程的起点
    3. 点击执行时，按照连接顺序一个一个往下执行
    """
    
    def __init__(self, width=150, height=60, x=0, y=0):
        super().__init__("开始", QColor("#E74C3C"), width, height, x, y)
        self.init_ports()
        self.update_variables()

    def init_ports(self):
        # 清空端口列表
        self.ports.clear()
        # 只添加一个输出执行端口，设置max_connections=-1表示无限制
        self.add_port("output", "exec", self.width - 16, 30, max_connections=-1)

    def paint(self, painter, option, widget):
        try:
            # 调用父类的paint方法
            super().paint(painter, option, widget)
        except Exception:
            # 忽略绘制错误，避免程序崩溃
            pass

    def update_variables(self):
        """更新内置变量"""
        super().update_variables()
        
        # 输出变量
        self.variables['outputs'] = [
            {'name': '执行', 'type': 'exec'}
        ]

    def _execute(self, context, resolved_inputs=None, all_nodes=None):
        """执行开始逻辑"""
        # 不再触发后续节点执行，由execute_all方法中的拓扑排序决定执行顺序
        return None
    
    def contextMenuEvent(self, event):
        """重写右键菜单事件"""
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
        
        # 开始节点不允许删除，所以不添加删除选项
        # 可以添加其他可能的选项，但删除选项被禁用
        menu.addAction(QAction("开始节点", menu))
        
        # 显示菜单
        menu.exec(event.screenPos())