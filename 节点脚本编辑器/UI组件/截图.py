import sys
from PySide6.QtCore import Qt, QPoint, QRect, Signal
from PySide6.QtGui import QGuiApplication, QPixmap, QPainter, QPen, QColor, QBrush, QPainterPath
from PySide6.QtWidgets import (QApplication, QDialog, QPushButton, QFrame)

HANDLE_SIZE = 8
TOOLBAR_HEIGHT = 32
TOOLBAR_PADDING = 6


class SelectionToolBar(QFrame):
    """选区下方工具栏：取消 ×、确认 √"""
    confirm = Signal()
    cancel = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, TOOLBAR_HEIGHT)
        self.setStyleSheet("""
            QFrame {
                background-color: #2b2d30;
                border-radius: 6px;
            }
            QPushButton {
                color: white;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)

        btn_cancel = QPushButton("✕", self)
        btn_cancel.setGeometry(0, 0, 40, TOOLBAR_HEIGHT)
        btn_cancel.clicked.connect(self.cancel)

        btn_ok = QPushButton("✓", self)
        btn_ok.setGeometry(40, 0, 40, TOOLBAR_HEIGHT)
        btn_ok.clicked.connect(self.confirm)


class ScreenshotWindow(QDialog):
    def __init__(self, mode="screenshot"):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 模式：screenshot（截图）或 range（获取范围）
        self.mode = mode

        # 全屏截图背景
        self.screen = QGuiApplication.primaryScreen()
        self.bg = self.screen.grabWindow(0)
        self.setFixedSize(self.bg.size())

        # 选区状态
        self.selecting = False  # 正在拖拽框选
        self.editing = False    # 松开后进入编辑模式
        self.start = QPoint()
        self.rect = QRect()

        # 拖拽移动
        self.moving_rect = False
        self.move_origin = QPoint()

        # 控制点
        self.dragging_handle = None

        # 工具栏
        self.bar = SelectionToolBar(self)
        self.bar.hide()
        self.bar.confirm.connect(self.on_confirm)
        self.bar.cancel.connect(self.close)
        
        # 保存的文件名
        self.saved_file_name = None
        
        # 创建假的框选框（居中显示，占屏幕的1/4大小）
        screen_width = self.width()
        screen_height = self.height()
        box_width = screen_width // 2
        box_height = screen_height // 2
        box_x = (screen_width - box_width) // 2
        box_y = (screen_height - box_height) // 2
        self.rect = QRect(box_x, box_y, box_width, box_height)
        self.editing = True
        self.update_toolbar()
        self.bar.show()

    def paintEvent(self, e):
        painter = QPainter(self)
        try:
            painter.drawPixmap(0, 0, self.bg)

            # 半透明遮罩
            if not self.rect.isNull():
                mask = QColor(0, 0, 0, 100)
                full = QRect(0, 0, self.width(), self.height())
                # 使用QPainterPath来实现遮罩效果
                path = QPainterPath()
                path.addRect(full)
                path.addRect(self.rect)
                painter.fillPath(path, mask)

            # 选区边框
            pen = QPen(QColor(30, 144, 255), 2)
            painter.setPen(pen)
            painter.drawRect(self.rect)

            # 编辑模式才画8个点
            if self.editing and not self.rect.isNull():
                painter.setBrush(QColor(255, 255, 255))
                # 计算各个中心点
                top_left = self.rect.topLeft()
                top_right = self.rect.topRight()
                bottom_left = self.rect.bottomLeft()
                bottom_right = self.rect.bottomRight()
                top_center = QPoint(self.rect.center().x(), self.rect.top())
                bottom_center = QPoint(self.rect.center().x(), self.rect.bottom())
                center_left = QPoint(self.rect.left(), self.rect.center().y())
                center_right = QPoint(self.rect.right(), self.rect.center().y())
                
                points = [
                    top_left,
                    top_right,
                    bottom_left,
                    bottom_right,
                    top_center,
                    bottom_center,
                    center_left,
                    center_right,
                ]
                for p in points:
                    painter.drawEllipse(p.x() - HANDLE_SIZE//2,
                                       p.y() - HANDLE_SIZE//2,
                                       HANDLE_SIZE, HANDLE_SIZE)
        finally:
            # 确保painter正确结束
            painter.end()

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            return

        pos = e.position().toPoint()

        # 如果在编辑模式下
        if self.editing:
            # 检查是否点击在控制点上
            handle = self.get_handle_at(pos)
            if handle:
                # 开始拖拽控制点
                self.dragging_handle = handle
                return
            
            # 检查是否点击在选区内
            if self.rect.contains(pos):
                # 开始移动选区
                self.moving_rect = True
                self.move_origin = pos
                return
        
        # 点击在选区外，开始新的框选
        self.editing = False
        self.bar.hide()
        self.selecting = True
        self.start = pos
        self.rect = QRect()
        self.update()

    def mouseMoveEvent(self, e):
        pos = e.position().toPoint()

        # 框选拖拽
        if self.selecting:
            self.rect = QRect(self.start, pos).normalized()
            self.update()
            return

        # 移动整个选区
        if self.moving_rect:
            dx = pos.x() - self.move_origin.x()
            dy = pos.y() - self.move_origin.y()
            self.rect.translate(dx, dy)
            self.rect = self.rect.intersected(self.rect)
            self.move_origin = pos
            self.update()
            self.update_toolbar()
            return

        # 拖拽控制点缩放
        if self.dragging_handle and self.editing:
            self.resize_by_handle(pos)
            self.update()
            self.update_toolbar()
            return

    def mouseReleaseEvent(self, e):
        self.selecting = False
        self.moving_rect = False
        self.dragging_handle = None

        # 有效选区：进入编辑模式并显示工具栏
        if self.rect.width() > 20 and self.rect.height() > 20:
            self.editing = True
            self.update_toolbar()
            self.bar.show()
        else:
            self.bar.hide()
            self.editing = False
        self.update()

    def get_handle_at(self, pos):
        r = self.rect
        hs = HANDLE_SIZE
        handles = {
            'top-left': QRect(r.left() - hs//2, r.top() - hs//2, hs, hs),
            'top-right': QRect(r.right() - hs//2, r.top() - hs//2, hs, hs),
            'bottom-left': QRect(r.left() - hs//2, r.bottom() - hs//2, hs, hs),
            'bottom-right': QRect(r.right() - hs//2, r.bottom() - hs//2, hs, hs),
            'top': QRect(r.center().x() - hs//2, r.top() - hs//2, hs, hs),
            'bottom': QRect(r.center().x() - hs//2, r.bottom() - hs//2, hs, hs),
            'left': QRect(r.left() - hs//2, r.center().y() - hs//2, hs, hs),
            'right': QRect(r.right() - hs//2, r.center().y() - hs//2, hs, hs),
        }
        for k, v in handles.items():
            if v.contains(pos):
                return k
        return None

    def resize_by_handle(self, pos):
        r = self.rect
        h = self.dragging_handle
        if h == 'top-left':
            r.setTopLeft(pos)
        elif h == 'top-right':
            r.setTopRight(pos)
        elif h == 'bottom-left':
            r.setBottomLeft(pos)
        elif h == 'bottom-right':
            r.setBottomRight(pos)
        elif h == 'top':
            r.setTop(pos.y())
        elif h == 'bottom':
            r.setBottom(pos.y())
        elif h == 'left':
            r.setLeft(pos.x())
        elif h == 'right':
            r.setRight(pos.x())

        # 最小尺寸限制
        if r.width() < 30:
            r.setWidth(30)
        if r.height() < 30:
            r.setHeight(30)
        self.rect = r.normalized()

    def update_toolbar(self):
        """智能贴边：工具栏放在选区下方，放不下就放上方"""
        r = self.rect
        bar_w = self.bar.width()
        bar_h = self.bar.height()

        # 默认居中下方
        x = r.center().x() - bar_w // 2
        y = r.bottom() + TOOLBAR_PADDING

        # 超出屏幕底部 → 放到选区上方
        if y + bar_h > self.height():
            y = r.top() - bar_h - TOOLBAR_PADDING

        # 左右贴边
        if x < 0:
            x = 0
        if x + bar_w > self.width():
            x = self.width() - bar_w

        self.bar.move(x, y)

    def on_confirm(self):
        """保存截图并退出"""
        if self.mode == "screenshot" and self.rect.isValid():
            shot = self.bg.copy(self.rect)
            # 显示文件名输入对话框
            from PySide6.QtWidgets import QInputDialog
            file_name, ok = QInputDialog.getText(self, "保存截图", "请输入文件名:", text="screenshot")
            if ok and file_name:
                # 确保文件名以.png结尾
                if not file_name.endswith(".png"):
                    file_name += ".png"
                shot.save(file_name, "PNG")
                self.saved_file_name = file_name
        # 如果是range模式，直接关闭窗口
        self.close()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()
        if e.key() in (Qt.Key_Enter, Qt.Key_Return):
            self.on_confirm()
    
    def closeEvent(self, event):
        """处理关闭事件"""
        # 确保所有资源被正确释放
        self.bar.hide()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = ScreenshotWindow()
    win.show()
    sys.exit(app.exec())