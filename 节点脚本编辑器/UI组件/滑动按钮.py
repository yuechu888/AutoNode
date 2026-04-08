import sys
from PySide6.QtWidgets import QApplication, QWidget, QPushButton
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
from PySide6.QtCore import Qt, QRectF, Property

class SwitchButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)  # 让按钮可切换状态
        self.setChecked(True)    # 默认开启（绿色）
        # 不设置固定尺寸，允许外部通过 setFixedSize 调整
        
        # 颜色定义
        self._checked_color = QColor(52, 208, 88)   # iOS绿色
        self._unchecked_color = QColor(204, 204, 204)
        self._thumb_color = QColor(255, 255, 255)   # 白色滑块
        
        # 确保按钮能够响应点击事件
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        
        # 1. 绘制背景
        rect = QRectF(0, 0, self.width(), self.height())
        bg_color = self._checked_color if self.isChecked() else self._unchecked_color
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, self.height()/2, self.height()/2)
        
        # 2. 绘制白色滑块
        thumb_diameter = self.height() * 0.8
        if self.isChecked():
            thumb_x = self.width() - thumb_diameter - 2
        else:
            thumb_x = 2
        thumb_y = (self.height() - thumb_diameter) / 2
        
        painter.setBrush(QBrush(self._thumb_color))
        painter.setPen(QPen(QColor(200, 200, 200), 1))  # 滑块边框
        painter.drawEllipse(thumb_x, thumb_y, thumb_diameter, thumb_diameter)
    
    def mousePressEvent(self, event):
        # 打印鼠标按下事件，用于调试
        print(f"滑动按钮鼠标按下")
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        # 打印鼠标释放事件，用于调试
        print(f"滑动按钮鼠标释放")
        super().mouseReleaseEvent(event)
    
    def mouseMoveEvent(self, event):
        # 不打印鼠标移动事件，避免过多输出
        super().mouseMoveEvent(event)

class DemoWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 开关按钮示例")
        self.setGeometry(100, 100, 300, 200)
        
        # 创建开关按钮
        self.switch = SwitchButton(self)
        self.switch.move(120, 80)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec())