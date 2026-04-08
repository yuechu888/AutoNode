import sys
import os
import json
import re
from pathlib import Path

from PySide6.QtWidgets import (QApplication, QMainWindow, QMenu, QFileDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                                QLabel, QLineEdit, QSplitter, QPushButton, QComboBox, QToolTip, QDockWidget, QTextEdit, 
                                QTabWidget, QTreeWidget, QTreeWidgetItem, QScrollArea, QSizePolicy, QTableWidget, 
                                QTableWidgetItem, QDialog, QMessageBox)
from UI组件.滑动按钮 import SwitchButton
from PySide6.QtGui import QAction, QDrag, QTextCharFormat, QColor, QTextCursor
from PySide6.QtCore import Qt, QPointF, QMimeData, Slot, QTimer
from UI组件.画布视图 import NodeGraphicsView
from UI组件.节点 import StartNode
from 节点核心.节点基类端口 import signal_manager
from 节点核心.节点管理器 import node_manager
from 节点核心.连线类 import Connection
from 节点核心.上下文 import Context

def load_stylesheet():
    qss_path = os.path.join(os.path.dirname(__file__), "资源文件", "样式.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def get_config_path():
    return os.path.join(os.path.dirname(__file__), "..", "配置", "快捷键设置.json")

def load_hotkey_settings():
    config_path = get_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"run_key": "F8", "stop_key": "Ctrl+F8"}

def save_hotkey_settings(settings):
    config_path = get_config_path()
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=4)

class HotkeySettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("快捷键设置")
        self.setFixedSize(400, 200)
        self.settings = load_hotkey_settings()
        self.recording_key = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        run_layout = QHBoxLayout()
        run_layout.addWidget(QLabel("运行快捷键:"))
        self.run_key_label = QLabel(self.settings.get("run_key", "F8"))
        self.run_key_label.setStyleSheet("background-color: #3D3D3D; color: white; padding: 5px; border-radius: 4px;")
        self.run_key_label.setFixedWidth(120)
        self.run_key_label.setAlignment(Qt.AlignCenter)
        self.run_key_label.mousePressEvent = lambda e: self.start_recording("run")
        run_layout.addWidget(self.run_key_label)
        layout.addLayout(run_layout)
        
        stop_layout = QHBoxLayout()
        stop_layout.addWidget(QLabel("停止快捷键:"))
        self.stop_key_label = QLabel(self.settings.get("stop_key", "Ctrl+F8"))
        self.stop_key_label.setStyleSheet("background-color: #3D3D3D; color: white; padding: 5px; border-radius: 4px;")
        self.stop_key_label.setFixedWidth(120)
        self.stop_key_label.setAlignment(Qt.AlignCenter)
        self.stop_key_label.mousePressEvent = lambda e: self.start_recording("stop")
        stop_layout.addWidget(self.stop_key_label)
        layout.addLayout(stop_layout)
        
        layout.addWidget(QLabel("点击标签开始录制新快捷键"))
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
    
    def start_recording(self, key_type):
        self.recording_key = key_type
        if key_type == "run":
            self.run_key_label.setText("请按键...")
        else:
            self.stop_key_label.setText("请按键...")
        self.grabKeyboard()
    
    def keyPressEvent(self, event):
        if self.recording_key:
            key_text = ""
            modifiers = []
            if event.modifiers() & Qt.ControlModifier:
                modifiers.append("Ctrl")
            if event.modifiers() & Qt.ShiftModifier:
                modifiers.append("Shift")
            if event.modifiers() & Qt.AltModifier:
                modifiers.append("Alt")
            
            key = event.key()
            if key == Qt.Key_Control or key == Qt.Key_Shift or key == Qt.Key_Alt:
                super().keyPressEvent(event)
                return
            
            if key in (Qt.Key_Return, Qt.Key_Enter):
                key_text = "Enter"
            elif key == Qt.Key_Escape:
                key_text = "Escape"
            elif key >= 0x20 and key <= 0x7E:
                key_text = chr(key).upper()
            else:
                key_text = {Qt.Key_F1: "F1", Qt.Key_F2: "F2", Qt.Key_F3: "F3", Qt.Key_F4: "F4",
                           Qt.Key_F5: "F5", Qt.Key_F6: "F6", Qt.Key_F7: "F7", Qt.Key_F8: "F8",
                           Qt.Key_F9: "F9", Qt.Key_F10: "F10", Qt.Key_F11: "F11", Qt.Key_F12: "F12"}.get(key, "")
            
            if key_text:
                if modifiers:
                    final_key = "+".join(modifiers) + "+" + key_text
                else:
                    final_key = key_text
                
                if self.recording_key == "run":
                    self.settings["run_key"] = final_key
                    self.run_key_label.setText(final_key)
                else:
                    self.settings["stop_key"] = final_key
                    self.stop_key_label.setText(final_key)
                self.recording_key = None
                self.releaseKeyboard()
        else:
            super().keyPressEvent(event)
    
    def save_settings(self):
        save_hotkey_settings(self.settings)
        self.accept()

# 自定义提示标签类
class HintLabel(QLabel):
    def __init__(self, text, tooltip):
        super().__init__(text)
        self.tooltip_text = tooltip
        self.setMouseTracking(True)
        # 设置文字居中对齐
        self.setAlignment(Qt.AlignCenter)
    
    def enterEvent(self, event):
        super().enterEvent(event)
        if self.tooltip_text:
            global_pos = event.globalPosition()
            adjusted_pos = global_pos - QPointF(0, 30)
            # 显示自定义工具提示
            QToolTip.showText(adjusted_pos.toPoint(), self.tooltip_text)
    
    def leaveEvent(self, event):
        super().leaveEvent(event)
        QToolTip.hideText()
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.tooltip_text:
            global_pos = event.globalPosition()
            adjusted_pos = global_pos - QPointF(0, 30)
            QToolTip.showText(adjusted_pos.toPoint(), self.tooltip_text)
    
    def toolTip(self):
        # 重写toolTip方法，返回空字符串，禁用默认工具提示
        return ""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 隐藏默认标题栏
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("节点脚本编辑器")
        self.setGeometry(100, 100, 1400, 1000)
        
        # 设置软件图标
        from PySide6.QtGui import QIcon
        icon_path = os.path.join(os.path.dirname(__file__), "资源文件", "头像.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # 自定义标题栏变量
        self.is_maximized = False
        self.dragging = False
        self.drag_start_pos = QPointF()
        
        # 用于输入防抖的定时器
        self.input_timer = QTimer(self)
        self.input_timer.setSingleShot(True)
        self.input_timer.timeout.connect(self._handle_input_timeout)
        self.pending_inputs = {}
        
        # 创建顶部水平分割器
        self.top_splitter = QSplitter(Qt.Horizontal)
        
        # 初始化画布
        self.view = NodeGraphicsView()
        
        # 自动创建开始节点（确保只有一个）
        self.start_node = None
        # 检查是否已有开始节点
        for item in self.view.scene.items():
            if item.__class__.__name__ == 'StartNode':
                self.start_node = item
                # 确保开始节点已添加到视图的nodes字典中
                if self.start_node.id not in self.view.nodes:
                    self.view.nodes[self.start_node.id] = self.start_node
                    # 连接信号
                    self.start_node.delete_requested.connect(self.view.delete_node)
                    self.start_node.copy_requested.connect(self.view.handle_copy_node)
                    self.start_node.edit_settings_requested.connect(self.view.edit_node_settings)
                    self.start_node.card_clicked.connect(self.view.handle_card_clicked)
                break
        # 如果没有开始节点，创建一个
        if not self.start_node:
            self.start_node = StartNode(x=100, y=100)
            self.view.scene.addItem(self.start_node)
            # 添加到视图的nodes字典中
            self.view.nodes[self.start_node.id] = self.start_node
            # 连接信号
            self.start_node.delete_requested.connect(self.view.delete_node)
            self.start_node.copy_requested.connect(self.view.handle_copy_node)
            self.start_node.edit_settings_requested.connect(self.view.edit_node_settings)
            self.start_node.card_clicked.connect(self.view.handle_card_clicked)
        
        # 自动加载保存的节点内容
        self.load_saved_nodes()
        
        # 不再自动创建查找图片节点，用户可以从节点库中手动添加
        
        # 添加画布到顶部分割器
        self.top_splitter.addWidget(self.view)
        
        # 创建右侧选项卡
        self.right_tab_widget = QTabWidget()
        self.right_tab_widget.setFixedWidth(350)
        
        # 创建属性面板
        self.property_panel = self.create_property_panel()
        # 默认显示属性面板
        self.property_panel.show()
        
        # 创建节点库
        self.node_tree = self.create_node_tree()
        
        # 添加选项卡
        self.right_tab_widget.addTab(self.property_panel, "属性面板")
        self.right_tab_widget.addTab(self.node_tree, "节点库")
        
        # 添加选项卡到顶部分割器
        self.top_splitter.addWidget(self.right_tab_widget)
        
        # 创建日志窗口
        self.create_log_window()
        
        # 加载暗黑样式
        self.setStyleSheet(load_stylesheet())
        
        # 创建菜单栏
        self.create_menu()
        
        # 创建自定义标题栏
        self.create_custom_title_bar()
        
        # 连接信号
        self.view.scene.selectionChanged.connect(self.on_selection_changed)
        # 连接节点选中信号
        signal_manager.node_selected_signal.connect(self.on_node_selected)
        
        # 当前选中的节点
        self.selected_node = self.start_node
        # 当前在属性面板中显示的节点
        self.current_property_node = self.start_node
        # 当前选中节点的ID，用于判断是否重新选中同一个节点
        self.current_selected_node_id = self.start_node.id if self.start_node else None
        
        # 初始显示开始节点的属性
        self.start_node.update_variables()
        self.on_node_selected(self.start_node.variables)
        
        # 安装事件过滤器（必须在pynput之前）
        self.installEventFilter(self)
        
        # 使用pynput添加全局快捷键
        from pynput import keyboard
        import threading
        
        # 加载快捷键设置
        self.hotkey_settings = load_hotkey_settings()
        self.current_keys = set()
        
        def get_key_name(key):
            key_map = {
                keyboard.Key.ctrl_l: "Ctrl", keyboard.Key.ctrl_r: "Ctrl",
                keyboard.Key.shift_l: "Shift", keyboard.Key.shift_r: "Shift",
                keyboard.Key.alt_l: "Alt", keyboard.Key.alt_r: "Alt",
                keyboard.Key.f1: "F1", keyboard.Key.f2: "F2", keyboard.Key.f3: "F3",
                keyboard.Key.f4: "F4", keyboard.Key.f5: "F5", keyboard.Key.f6: "F6",
                keyboard.Key.f7: "F7", keyboard.Key.f8: "F8", keyboard.Key.f9: "F9",
                keyboard.Key.f10: "F10", keyboard.Key.f11: "F11", keyboard.Key.f12: "F12",
                keyboard.Key.enter: "Enter", keyboard.Key.space: "Space",
                keyboard.Key.tab: "Tab", keyboard.Key.esc: "Escape",
            }
            if key in key_map:
                return key_map[key]
            try:
                char = key.char.upper()
                if char.isalnum() and len(char) == 1:
                    return char
            except:
                pass
            return None
        
        def on_press(key):
            try:
                key_name = get_key_name(key)
                if key_name is None:
                    return
                
                if key_name in ("Ctrl", "Shift", "Alt"):
                    self.current_keys.add(key_name)
                else:
                    self.current_keys.add(key_name)
                    current_combo = "+".join(sorted(self.current_keys))
                    
                    if current_combo == self.hotkey_settings.get("run_key", "F8"):
                        from PySide6.QtCore import QCoreApplication, QEvent
                        QCoreApplication.postEvent(self, QEvent(QEvent.Type(1000)))
                    elif current_combo == self.hotkey_settings.get("stop_key", "Ctrl+F8"):
                        from PySide6.QtCore import QCoreApplication, QEvent
                        QCoreApplication.postEvent(self, QEvent(QEvent.Type(1001)))
            except Exception as e:
                print(f"按键处理出错: {e}")
        
        def on_release(key):
            try:
                key_name = get_key_name(key)
                if key_name:
                    self.current_keys.discard(key_name)
            except Exception as e:
                print(f"按键释放处理出错: {e}")
        
        # 启动键盘监听线程
        self.keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.keyboard_listener.start()
        print("pynput键盘监听已启动")
    
    def create_menu(self):
        # 菜单功能已集成到自定义标题栏中，此方法保留为兼容性
        pass
    
    def create_custom_title_bar(self):
        """创建自定义标题栏"""
        
        
        # 创建标题栏部件
        self.title_bar = QWidget()
        self.title_bar.setStyleSheet("""
            QWidget {
                background-color: #2D2D2D;
                border-bottom: 1px solid #555555;
            }
        """)
        self.title_bar.setFixedHeight(40)
        
        # 创建标题栏布局
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 5, 10, 5)
        title_layout.setSpacing(10)
        
        # 创建打开图片按钮
        self.open_image_button = QPushButton("打开图片")
        self.open_image_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
            QPushButton:pressed {
                background-color: #1E90FF;
            }
        """)
        self.open_image_button.clicked.connect(self.open_image_folder)
        
        # 创建加入交流群按钮
        self.join_group_button = QPushButton("加入交流群")
        self.join_group_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4ECDC4;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
            QPushButton:pressed {
                background-color: #4ECDC4;
                color: white;
            }
        """)
        self.join_group_button.clicked.connect(self.show_group_window)
        
        # 设置窗口标题
        self.setWindowTitle("节点脚本编辑器")
        
        # 创建窗口控制按钮
        button_style = """
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
            QPushButton:pressed {
                background-color: #1E90FF;
            }
        """
        
        # 创建快捷键设置按钮
        self.hotkey_settings_btn = QPushButton("⚙")
        self.hotkey_settings_btn.setStyleSheet(button_style)
        self.hotkey_settings_btn.setFixedSize(30, 28)
        self.hotkey_settings_btn.setToolTip("快捷键设置")
        self.hotkey_settings_btn.clicked.connect(self.show_hotkey_settings)
        
        # 最小化按钮
        button_style = """
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3D3D3D;
            }
            QPushButton:pressed {
                background-color: #1E90FF;
            }
        """
        
        # 最小化按钮
        min_button = QPushButton("_")
        min_button.setStyleSheet(button_style)
        min_button.setFixedSize(30, 28)
        min_button.clicked.connect(self.showMinimized)
        
        # 最大化/还原按钮
        self.max_button = QPushButton("□")
        self.max_button.setStyleSheet(button_style)
        self.max_button.setFixedSize(30, 28)
        self.max_button.clicked.connect(self.toggle_maximize)
        
        # 关闭按钮
        close_button = QPushButton("×")
        close_button.setStyleSheet(button_style)
        close_button.setFixedSize(30, 28)
        close_button.clicked.connect(self.close)
        
        # 创建运行按钮
        self.run_button = QPushButton("运行")
        self.run_button.setStyleSheet(button_style)
        self.run_button.setFixedSize(60, 28)
        self.run_button.clicked.connect(self.execute_all)
        
        # 创建停止按钮
        self.stop_button = QPushButton("停止")
        self.stop_button.setStyleSheet(button_style)
        self.stop_button.setFixedSize(60, 28)
        self.stop_button.clicked.connect(self.stop_execution)
        self.stop_button.hide()
        
        # 创建赞助按钮
        sponsor_button = QPushButton("❤")
        sponsor_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #FF6B6B;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 107, 107, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(255, 107, 107, 0.4);
            }
        """)
        sponsor_button.setFixedSize(30, 28)
        sponsor_button.clicked.connect(self.show_sponsor_window)
        
        # 添加部件到布局
        title_layout.addWidget(self.open_image_button)
        title_layout.addWidget(self.join_group_button)
        title_layout.addStretch()
        title_layout.addWidget(self.hotkey_settings_btn)
        title_layout.addWidget(sponsor_button)
        title_layout.addWidget(self.run_button)
        title_layout.addWidget(self.stop_button)
        title_layout.addWidget(min_button)
        title_layout.addWidget(self.max_button)
        title_layout.addWidget(close_button)
        
        # 添加标题栏到主窗口
        # 创建一个新的垂直布局作为主布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建垂直布局放置标题栏、顶部内容和日志窗口
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 添加标题栏
        content_layout.addWidget(self.title_bar)
        # 添加顶部分割器，设置拉伸因子为1，使其占据剩余空间
        content_layout.addWidget(self.top_splitter, 1)
        # 添加日志窗口，设置固定高度
        self.log_widget.setFixedHeight(self.log_expanded_height)
        content_layout.addWidget(self.log_widget)
        
        main_layout.addLayout(content_layout)
        
        # 设置新的中心部件
        self.setCentralWidget(main_widget)
        

    
    def toggle_maximize(self):
        """切换窗口最大化/还原状态"""
        if self.is_maximized:
            self.showNormal()
            self.max_button.setText("□")
            self.is_maximized = False
        else:
            self.showMaximized()
            self.max_button.setText("□")
            self.is_maximized = True
    
    def mousePressEvent(self, event):
        """鼠标按下事件，用于窗口拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击在标题栏区域
            if self.title_bar.geometry().contains(event.pos()):
                self.dragging = True
                self.drag_start_pos = event.globalPosition() - self.frameGeometry().topLeft()
                event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件，用于窗口拖动"""
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition() - self.drag_start_pos
            self.move(new_pos.toPoint())
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件，结束窗口拖动"""
        self.dragging = False
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理全局热键消息和自定义事件"""
        # 处理自定义事件（来自热键监听线程）
        if event.type() == 1000:  # 运行事件
            print("收到运行事件")
            self.execute_all()
            return True
        elif event.type() == 1001:  # 停止事件
            print("收到停止事件")
            self.stop_execution()
            return True
        
        return super().eventFilter(obj, event)
    
    def open_image_folder(self):
        """打开图片文件夹"""
        print("打开图片文件夹方法被调用")
        try:
            import os
            import subprocess
            
            # 获取程序所在目录的相对路径
            image_folder = os.path.join(os.path.dirname(__file__), "..", "脚本", "Pic")
            print(f"图片文件夹路径: {image_folder}")
            
            # 检查文件夹是否存在
            if not os.path.exists(image_folder):
                print("图片文件夹不存在")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "提示", "图片文件夹不存在，请先创建该目录")
                return
            
            # 打开文件夹
            if os.name == 'nt':  # Windows
                print("在Windows系统上打开文件夹")
                os.startfile(str(image_folder))
                print("文件夹已打开")
            else:  # 其他系统
                print("在非Windows系统上打开文件夹")
                subprocess.run(['open', str(image_folder)])
                print("文件夹已打开")
        except Exception as e:
            print(f"打开图片文件夹失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "错误", f"打开图片文件夹失败: {str(e)}")
    
    def stop_execution(self):
        """停止执行所有节点"""
        print("停止执行方法被调用")
        self.should_stop = True
        self.is_executing = False  # 重置执行标志
        # 设置上下文的停止标志
        if hasattr(self, 'current_context') and self.current_context:
            print("设置上下文停止标志")
            self.current_context.set_stop_requested(True)
        # 显示运行按钮，隐藏停止按钮
        self.run_button.show()
        self.stop_button.hide()
        QApplication.processEvents()
    
    def show_sponsor_window(self):
        """显示赞助窗口"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        
        # 创建赞助窗口
        dialog = QDialog(self, Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        dialog.setWindowTitle("赞助作者")
        dialog.setFixedSize(500, 450)
        dialog.setModal(True)
        
        # 创建布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 30, 40, 30)
        
        # 标题
        title_label = QLabel("感谢您的支持！❤")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; text-align: center; color: #333333;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 说明文本
        desc_label = QLabel("如果这个工具对您有帮助，欢迎赞助支持项目持续开发")
        desc_label.setStyleSheet("font-size: 14px; text-align: center; color: #666666; margin-top: 10px;")
        desc_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(desc_label)
        
        # 二维码布局
        qr_layout = QHBoxLayout()
        qr_layout.setSpacing(60)
        qr_layout.setAlignment(Qt.AlignCenter)
        
        # 微信二维码
        wechat_layout = QVBoxLayout()
        wechat_layout.setAlignment(Qt.AlignCenter)
        wechat_label = QLabel("微信赞助")
        wechat_label.setStyleSheet("font-size: 14px; text-align: center; color: #666666; margin-bottom: 15px;")
        wechat_label.setAlignment(Qt.AlignCenter)
        wechat_layout.addWidget(wechat_label)
        
        wechat_qr = QLabel()
        # 这里使用默认的占位图片，用户可以替换
        qr_path = os.path.join(os.path.dirname(__file__), "资源文件", "wechat_qr.png")
        if os.path.exists(qr_path):
            pixmap = QPixmap(str(qr_path))
            # 确保图片完整显示，使用平滑转换
            wechat_qr.setPixmap(pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            # 创建一个简单的二维码占位符
            wechat_qr.setStyleSheet("border: 1px solid #CCCCCC; width: 180px; height: 180px;")
        wechat_qr.setAlignment(Qt.AlignCenter)
        wechat_qr.setFixedSize(180, 180)
        wechat_layout.addWidget(wechat_qr)
        
        qr_layout.addLayout(wechat_layout)
        
        # 支付宝二维码
        alipay_layout = QVBoxLayout()
        alipay_layout.setAlignment(Qt.AlignCenter)
        alipay_label = QLabel("支付宝赞助")
        alipay_label.setStyleSheet("font-size: 14px; text-align: center; color: #666666; margin-bottom: 15px;")
        alipay_label.setAlignment(Qt.AlignCenter)
        alipay_layout.addWidget(alipay_label)
        
        alipay_qr = QLabel()
        # 这里使用默认的占位图片，用户可以替换
        qr_path = os.path.join(os.path.dirname(__file__), "资源文件", "alipay_qr.png")
        if os.path.exists(qr_path):
            pixmap = QPixmap(str(qr_path))
            # 确保图片完整显示，使用平滑转换
            alipay_qr.setPixmap(pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            # 创建一个简单的二维码占位符
            alipay_qr.setStyleSheet("border: 1px solid #CCCCCC; width: 180px; height: 180px;")
        alipay_qr.setAlignment(Qt.AlignCenter)
        alipay_qr.setFixedSize(180, 180)
        alipay_layout.addWidget(alipay_qr)
        
        qr_layout.addLayout(alipay_layout)
        main_layout.addLayout(qr_layout)
        
        # 移除关闭按钮，用户可以通过标题栏的关闭按钮关闭窗口
        
        # 设置布局
        dialog.setLayout(main_layout)
        
        # 显示窗口
        dialog.exec()
    
    def show_hotkey_settings(self):
        """显示快捷键设置对话框"""
        dialog = HotkeySettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            QMessageBox.information(self, "提示", "快捷键设置已保存，重启后生效")
    
    def show_group_window(self):
        """显示交流群窗口"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        
        # 创建交流群窗口
        dialog = QDialog(self, Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        dialog.setWindowTitle("加入交流群")
        dialog.setFixedSize(400, 450)
        dialog.setModal(True)
        
        # 创建布局
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 30, 40, 30)
        
        # 标题
        title_label = QLabel("加入我们的交流群")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; text-align: center; color: #333333;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 说明文本
        desc_label = QLabel("扫码加入交流群，获取更多使用技巧和更新信息")
        desc_label.setStyleSheet("font-size: 14px; text-align: center; color: #666666; margin-top: 10px;")
        desc_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(desc_label)
        
        # 二维码
        qr_layout = QHBoxLayout()
        qr_layout.setAlignment(Qt.AlignCenter)
        
        qr_label = QLabel()
        # 使用用户提供的QQ群二维码图片
        qr_path = os.path.join(os.path.dirname(__file__), "资源文件", "image.png")
        if os.path.exists(qr_path):
            pixmap = QPixmap(str(qr_path))
            # 确保图片完整显示，使用平滑转换
            qr_label.setPixmap(pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            # 创建一个简单的二维码占位符
            qr_label.setStyleSheet("border: 1px solid #CCCCCC; width: 200px; height: 200px;")
            qr_label.setText("群二维码")
            qr_label.setAlignment(Qt.AlignCenter)
        qr_label.setFixedSize(200, 200)
        qr_layout.addWidget(qr_label)
        
        main_layout.addLayout(qr_layout)
        
        # 群号信息
        group_id_label = QLabel("群号: 828492180")
        group_id_label.setStyleSheet("font-size: 16px; text-align: center; color: #333333; margin-top: 10px;")
        group_id_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(group_id_label)
        
        # 提示信息
        tip_label = QLabel("提示：扫码或搜索群号加入")
        tip_label.setStyleSheet("font-size: 12px; text-align: center; color: #999999; margin-top: 5px;")
        tip_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(tip_label)
        
        # 跳转申请按钮
        jump_button = QPushButton("点击跳转申请")
        jump_button.setStyleSheet("""
            QPushButton {
                background-color: #4ECDC4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45b7aa;
            }
            QPushButton:pressed {
                background-color: #3a9e91;
            }
        """)
        jump_button.setFixedSize(150, 36)
        
        # 按钮点击事件
        def on_jump_clicked():
            import webbrowser
            # 这里可以替换为实际的申请链接
            webbrowser.open("https://qm.qq.com/q/vPWPhLVwwS")
        
        jump_button.clicked.connect(on_jump_clicked)
        
        # 添加按钮到布局
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.addWidget(jump_button)
        main_layout.addLayout(button_layout)
        
        # 设置布局
        dialog.setLayout(main_layout)
        
        # 显示窗口
        dialog.exec()
    
    def save_graph(self):
        # 打开保存对话框
        file_path, _ = QFileDialog.getSaveFileName(self, "保存节点图", "", "JSON Files (*.json)")
        if not file_path:
            return
        
        # 收集节点数据
        nodes = []
        for item in self.view.scene.items():
            if hasattr(item, 'title') and hasattr(item, 'ports'):
                # 是节点
                node_data = {
                    'type': item.__class__.__name__,
                    'title': item.title,
                    'pos': {'x': item.x(), 'y': item.y()},
                    'width': item.width,
                    'height': item.height
                }
                
                # 收集端口信息
                ports = []
                for port in item.ports:
                    port_data = {
                        'port_type': port.port_type,
                        'pos': {'x': port.x(), 'y': port.y()}
                    }
                    ports.append(port_data)
                node_data['ports'] = ports
                
                # 收集参数 - 使用节点的variables属性保存所有属性
                if hasattr(item, 'variables'):
                    node_data['variables'] = item.variables
                
                nodes.append(node_data)
        
        # 收集连线数据
        connections = []
        for item in self.view.scene.items():
            if hasattr(item, 'start_port') and hasattr(item, 'end_port'):
                # 是连线
                if item.end_port:
                    # 找到开始端口和结束端口所属的节点
                    start_node = None
                    end_node = None
                    for node_item in self.view.scene.items():
                        if hasattr(node_item, 'ports'):
                            if item.start_port in node_item.ports:
                                start_node = node_item
                            if item.end_port in node_item.ports:
                                end_node = node_item
                    
                    if start_node and end_node:
                        # 找到节点在nodes列表中的索引
                        start_node_index = next((i for i, n in enumerate(nodes) if n['type'] == start_node.__class__.__name__ and n['pos']['x'] == start_node.x() and n['pos']['y'] == start_node.y()), -1)
                        end_node_index = next((i for i, n in enumerate(nodes) if n['type'] == end_node.__class__.__name__ and n['pos']['x'] == end_node.x() and n['pos']['y'] == end_node.y()), -1)
                        
                        if start_node_index != -1 and end_node_index != -1:
                            connection_data = {
                                'start_node_index': start_node_index,
                                'start_port_index': start_node.ports.index(item.start_port),
                                'end_node_index': end_node_index,
                                'end_port_index': end_node.ports.index(item.end_port)
                            }
                            connections.append(connection_data)

        
        # 保存数据
        graph_data = {
            'nodes': nodes,
            'connections': connections
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
    
    def load_graph(self):
        # 打开加载对话框
        file_path, _ = QFileDialog.getOpenFileName(self, "加载节点图", "", "JSON Files (*.json)")
        if not file_path:
            return
        
        # 清除现有内容
        self.view.scene.clear()
        
        # 读取数据
        with open(file_path, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)
        
        # 加载节点
        loaded_nodes = []
        
        for node_data in graph_data['nodes']:
            node_type = node_data['type']
            # 跳过StartNode
            if node_type == 'StartNode':
                continue
            # 使用节点管理器创建节点
            node = node_manager.create_node(node_type)
            if not node:
                continue
            
            # 设置节点属性 - 使用保存的variables属性
            if 'variables' in node_data:
                node.variables = node_data['variables']
                # 调用update_variables确保节点内部状态同步
                node.update_variables()
            
            node.setPos(node_data['pos']['x'], node_data['pos']['y'])
            node.width = node_data['width']
            node.height = node_data['height']
            self.view.scene.addItem(node)
            loaded_nodes.append(node)
        
        # 加载连线
        
        for connection_data in graph_data['connections']:
            start_node = loaded_nodes[connection_data['start_node_index']]
            start_port = start_node.ports[connection_data['start_port_index']]
            end_node = loaded_nodes[connection_data['end_node_index']]
            end_port = end_node.ports[connection_data['end_port_index']]
            
            connection = Connection(start_port, end_port)
            self.view.scene.addItem(connection)
    
    def create_property_panel(self):
        """创建属性面板"""
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setStyleSheet("background-color: #2D2D2D; color: white; border: none;")
        scroll_area.setWidgetResizable(True)
        scroll_area.setContentsMargins(0, 0, 0, 0)
        
        # 创建内容面板
        panel = QWidget()
        panel.setStyleSheet("background-color: #2D2D2D; color: white;")
        layout = QVBoxLayout(panel)
        layout.setSpacing(0)
        layout.setContentsMargins(10, 0, 10, 0)
        
        # 面板标题
        title_label = QLabel("属性面板")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 节点标题
        self.title_label = QLabel("节点: 无")
        self.title_label.setStyleSheet("margin-bottom: 15px;")
        layout.addWidget(self.title_label)
        
        # 添加分割线
        separator0 = QWidget()
        separator0.setStyleSheet("height: 1px; background-color: #555555;")
        separator0.setFixedHeight(1)
        layout.addWidget(separator0)
        
        # 节点参数
        self.params_group = QWidget()
        params_layout = QVBoxLayout(self.params_group)
        
        # 参数输入框
        self.param_inputs = []
        
        # 输入变量区域
        self.inputs_group = QWidget()
        self.inputs_layout = QVBoxLayout(self.inputs_group)
        self.inputs_layout.setSpacing(0)
        self.inputs_layout.setContentsMargins(0, 0, 0, 0)
        # 设置布局为顶部对齐，避免垂直拉伸
        self.inputs_layout.setAlignment(Qt.AlignTop)
        # 设置大小策略为最小化，根据内容自动调整高度
        self.inputs_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        # 输出变量区域
        self.outputs_group = QWidget()
        self.outputs_layout = QVBoxLayout(self.outputs_group)
        self.outputs_layout.setSpacing(0)
        self.outputs_layout.setContentsMargins(0, 0, 0, 0)
        # 设置布局为顶部对齐，避免垂直拉伸
        self.outputs_layout.setAlignment(Qt.AlignTop)
        # 设置大小策略为最小化，根据内容自动调整高度
        self.outputs_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        
        # 输入参数收纳按钮
        self.inputs_expanded = True
        inputs_toggle_layout = QHBoxLayout()
        inputs_toggle_layout.setAlignment(Qt.AlignLeft)
        inputs_toggle_layout.setSpacing(5)
        
        self.inputs_toggle_button = QPushButton("▼ 输入")
        self.inputs_toggle_button.setStyleSheet("color: #1E90FF; border: none; border-radius: 0; padding: 8px 10px; text-align: left;")
        self.inputs_toggle_button.setMinimumWidth(80)
        self.inputs_toggle_button.clicked.connect(self.toggle_inputs)
        
        # 添加提示图标
        hint_icon = QLabel("ⓘ")
        hint_icon.setStyleSheet("font-size: 14px; color: #1E90FF; padding: 8px 5px;")
        hint_icon.setFixedWidth(30)

        hint_icon = HintLabel("i", "请输入API的参数，当此节点运行时，会将这些参数传入并调用这个API")
        hint_icon.setStyleSheet("font-size: 12px; color: white; font-weight: bold; background-color: #3498DB; border-radius: 8px; text-align: center; padding: 0px; line-height: 16px;")
        hint_icon.setFixedSize(16, 16)
        
        inputs_toggle_layout.addWidget(self.inputs_toggle_button)
        inputs_toggle_layout.addWidget(hint_icon)
        layout.addLayout(inputs_toggle_layout)
        
        # 添加输入按钮与参数之间的间距
        spacing_widget = QWidget()
        spacing_widget.setFixedHeight(4)
        layout.addWidget(spacing_widget)
        
        # 输入参数区域
        # 设置拉伸因子为0，避免输入区域被拉伸
        layout.addWidget(self.inputs_group, 0)
        
        # 添加分割线
        separator1 = QWidget()
        separator1.setStyleSheet("height: 1px; background-color: #555555;")
        separator1.setFixedHeight(1)
        layout.addWidget(separator1)
        
        # 输出结果收纳按钮
        self.outputs_expanded = True
        outputs_toggle_layout = QHBoxLayout()
        outputs_toggle_layout.setAlignment(Qt.AlignLeft)
        outputs_toggle_layout.setSpacing(5)
        
        self.outputs_toggle_button = QPushButton("▼ 输出")
        self.outputs_toggle_button.setStyleSheet("color: #1E90FF; border: none; border-radius: 0; padding: 8px 10px; text-align: left;")
        self.outputs_toggle_button.setMinimumWidth(80)
        self.outputs_toggle_button.clicked.connect(self.toggle_outputs)
        
        # 添加提示图标
        hint_icon2 = HintLabel("i", "输出结果显示节点执行后的输出值，包括API调用的返回数据")
        hint_icon2.setStyleSheet("font-size: 12px; color: white; font-weight: bold; background-color: #3498DB; border-radius: 8px; text-align: center; padding: 0px; line-height: 16px;")
        hint_icon2.setFixedSize(20, 20)
        
        # 添加查看示例链接
        example_link = QLabel("<a href='#' style='color: #1E90FF; text-decoration: none;'>查看示例</a>")
        example_link.setStyleSheet("padding: 8px 5px;")
        example_link.setOpenExternalLinks(False)
        example_link.mousePressEvent = lambda event: print("查看示例被点击")
        
        outputs_toggle_layout.addWidget(self.outputs_toggle_button)
        outputs_toggle_layout.addWidget(hint_icon2)
        outputs_toggle_layout.addWidget(example_link)
        layout.addLayout(outputs_toggle_layout)
        
        # 添加输出按钮与参数之间的间距
        spacing_widget2 = QWidget()
        spacing_widget2.setFixedHeight(4)
        layout.addWidget(spacing_widget2)
        
        # 输出结果区域
        # 设置拉伸因子为0，避免输出区域被拉伸
        layout.addWidget(self.outputs_group, 0)
        
        # 添加分割线
        separator2 = QWidget()
        separator2.setStyleSheet("height: 1px; background-color: #555555;")
        separator2.setFixedHeight(1)
        layout.addWidget(separator2)
        
        # 异常处理收纳按钮
        self.exceptions_expanded = False
        
        # 执行控制标志
        self.is_executing = False
        self.should_stop = False
        self.current_context = None
        exceptions_layout = QHBoxLayout()
        exceptions_layout.setAlignment(Qt.AlignLeft)
        exceptions_layout.setSpacing(5)
        
        self.exceptions_toggle_button = QPushButton("▶ 异常处理")
        self.exceptions_toggle_button.setStyleSheet("color: #1E90FF; border: none; border-radius: 0; padding: 8px 10px; text-align: left;")
        self.exceptions_toggle_button.setMinimumWidth(100)
        self.exceptions_toggle_button.clicked.connect(self.toggle_exceptions)
        
        # 添加提示图标
        hint_icon3 = HintLabel("i", "异常处理用于配置节点的错误处理逻辑，当API调用失败时可以设置如何处理错误")
        hint_icon3.setStyleSheet("font-size: 12px; color: white; font-weight: bold; background-color: #3498DB; border-radius: 8px; text-align: center; padding: 0px; line-height: 16px;")
        hint_icon3.setFixedSize(20, 20)
        
        exceptions_layout.addWidget(self.exceptions_toggle_button)
        exceptions_layout.addWidget(hint_icon3)
        layout.addLayout(exceptions_layout)
        
        # 异常处理区域
        self.exceptions_group = QWidget()
        exceptions_layout = QVBoxLayout(self.exceptions_group)
        # 设置布局为顶部对齐，避免垂直拉伸
        exceptions_layout.setAlignment(Qt.AlignTop)
        # 设置大小策略为最小化，根据内容自动调整高度
        self.exceptions_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        # 设置拉伸因子为0，避免异常处理区域被拉伸
        layout.addWidget(self.exceptions_group, 0)
        self.exceptions_group.hide()
        
        # 添加分割线
        separator3 = QWidget()
        separator3.setStyleSheet("height: 1px; background-color: #555555;")
        separator3.setFixedHeight(1)
        layout.addWidget(separator3)
        
        # 其他参数区域
        # 设置拉伸因子为0，避免参数区域被拉伸
        layout.addWidget(self.params_group, 0)
        
        # 填充空间
        layout.addStretch()
        
        # 将内容面板设置为滚动区域的widget
        scroll_area.setWidget(panel)
        
        return scroll_area
    
    def create_node_tree(self):
        """创建节点菜单树"""

        
        # 创建树部件
        tree_widget = QTreeWidget()
        tree_widget.setHeaderLabel("节点库")
        tree_widget.setStyleSheet("background-color: #2D2D2D; color: white; border: none;")
        
        # 启用拖动
        tree_widget.setDragEnabled(True)
        
        # 从节点管理器获取所有节点
        node_classes = node_manager.get_node_classes()
        
        # 按类别组织节点
        categories = {
            "控制节点": [],
            "数据节点": []
        }
        
        # 分类节点
        for node_name, node_class in node_classes.items():
            try:
                # 跳过StartNode，不允许用户创建新的开始节点
                if node_name == "StartNode":
                    continue
                    
                temp_node = node_class()
                node_title = temp_node.title
                del temp_node
                
                if node_name == "ForLoopNode":
                    categories["控制节点"].append((node_name, node_title))
                elif node_name in ["PrintNode", "CalculateNode", "TypeConvertNode"]:
                    categories["数据节点"].append((node_name, node_title))
                elif node_name == "FindImageNode":
                    categories["控制节点"].append((node_name, node_title))
                else:
                    # 外部节点默认添加到控制节点类别
                    categories["控制节点"].append((node_name, node_title))
            except:
                pass
        
        # 添加分类和节点到树
        for category, nodes in categories.items():
            if nodes:
                category_item = QTreeWidgetItem(tree_widget, [category])
                for node_name, node_title in nodes:
                    node_item = QTreeWidgetItem(category_item, [node_title])
                    node_item.setData(0, Qt.ItemDataRole.UserRole, node_name)
        
        # 展开所有节点
        tree_widget.expandAll()
        
        # 自定义拖动事件
        def startDrag(event):
            item = tree_widget.currentItem()
            if item and item.parent():
                node_type = item.data(0, Qt.ItemDataRole.UserRole)
                if node_type:
                    mimeData = QMimeData()
                    mimeData.setText(node_type)
                    drag = QDrag(tree_widget)
                    drag.setMimeData(mimeData)
                    drag.exec(Qt.DropAction.CopyAction)
        
        tree_widget.mouseMoveEvent = startDrag
        
        # 创建容器部件
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.addWidget(tree_widget)
        container.setStyleSheet("background-color: #2D2D2D;")
        
        return container
    
    def create_log_window(self):
        """创建日志窗口"""

        
        # 创建日志窗口部件
        self.log_widget = QWidget()
        log_layout = QVBoxLayout(self.log_widget)
        self.log_widget.setStyleSheet("background-color: #2D2D2D; color: white;")
        
        # 日志窗口标题栏（包含标题和收缩按钮）
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)
        
        # 收缩按钮
        self.log_toggle_btn = QPushButton(">")
        self.log_toggle_btn.setFixedSize(20, 20)
        self.log_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                font-size: 12px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:focus {
                outline: none;
            }
        """)
        self.log_toggle_btn.clicked.connect(self.toggle_log_window)
        title_layout.addWidget(self.log_toggle_btn)
        
        # 日志窗口标题
        log_title = QLabel("日志输出")
        log_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        title_layout.addWidget(log_title)
        
        # 弹簧
        title_layout.addStretch()
        
        # 搜索日志输入框
        self.log_search_input = QLineEdit()
        self.log_search_input.setPlaceholderText("搜索日志...")
        self.log_search_input.setStyleSheet("""
            QLineEdit {
                background-color: #3D3D3D;
                color: white;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 12px;
                max-width: 150px;
            }
        """)
        # 连接搜索信号
        self.log_search_input.textChanged.connect(self.on_log_search)
        title_layout.addWidget(self.log_search_input)
        
        # 自动滚动开关（使用滑动按钮）
        from UI组件.滑动按钮 import SwitchButton
        self.auto_scroll_btn = SwitchButton()
        self.auto_scroll_btn.setFixedSize(60, 20)
        self.auto_scroll_btn.setChecked(True)
        # 连接信号，确保状态变化时能正确处理
        self.auto_scroll_btn.toggled.connect(self.on_auto_scroll_toggled)
        title_layout.addWidget(self.auto_scroll_btn)
        
        # 自动滚动标签
        auto_scroll_label = QLabel("自动滚动")
        auto_scroll_label.setStyleSheet("font-size: 10px; color: white;")
        title_layout.addWidget(auto_scroll_label)
        
        # 清空按钮
        self.clear_log_btn = QPushButton("清空")
        self.clear_log_btn.setFixedSize(40, 20)
        self.clear_log_btn.setStyleSheet("""
            QPushButton {
                background-color: #3D3D3D;
                color: white;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:focus {
                outline: none;
            }
        """)
        self.clear_log_btn.clicked.connect(self.clear_log)
        title_layout.addWidget(self.clear_log_btn)
        
        log_layout.addWidget(title_bar)
        
        # 创建日志表格
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(3)
        self.log_table.setHorizontalHeaderLabels(["时间", "类型", "内容"])
        # 隐藏垂直和水平滚动条
        self.log_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.log_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 隐藏行号
        self.log_table.verticalHeader().setVisible(False)
        # 设置为整行选择模式
        self.log_table.setSelectionBehavior(QTableWidget.SelectRows)
        # 禁用编辑功能
        self.log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        # 设置样式，添加白色横线
        self.log_table.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: none;
                gridline-color: #1E1E1E;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: #E0E0E0;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #555555;
            }
            QTableWidget::item {
                border: none;
                border-bottom: 1px solid #333333;
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #1E90FF;
                color: white;
                border-bottom: 1px solid #1E90FF;
            }
        """)
        # 设置列宽
        self.log_table.setColumnWidth(0, 120)
        self.log_table.setColumnWidth(1, 80)
        self.log_table.horizontalHeader().setStretchLastSection(True)
        log_layout.addWidget(self.log_table)
        
        # 保存原始标准输出和标准错误
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # 创建UI日志系统
        import datetime
        
        class UILogStream:
            def __init__(self, table_widget, main_window):
                self.table_widget = table_widget
                self.main_window = main_window
                print(f"UILogStream 初始化，main_window: {main_window}")  # 添加调试信息
            
            def write(self, text):
                # 只显示用户需要看到的信息，如Print节点的输出和错误信息
                # 添加时间戳
                timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                log_text = text.strip()
                
                # 确定日志类型
                log_type = "信息"
                if "错误" in log_text or "Error" in log_text:
                    log_type = "错误"
                elif "提示" in log_text:
                    log_type = "提示"
                elif "开始" in log_text:
                    log_type = "开始"
                elif "结束" in log_text:
                    log_type = "结束"
                
                # 确保在主线程中执行UI操作
                from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                
                def add_log_entry():
                    try:
                        row_position = self.table_widget.rowCount()
                        self.table_widget.insertRow(row_position)
                        
                        # 设置时间单元格
                        time_item = QTableWidgetItem(timestamp)
                        time_item.setTextAlignment(Qt.AlignCenter)
                        self.table_widget.setItem(row_position, 0, time_item)
                        
                        # 设置类型单元格
                        type_item = QTableWidgetItem(log_type)
                        type_item.setTextAlignment(Qt.AlignCenter)
                        # 设置类型颜色
                        if log_type == "错误":
                            type_item.setForeground(QColor("#FF6B6B"))
                        elif log_type == "提示":
                            type_item.setForeground(QColor("#4ECDC4"))
                        elif log_type == "开始":
                            type_item.setForeground(QColor("#45B7D1"))
                        elif log_type == "结束":
                            type_item.setForeground(QColor("#96CEB4"))
                        self.table_widget.setItem(row_position, 1, type_item)
                        
                        # 设置内容单元格
                        content_item = QTableWidgetItem(log_text)
                        self.table_widget.setItem(row_position, 2, content_item)
                        
                        # 检查自动滚动状态并执行滚动
                        auto_scroll = False
                        if hasattr(self, 'main_window') and hasattr(self.main_window, 'auto_scroll_btn'):
                            auto_scroll = self.main_window.auto_scroll_btn.isChecked()
                        
                        if auto_scroll:
                            self.table_widget.scrollToBottom()
                    except Exception as e:
                        print(f"添加日志条目错误: {e}")
                
                QMetaObject.invokeMethod(self.table_widget, "clearFocus", Qt.QueuedConnection)
                QTimer.singleShot(10, add_log_entry)
            
            def flush(self):
                pass

        # 创建UI日志流实例
        self.ui_log_stream = UILogStream(self.log_table, self)
        
        # 设置UI日志流到日志管理器
        from 工具类.日志管理器 import log_manager
        log_manager.set_ui_log_stream(self.ui_log_stream)
        
        # 恢复标准输出和标准错误，让print输出到终端
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # 日志窗口收缩状态
        self.log_collapsed = False
        self.log_expanded_height = 270
        self.log_collapsed_height = 40  # 标题栏高度
    
    def toggle_log_window(self):
        """切换日志窗口收缩/展开状态"""
        if not self.log_collapsed:
            # 收缩：高度变窄，只显示标题栏
            self.log_widget.setFixedHeight(self.log_collapsed_height)
            self.log_table.setVisible(False)
            self.log_toggle_btn.setText("⌵")
        else:
            # 展开：高度恢复，显示完整内容
            self.log_widget.setFixedHeight(self.log_expanded_height)
            self.log_table.setVisible(True)
            self.log_toggle_btn.setText(">" )
        self.log_collapsed = not self.log_collapsed
    
    def clear_log(self):
        """清空日志内容"""
        if self.log_table:
            self.log_table.setRowCount(0)
    
    def on_auto_scroll_toggled(self, checked):
        """处理自动滚动按钮的状态变化"""
        # 打印状态变化，用于调试
        print(f"自动滚动按钮状态变化: {checked}")
        # 自动滚动状态变化时的处理逻辑
        # 这里可以添加额外的处理，比如保存设置等
        pass
    
    def on_log_search(self, text):
        """处理日志搜索"""
        # 获取搜索文本
        search_text = text.lower()
        
        # 遍历日志表格中的所有行
        for row in range(self.log_table.rowCount()):
            # 获取内容单元格
            content_item = self.log_table.item(row, 2)
            if content_item:
                content = content_item.text().lower()
                # 检查内容是否包含搜索文本
                if search_text in content:
                    # 显示行
                    self.log_table.setRowHidden(row, False)
                else:
                    # 隐藏行
                    self.log_table.setRowHidden(row, True)
    
    def on_selection_changed(self):
        """处理选中节点变化"""
        # 获取选中的节点
        selected_items = self.view.scene.selectedItems()
        node = None
        for item in selected_items:
            if hasattr(item, 'title') and hasattr(item, 'ports'):
                node = item
                break
        
        if node:
            # 检查是否重新选中同一个节点
            if hasattr(node, 'id') and node.id == self.current_selected_node_id:
                # 重新选中同一个节点，不需要更新属性面板
                return
            
            # 更新当前选中节点的ID
            self.current_selected_node_id = node.id
            self.selected_node = node
            # 更新当前在属性面板中显示的节点
            self.current_property_node = node
            # 更新属性面板
            self.update_property_panel(node)
        else:
            self.selected_node = None
    
    def add_param_input(self, label_text, input_widget):
        """添加参数输入框"""
        # 找到参数组
        params_group = self.property_panel.findChildren(QWidget)[2]  # 第三个子部件是参数组
        params_layout = params_group.layout()
        
        # 创建标签
        label = QLabel(label_text)
        label.setStyleSheet("margin-top: 10px;")
        params_layout.addWidget(label)
        
        # 创建输入框
        new_input = QLineEdit(input_widget.text())
        new_input.setStyleSheet("background-color: #3D3D3D; color: white; border: 1px solid #555555;")
        
        # 保存原始输入框的引用
        new_input.original_input = input_widget
        
        # 连接信号
        new_input.editingFinished.connect(lambda widget=new_input: self.update_node_param(widget))
        
        params_layout.addWidget(new_input)
        self.param_inputs.append(new_input)
    
    def update_node_position(self):
        """更新节点位置"""
        if not self.selected_node:
            return
        
        try:
            x = float(self.x_input.text())
            y = float(self.y_input.text())
            self.selected_node.setPos(x, y)
        except ValueError:
            pass
    
    def update_node_size(self):
        """更新节点尺寸"""
        if not self.selected_node:
            return
        
        try:
            width = int(self.width_input.text())
            height = int(self.height_input.text())
            self.selected_node.width = width
            self.selected_node.height = height
            # 触发重绘
            self.selected_node.update()
        except ValueError:
            pass
    
    def update_node_width(self, input_widget, node):
        """更新节点宽度"""
        if not node:
            return
        
        try:
            width = int(input_widget.text())
            # 确保宽度不小于最小值
            width = max(100, width)
            node.width = width
            # 触发重绘
            node.update()
            # 更新端口位置
            for port in node.ports:
                if port.port_type == 'output':
                    port.setPos(width, port.y())
        except ValueError:
            # 输入无效，恢复原始值
            input_widget.setText(str(node.width))
    
    def update_node_param(self, input_widget):
        """更新节点参数"""
        if not self.selected_node or not hasattr(input_widget, 'original_input'):
            return
        
        original_input = input_widget.original_input
        original_input.setText(input_widget.text())
    
    def update_property_panel(self, node):
        """更新属性面板，显示节点的最新属性"""
        if not node or not hasattr(node, 'variables'):
            return
        
        # 更新当前在属性面板中显示的节点
        self.current_property_node = node
        
        # 直接更新属性面板，避免调用on_node_selected导致循环
        variables = node.variables
        
        # 清空之前的参数输入框
        for input_widget in self.param_inputs:
            input_widget.hide()
            input_widget.deleteLater()
        self.param_inputs.clear()
        
        # 清空参数组的布局
        params_layout = self.params_group.layout()
        while params_layout.count() > 0:
            item = params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # 隐藏参数组，避免占用空间
        self.params_group.hide()
        
        # 清空输入变量组的布局
        while self.inputs_layout.count() > 0:
            item = self.inputs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                sub_layout = item.layout()
                while sub_layout.count() > 0:
                    sub_item = sub_layout.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                # 也删除子布局本身
                sub_layout.deleteLater()
        
        # 清空输出变量组的布局
        while self.outputs_layout.count() > 0:
            item = self.outputs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                sub_layout = item.layout()
                while sub_layout.count() > 0:
                    sub_item = sub_layout.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                # 也删除子布局本身
                sub_layout.deleteLater()
        
        # 显示属性面板
        self.property_panel.show()
        # 切换到属性面板选项卡
        self.right_tab_widget.setCurrentWidget(self.property_panel)
        
        # 只有当变量不为空时才更新属性面板
        if variables:
            # 更新节点标题
            self.title_label.setText(f"节点: {variables.get('title', '无')}")
            
            # 显示输入变量
            inputs = variables.get('inputs', [])
            if inputs:
                for input_var in inputs:
                    input_name = input_var.get('name', '未知')
                    input_value = input_var.get('value', '')
                    input_options = input_var.get('options', [])
                    
                    # 创建水平布局放置标签和提示图标
                    label_layout = QHBoxLayout()
                    label_layout.setAlignment(Qt.AlignLeft)
                    label_layout.setContentsMargins(0, 0, 0, 0)
                    label_layout.setSpacing(5)
                    
                    # 创建标签
                    label = QLabel(f"{input_name}:")
                    # 增强循环次数的视觉层级
                    if input_name == '循环次数':
                        label.setStyleSheet("font-weight: bold; font-size: 14px;")
                    label_layout.addWidget(label)
                    
                    # 添加提示图标
                    input_description = input_var.get('description', f"{input_name} 参数的说明")
                    hint_icon = HintLabel("i", input_description)
                    hint_icon.setStyleSheet("font-size: 12px; color: white; font-weight: bold; background-color: #3498DB; border-radius: 8px; text-align: center; padding: 0px; line-height: 16px;")
                    hint_icon.setFixedSize(16, 16)
                    label_layout.addWidget(hint_icon)
                    
                    # 添加到输入布局
                    self.inputs_layout.addLayout(label_layout)
                    
                    # 添加标签和输入框之间的间距
                    label_input_spacing = QWidget()
                    label_input_spacing.setFixedHeight(2)
                    self.inputs_layout.addWidget(label_input_spacing)
                    
                    # 根据展开状态决定是否显示
                    if not self.inputs_expanded:
                        label.hide()
                        hint_icon.hide()
                        label_input_spacing.hide()
                    
                    # 创建水平布局放置输入控件和变量选择按钮
                    input_widget = None
                    
                    # 特殊处理"是否点击"和"执行下一步操作"选项，使用滑动按钮
                    if input_name == '是否点击' or input_name == '执行下一步操作':
                        # 创建滑动按钮
                        input_widget = SwitchButton()
                        input_widget.setChecked(input_value == '是')
                        input_widget.setFixedSize(60, 28)
                        # 连接信号
                        def on_toggled(checked, name=input_name):
                            value = '是' if checked else '否'
                            print(f"{name}按钮状态变化: {checked} -> {value}")
                            self.update_input_variable(name, None, value)
                        input_widget.toggled.connect(on_toggled)
                        self.param_inputs.append(input_widget)
                    elif input_options:
                        # 创建下拉框
                        input_widget = QComboBox()
                        input_widget.addItems(input_options)
                        input_widget.setCurrentText(str(input_value))
                        input_widget.setStyleSheet("background-color: #3D3D3D; color: white; border: 1px solid #555555; padding: 4px;")
                        input_widget.setMaximumWidth(250)
                        input_widget.setMinimumHeight(28)
                        # 连接信号
                        input_widget.currentTextChanged.connect(
                            lambda text, name=input_name: self.update_input_variable(name, None, text)
                        )
                        self.param_inputs.append(input_widget)
                    else:
                        # 创建文本编辑框
                        input_widget = QTextEdit()
                        input_widget.setPlainText(str(input_value))
                        # 统一输入框颜色，保持一致
                        input_widget.setStyleSheet("background-color: #3D3D3D; color: white; border: 1px solid #555555; padding: 4px;")
                        input_widget.setMaximumWidth(250)
                        input_widget.setMinimumHeight(28)
                        input_widget.setMaximumHeight(28)
                        input_widget.setLineWrapMode(QTextEdit.NoWrap)
                        input_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                        input_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                        # 连接信号，使用textChanged并通过防抖处理避免每次按键都更新
                        input_widget.textChanged.connect(
                            lambda name=input_name, widget=input_widget: self.update_input_variable(name, widget)
                        )
                        # 连接文本变化信号用于高亮变量引用（保持实时更新）
                        input_widget.textChanged.connect(
                            lambda widget=input_widget: self.highlight_variable_references(widget)
                        )
                        self.param_inputs.append(input_widget)
                    
                    # 创建水平布局放置输入控件和按钮
                    input_layout = QHBoxLayout()
                    input_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    input_layout.setContentsMargins(0, 0, 0, 0)
                    input_layout.setSpacing(5)
                    
                    # 添加输入控件
                    input_layout.addWidget(input_widget)
                    
                    # 只有当有可输入的控件时才创建变量选择按钮
                    if input_name != '是否点击' and input_name != '点击方法' and input_name != '执行下一步操作':
                        # 创建变量选择按钮
                        var_button = QPushButton("◉")
                        var_button.setStyleSheet("background-color: #34495E; color: white; border: none; border-radius: 4px; padding: 0px; font-size: 12px;")
                        var_button.setFixedSize(28, 28)
                        # 连接信号
                        var_button.clicked.connect(
                            lambda checked, name=input_name, widget=input_widget: self.show_variable_menu(name, widget)
                        )
                        input_layout.addWidget(var_button)
                    
                    # 为图像名称输入框添加获取图像路径和截图按钮
                    if input_name == '图像名称':
                        # 创建获取图像路径按钮
                        browse_button = QPushButton("...")
                        browse_button.setStyleSheet("background-color: #2C3E50; color: white; border: none; border-radius: 4px; padding: 0px; font-size: 12px;")
                        browse_button.setFixedSize(28, 28)
                        # 连接信号
                        browse_button.clicked.connect(
                            lambda checked, widget=input_widget: self.browse_image_path(widget)
                        )
                        input_layout.addWidget(browse_button)
                        
                        # 创建截图按钮
                        screenshot_button = QPushButton("截图")
                        screenshot_button.setStyleSheet("background-color: #1ABC9C; color: white; border: none; border-radius: 4px; padding: 0px; font-size: 12px;")
                        screenshot_button.setFixedSize(28, 28)
                        # 连接信号
                        screenshot_button.clicked.connect(
                            lambda checked, widget=input_widget: self.take_screenshot(widget)
                        )
                        input_layout.addWidget(screenshot_button)
                    # 为范围输入框添加获取范围按钮
                    elif input_name == '搜索区域':
                        # 创建获取范围按钮
                        range_button = QPushButton("获取范围")
                        range_button.setStyleSheet("background-color: #9B59B6; color: white; border: none; border-radius: 4px; padding: 0px; font-size: 12px;")
                        range_button.setFixedSize(50, 28)
                        # 连接信号
                        range_button.clicked.connect(
                            lambda checked, widget=input_widget: self.get_range(widget)
                        )
                        input_layout.addWidget(range_button)
                    
                    # 直接将输入布局添加到输入组布局中，不使用容器widget
                    self.inputs_layout.addLayout(input_layout)
                    
                    # 根据展开状态决定是否显示
                    if not self.inputs_expanded:
                        # 隐藏布局中的所有控件
                        for i in range(input_layout.count()):
                            item = input_layout.itemAt(i)
                            if item.widget():
                                item.widget().hide()
                    
                    # 添加变量之间的间距（只有当不是最后一个参数时才添加）
                    if input_var != inputs[-1]:
                        var_spacing = QWidget()
                        var_spacing.setFixedHeight(8)
                        self.inputs_layout.addWidget(var_spacing)
                        
                        # 根据展开状态决定是否显示
                        if not self.inputs_expanded:
                            var_spacing.hide()
            
            # 根据展开状态设置输入组的可见性
            if self.inputs_expanded:
                self.inputs_group.show()
            else:
                self.inputs_group.hide()
            
            # 显示输出变量
            outputs = variables.get('outputs', [])
            if outputs:
                for output_var in outputs:
                    output_name = output_var.get('name', '未知')
                    output_value = output_var.get('value', '')
                    
                    # 创建水平布局放置标签和提示图标
                    label_layout = QHBoxLayout()
                    label_layout.setAlignment(Qt.AlignLeft)
                    label_layout.setContentsMargins(0, 0, 0, 0)
                    label_layout.setSpacing(5)
                    
                    # 创建标签
                    label = QLabel(f"{output_name}:")
                    label_layout.addWidget(label)
                    
                    # 添加提示图标
                    output_description = output_var.get('description', f"{output_name} 输出的说明")
                    hint_icon = HintLabel("i", output_description)
                    hint_icon.setStyleSheet("font-size: 12px; color: white; font-weight: bold; background-color: #1E90FF; border-radius: 8px; text-align: center; padding: 0px; line-height: 16px;")
                    hint_icon.setFixedSize(16, 16)
                    label_layout.addWidget(hint_icon)
                    
                    # 添加到输出布局
                    self.outputs_layout.addLayout(label_layout)
                    
                    # 添加标签和输入框之间的间距
                    label_input_spacing = QWidget()
                    label_input_spacing.setFixedHeight(4)
                    self.outputs_layout.addWidget(label_input_spacing)
                    
                    # 根据展开状态决定是否显示
                    if not self.outputs_expanded:
                        label.hide()
                        hint_icon.hide()
                        label_input_spacing.hide()
                    
                    # 创建只读输入框显示输出值
                    output_widget = QLineEdit(str(output_value))
                    output_widget.setReadOnly(True)
                    output_widget.setStyleSheet("background-color: #2D2D2D; color: #888888; border: 1px solid #444444; padding: 4px;")
                    output_widget.setMaximumWidth(250)
                    output_widget.setMinimumHeight(28)
                    self.outputs_layout.addWidget(output_widget)
                    self.param_inputs.append(output_widget)
                    
                    # 根据展开状态决定是否显示
                    if not self.outputs_expanded:
                        output_widget.hide()
                    
                    # 添加变量之间的间距
                    var_spacing = QWidget()
                    var_spacing.setFixedHeight(8)
                    self.outputs_layout.addWidget(var_spacing)
                    
                    # 根据展开状态决定是否显示
                    if not self.outputs_expanded:
                        var_spacing.hide()
            
            # 根据展开状态设置输出组的可见性
            if self.outputs_expanded:
                self.outputs_group.show()
            else:
                self.outputs_group.hide()
    
    @Slot(dict)
    def on_node_selected(self, variables):
        """处理节点选中信号"""
        try:
            # 确保variables是字典类型
            if hasattr(variables, 'toPython'):
                variables = variables.toPython()
            elif not isinstance(variables, dict):
                variables = {}
            
            # 找到对应的节点
            node = None
            for item in self.view.scene.items():
                if hasattr(item, 'id') and item.id == variables.get('id'):
                    node = item
                    break
            
            if node:
                # 检查是否重新选中同一个节点
                if hasattr(node, 'id') and node.id == self.current_selected_node_id:
                    # 重新选中同一个节点，不需要更新属性面板
                    return
                
                # 更新当前选中节点的ID
                self.current_selected_node_id = node.id
                self.selected_node = node
                # 更新当前在属性面板中显示的节点
                self.current_property_node = node
                # 先断开之前的连接，避免信号循环
                try:
                    # 检查信号是否已连接
                    if node.properties_changed.isConnected(self.update_property_panel):
                        node.properties_changed.disconnect(self.update_property_panel)
                except:
                    pass
                # 先更新变量
                if hasattr(node, 'variables'):
                    node.update_variables()
                # 连接节点的属性变化信号
                node.properties_changed.connect(self.update_property_panel)
                # 更新属性面板
                self.update_property_panel(node)
        except Exception as e:
            print(f"处理节点选中事件时出错: {e}")
            # 显示属性面板
            self.property_panel.show()
            # 切换到属性面板选项卡
            self.right_tab_widget.setCurrentWidget(self.property_panel)
        

    
    def _handle_input_timeout(self):
        """处理防抖超时，更新所有待处理的输入变量"""
        if not self.pending_inputs:
            return
        
        # 处理所有待处理的输入
        for input_name, (widget, text_value) in self.pending_inputs.items():
            self._update_input_variable_internal(input_name, widget, text_value)
        
        # 清空待处理输入
        self.pending_inputs.clear()
    
    def _update_input_variable_internal(self, input_name, input_widget, text_value=None):
        """内部更新输入变量的方法"""
        # 使用当前在属性面板中显示的节点，而不是选中的节点
        node = self.current_property_node
        if not node:
            return
        
        # 获取输入值
        if text_value is not None:
            value = text_value.strip()
        else:
            # 检查控件类型
            if isinstance(input_widget, QTextEdit):
                value = input_widget.toPlainText().strip()
            else:
                value = input_widget.text().strip()
        
        # 无论值是否为空，都更新变量
        # 更新variables中的值
        inputs = node.variables.get('inputs', [])
        for input_var in inputs:
            if input_var.get('name') == input_name:
                input_var['value'] = value
                break
        
        # 保存更新后的输入变量
        node.variables['inputs'] = inputs
        
        # 调用节点的update_variables方法，确保节点内部状态得到更新
        node.update_variables()
        
        # 触发节点重绘
        node.update()
    
    def update_input_variable(self, input_name, input_widget, text_value=None):
        """更新输入变量（带防抖）"""
        # 存储待处理的输入
        self.pending_inputs[input_name] = (input_widget, text_value)
        
        # 对于点击方法、是否点击和执行下一步操作选项，立即更新属性面板，不需要防抖
        if input_name == '点击方法' or input_name == '是否点击' or input_name == '执行下一步操作':
            # 立即处理输入
            self._update_input_variable_internal(input_name, input_widget, text_value)
            # 清空待处理输入
            if input_name in self.pending_inputs:
                del self.pending_inputs[input_name]
            # 更新属性面板
            if self.current_property_node:
                self.update_property_panel(self.current_property_node)
        else:
            # 启动或重启防抖定时器（300毫秒）
            self.input_timer.start(300)
    
    def highlight_variable_references(self, input_widget):
        """高亮显示变量引用"""
        if not isinstance(input_widget, QTextEdit):
            return
        
        # 暂时断开信号，避免递归
        input_widget.blockSignals(True)
        
        try:
            # 获取文本
            text = input_widget.toPlainText()
            
            # 查找所有变量引用格式 ${node_id.variable_name}
            matches = list(re.finditer(r'\$\{([^}]+)\}', text))
            
            # 为每个变量引用设置颜色
            for match in matches:
                start = match.start()
                end = match.end()
                
                # 创建新的光标
                cursor = input_widget.textCursor()
                # 设置光标位置
                cursor.setPosition(start)
                # 使用正确的MoveMode枚举值
                cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
                
                # 设置格式
                char_format = QTextCharFormat()
                char_format.setForeground(QColor('#FFD700'))  # 金色
                cursor.setCharFormat(char_format)
                
        except Exception as e:
            print(f"高亮变量引用时出错: {e}")
        finally:
            # 重新连接信号
            input_widget.blockSignals(False)
    
    def show_variable_menu(self, input_name, input_widget):
        """显示变量选择菜单"""
        if not self.selected_node:
            return
        
        # 创建菜单
        menu = QMenu(self)
        
        # 获取所有可用的变量
        # 1. 获取当前节点之前的所有依赖节点
        def get_all_dependencies(node):
            """递归获取所有依赖节点"""
            dependencies = set()
            if hasattr(node, 'dependencies'):
                for dep in node.dependencies:
                    # 检查节点是否仍然存在于场景中
                    if dep and hasattr(dep, 'scene') and dep.scene() is not None:
                        dependencies.add(dep)
                        dependencies.update(get_all_dependencies(dep))
            return dependencies
        
        # 获取当前节点的所有依赖节点
        dependency_nodes = get_all_dependencies(self.selected_node)
        
        # 2. 收集所有依赖节点的输出变量
        variables = []
        for node in dependency_nodes:
            if hasattr(node, 'variables'):
                outputs = node.variables.get('outputs', [])
                for output in outputs:
                    var_name = output.get('name', '未知')
                    var_value = output.get('value', '')
                    # 生成简洁的变量名格式，如"cn_in3.结果"
                    # 提取节点标题中的类型缩写和ID
                    import re
                    match = re.search(r'\(([^_]+)_id:(\d+)\)', node.title)
                    if match:
                        node_abbr = match.group(1)
                        node_id = match.group(2)
                        # 生成简洁的变量名
                        short_node_name = f"{node_abbr}{node_id}"
                    else:
                        # 如果无法提取，使用节点标题的前几个字符
                        short_node_name = node.title[:5]
                    # 添加完整变量名（简洁节点名.变量名）
                    full_var_name = f"{short_node_name}.{var_name}"
                    # 显示友好的变量名（节点标题: 变量名）
                    display_name = f"{node.title}: {var_name}"
                    variables.append((node.title, full_var_name, display_name, var_value))
        
        # 3. 添加系统变量
        system_vars = [
            ('系统变量', 'current_time', 'current_time', '当前时间'),
            ('系统变量', 'current_date', 'current_date', '当前日期'),
        ]
        variables.extend(system_vars)
        
        # 4. 按类别组织菜单
        categories = {}
        for node_title, full_var_name, display_name, var_value in variables:
            if node_title not in categories:
                categories[node_title] = []
            categories[node_title].append((full_var_name, display_name, var_value))
        
        # 5. 添加菜单项
        for category, vars in categories.items():
            category_menu = QMenu(category, self)
            for full_var_name, display_name, var_value in vars:
                action = QAction(f"{display_name}", self)
                action.triggered.connect(
                    lambda checked, name=full_var_name: self.select_variable(input_widget, name)
                )
                category_menu.addAction(action)
            menu.addMenu(category_menu)
        
        # 6. 显示菜单
        if menu.actions():
            menu.exec_(input_widget.mapToGlobal(input_widget.rect().bottomRight()))
    
    def select_variable(self, input_widget, variable_name):
        """选择变量并填充到输入框"""
        variable_reference = f"{{{variable_name}}}"
        if isinstance(input_widget, QLineEdit):
            input_widget.setText(variable_reference)
        elif isinstance(input_widget, QTextEdit):
            input_widget.setPlainText(variable_reference)
        elif isinstance(input_widget, QComboBox):
            # 检查下拉框中是否已有该变量
            if input_widget.findText(variable_reference) == -1:
                input_widget.addItem(variable_reference)
            input_widget.setCurrentText(variable_reference)
    
    def browse_image_path(self, input_widget):
        """浏览图像路径"""
        from PySide6.QtWidgets import QFileDialog
        import os
        from pathlib import Path
        
        # 获取程序所在目录的相对路径
        app_dir = Path(__file__).parent.parent
        image_folder = app_dir / "脚本" / "Pic"
        
        # 确保图片文件夹存在
        image_folder.mkdir(parents=True, exist_ok=True)
        
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图像文件",
            str(image_folder),
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            # 检查文件是否在默认图片目录中
            from pathlib import Path
            app_dir = Path(__file__).parent.parent
            image_folder = app_dir / "脚本" / "Pic"
            
            # 转换为Path对象进行比较
            file_path_obj = Path(file_path)
            image_folder_obj = image_folder.resolve()
            
            # 如果文件在默认图片目录中，只使用文件名
            if image_folder_obj in file_path_obj.parents or file_path_obj.parent == image_folder_obj:
                file_name = file_path_obj.name
                display_path = file_name
            else:
                # 如果是外部文件，使用完整路径
                display_path = file_path
            
            # 设置到输入框
            if isinstance(input_widget, QLineEdit):
                input_widget.setText(display_path)
            elif isinstance(input_widget, QTextEdit):
                input_widget.setPlainText(display_path)
            elif isinstance(input_widget, QComboBox):
                # 检查下拉框中是否已有该路径
                if input_widget.findText(display_path) == -1:
                    input_widget.addItem(display_path)
                input_widget.setCurrentText(display_path)
    
    def take_screenshot(self, input_widget):
        """截图并保存"""
        import os
        import sys
        from PySide6.QtWidgets import QApplication
        from UI组件.截图 import ScreenshotWindow
        
        # 隐藏主窗口
        self.hide()
        # 确保主窗口被隐藏
        QApplication.processEvents()
        
        # 创建截图窗口
        screenshot_window = ScreenshotWindow()
        # 使用exec_()来模态显示，等待窗口关闭
        screenshot_window.exec_()
        
        # 显示主窗口
        self.show()
        
        # 检查是否保存了截图
        screenshot_path = screenshot_window.saved_file_name
        if screenshot_path and os.path.exists(screenshot_path):
            # 获取程序所在目录的相对路径
            from pathlib import Path
            app_dir = Path(__file__).parent.parent
            target_dir = app_dir / "脚本" / "Pic"
            # 确保目录存在
            target_dir.mkdir(parents=True, exist_ok=True)
            # 目标文件路径
            target_path = target_dir / os.path.basename(screenshot_path)
            # 移动文件
            import shutil
            shutil.move(screenshot_path, target_path)
            # 设置到输入框
            file_name = os.path.basename(target_path)
            if isinstance(input_widget, QLineEdit):
                input_widget.setText(file_name)
            elif isinstance(input_widget, QTextEdit):
                input_widget.setPlainText(file_name)
            elif isinstance(input_widget, QComboBox):
                # 检查下拉框中是否已有该文件名
                if input_widget.findText(file_name) == -1:
                    input_widget.addItem(file_name)
                input_widget.setCurrentText(file_name)
    
    def load_saved_nodes(self):
        """加载保存的节点内容"""
        try:
            # 从固定路径加载
            from pathlib import Path
            app_dir = Path(__file__).parent.parent
            file_path = app_dir / "nodes.json"
            
            if file_path.exists():
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    graph_data = json.load(f)
                
                # 加载节点
                all_nodes = []
                
                for node_data in graph_data.get('nodes', []):
                    node_type = node_data.get('type')
                    
                    # 处理StartNode
                    if node_type == 'StartNode':
                        # 加载StartNode的属性
                        if 'variables' in node_data:
                            self.start_node.variables = node_data['variables']
                            # 调用update_variables确保节点内部状态同步
                            self.start_node.update_variables()
                        # 加载StartNode的位置和尺寸
                        if 'pos' in node_data:
                            pos = node_data['pos']
                            self.start_node.setPos(pos['x'], pos['y'])
                        if 'width' in node_data:
                            self.start_node.width = node_data['width']
                        if 'height' in node_data:
                            self.start_node.height = node_data['height']
                        # 添加到视图的nodes字典中
                        if self.start_node.id not in self.view.nodes:
                            self.view.nodes[self.start_node.id] = self.start_node
                            # 连接信号
                            self.start_node.delete_requested.connect(self.view.delete_node)
                            self.start_node.copy_requested.connect(self.view.handle_copy_node)
                            self.start_node.edit_settings_requested.connect(self.view.edit_node_settings)
                            self.start_node.card_clicked.connect(self.view.handle_card_clicked)
                        # 添加到all_nodes列表
                        all_nodes.append(self.start_node)
                    else:
                        # 使用节点管理器创建节点
                        node = node_manager.create_node(node_type)
                        if not node:
                            continue
                        
                        # 设置节点属性 - 使用保存的variables属性
                        if 'variables' in node_data:
                            node.variables = node_data['variables']
                            # 调用update_variables确保节点内部状态同步
                            node.update_variables()
                        
                        # 设置位置和尺寸
                        pos = node_data.get('pos', {'x': 100, 'y': 100})
                        node.setPos(pos['x'], pos['y'])
                        node.width = node_data.get('width', 200)
                        node.height = node_data.get('height', 60)
                        self.view.scene.addItem(node)
                        # 添加到视图的nodes字典中
                        self.view.nodes[node.id] = node
                        # 连接信号
                        node.delete_requested.connect(self.view.delete_node)
                        node.copy_requested.connect(self.view.handle_copy_node)
                        node.edit_settings_requested.connect(self.view.edit_node_settings)
                        node.card_clicked.connect(self.view.handle_card_clicked)
                        all_nodes.append(node)
                
                # 加载连线
                for connection_data in graph_data.get('connections', []):
                    if len(all_nodes) > connection_data['start_node_index'] and len(all_nodes) > connection_data['end_node_index']:
                        start_node = all_nodes[connection_data['start_node_index']]
                        end_node = all_nodes[connection_data['end_node_index']]
                        
                        if len(start_node.ports) > connection_data['start_port_index'] and len(end_node.ports) > connection_data['end_port_index']:
                            start_port = start_node.ports[connection_data['start_port_index']]
                            end_port = end_node.ports[connection_data['end_port_index']]
                            connection = Connection(start_port, end_port)
                            self.view.scene.addItem(connection)
                
                print(f"节点内容已自动加载自: {file_path}")
            else:
                print("没有找到保存的节点内容，使用默认配置")
        except Exception as e:
            print(f"加载节点内容失败: {e}")
    
    def closeEvent(self, event):
        """窗口关闭事件，保存节点内容"""
        # 停止所有正在运行的节点线程
        self.should_stop = True
        self.is_executing = False
        if hasattr(self, 'current_context') and self.current_context:
            self.current_context.set_stop_requested(True)
        
        # 等待所有节点线程结束
        import time
        for item in self.view.scene.items():
            if hasattr(item, 'thread') and item.thread and item.thread.isRunning():
                item.thread.stop()
                item.thread.wait(1000)  # 最多等待1秒
        time.sleep(0.2)  # 等待线程完全结束
        
        # 停止pynput键盘监听
        if hasattr(self, 'keyboard_listener') and self.keyboard_listener:
            self.keyboard_listener.stop()
            print("键盘监听已停止")
        
        # 保存节点内容
        try:
            # 自动保存到固定路径
            file_path = Path("nodes.json")
            
            # 收集节点数据
            nodes = []
            for item in self.view.scene.items():
                if hasattr(item, 'title') and hasattr(item, 'ports'):
                    # 是节点
                    node_data = {
                        'type': item.__class__.__name__,
                        'title': item.title,
                        'pos': {'x': item.x(), 'y': item.y()},
                        'width': item.width,
                        'height': item.height
                    }
                    
                    # 收集端口信息
                    ports = []
                    for port in item.ports:
                        port_data = {
                            'port_type': port.port_type,
                            'pos': {'x': port.x(), 'y': port.y()}
                        }
                        ports.append(port_data)
                    node_data['ports'] = ports
                    
                    # 收集参数 - 使用节点的variables属性保存所有属性
                    if hasattr(item, 'variables'):
                        node_data['variables'] = item.variables
                    
                    nodes.append(node_data)
            
            # 收集连线数据
            connections = []
            for item in self.view.scene.items():
                if hasattr(item, 'start_port') and hasattr(item, 'end_port'):
                    # 是连线
                    if item.end_port:
                        # 找到开始端口和结束端口所属的节点
                        start_node = None
                        end_node = None
                        for node_item in self.view.scene.items():
                            if hasattr(node_item, 'ports'):
                                if item.start_port in node_item.ports:
                                    start_node = node_item
                                if item.end_port in node_item.ports:
                                    end_node = node_item
                        
                        if start_node and end_node:
                            # 找到节点在nodes列表中的索引
                            start_node_index = next((i for i, n in enumerate(nodes) if n['type'] == start_node.__class__.__name__ and n['pos']['x'] == start_node.x() and n['pos']['y'] == start_node.y()), -1)
                            end_node_index = next((i for i, n in enumerate(nodes) if n['type'] == end_node.__class__.__name__ and n['pos']['x'] == end_node.x() and n['pos']['y'] == end_node.y()), -1)
                            
                            if start_node_index != -1 and end_node_index != -1:
                                connection_data = {
                                    'start_node_index': start_node_index,
                                    'start_port_index': start_node.ports.index(item.start_port),
                                    'end_node_index': end_node_index,
                                    'end_port_index': end_node.ports.index(item.end_port)
                                }
                                connections.append(connection_data)
            
            # 保存数据
            graph_data = {
                'nodes': nodes,
                'connections': connections
            }
            
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
            print(f"节点内容已自动保存到: {file_path}")
        except Exception as e:
            print(f"保存节点内容失败: {e}")
        
        # 恢复标准输出和标准错误
        if hasattr(self, 'original_stdout'):
            sys.stdout = self.original_stdout
        if hasattr(self, 'original_stderr'):
            sys.stderr = self.original_stderr
        event.accept()
    
    def get_range(self, input_widget):
        """获取范围坐标"""
        import sys
        from PySide6.QtWidgets import QApplication
        from UI组件.截图 import ScreenshotWindow
        
        # 隐藏主窗口
        self.hide()
        # 确保主窗口被隐藏
        QApplication.processEvents()
        
        # 创建截图窗口，设置为range模式
        screenshot_window = ScreenshotWindow(mode="range")
        # 使用exec_()来模态显示，等待窗口关闭
        screenshot_window.exec_()
        
        # 显示主窗口
        self.show()
        
        # 获取选中的范围
        rect = screenshot_window.rect
        if rect.isValid():
            # 格式化范围为"x,y,width,height"
            range_str = f"{rect.x()},{rect.y()},{rect.width()},{rect.height()}"
            # 设置到输入框
            if isinstance(input_widget, QLineEdit):
                input_widget.setText(range_str)
            elif isinstance(input_widget, QTextEdit):
                input_widget.setPlainText(range_str)
            elif isinstance(input_widget, QComboBox):
                # 检查下拉框中是否已有该范围
                if input_widget.findText(range_str) == -1:
                    input_widget.addItem(range_str)
                input_widget.setCurrentText(range_str)
        
    def update_node_variable(self, key, input_widget, text_value=None):
        """更新节点变量"""
        if not self.selected_node:
            return
        
        # 获取值
        if text_value is not None:
            value = text_value.strip() if isinstance(text_value, str) else text_value
        else:
            if isinstance(input_widget, QTextEdit):
                value = input_widget.toPlainText().strip()
            else:
                value = input_widget.text().strip()
        
        # 尝试转换为适当的类型
        try:
            if key in ['start_value', 'end_value', 'step_value', 'input1_value', 'input2_value']:
                # 数字类型
                value = int(value)
            elif key in ['position']:
                # 位置字典
                value = json.loads(value)
        except:
            pass
        
        self.selected_node.variables[key] = value
    
    def update_input_variable_name(self, old_name, input_widget):
        """更新输入变量名"""
        if not self.selected_node:
            return
        
        # 获取新的变量名
        new_name = input_widget.text()
        
        # 更新输入变量名
        inputs = self.selected_node.variables.get('inputs', [])
        for input_var in inputs:
            if input_var.get('name') == old_name:
                input_var['name'] = new_name
                break
        
        # 保存更新后的输入变量
        self.selected_node.variables['inputs'] = inputs
        
        # 调用节点的update_variables方法，确保节点内部状态得到更新
        self.selected_node.update_variables()
        
        # 触发节点重绘
        self.selected_node.update()
    
    def update_output_variable_name(self, old_name, input_widget):
        """更新输出变量名"""
        if not self.selected_node:
            return
        
        # 获取新的变量名
        new_name = input_widget.text()
        
        # 更新输出变量名
        outputs = self.selected_node.variables.get('outputs', [])
        for output_var in outputs:
            if output_var.get('name') == old_name:
                output_var['name'] = new_name
                break
        
        # 保存更新后的输出变量
        self.selected_node.variables['outputs'] = outputs
        
        # 调用节点的update_variables方法，确保节点内部状态得到更新
        self.selected_node.update_variables()
        
        # 触发节点重绘
        self.selected_node.update()
    
    def toggle_inputs(self):
        """切换输入参数的显示/隐藏"""
        self.inputs_expanded = not self.inputs_expanded
        if self.inputs_expanded:
            self.inputs_toggle_button.setText("▼ 输入")
            # 显示输入参数
            self.inputs_group.show()
            # 显示输入组内的所有控件
            for i in range(self.inputs_layout.count()):
                item = self.inputs_layout.itemAt(i)
                if item.widget():
                    item.widget().show()
                elif item.layout():
                    for j in range(item.layout().count()):
                        sub_item = item.layout().itemAt(j)
                        if sub_item.widget():
                            sub_item.widget().show()
        else:
            self.inputs_toggle_button.setText("▶ 输入")
            # 隐藏输入参数
            self.inputs_group.hide()
            # 隐藏输入组内的所有控件
            for i in range(self.inputs_layout.count()):
                item = self.inputs_layout.itemAt(i)
                if item.widget():
                    item.widget().hide()
                elif item.layout():
                    for j in range(item.layout().count()):
                        sub_item = item.layout().itemAt(j)
                        if sub_item.widget():
                            sub_item.widget().hide()
    
    def toggle_outputs(self):
        """切换输出结果的显示/隐藏"""
        self.outputs_expanded = not self.outputs_expanded
        if self.outputs_expanded:
            self.outputs_toggle_button.setText("▼ 输出")
            # 显示输出结果
            self.outputs_group.show()
            # 显示输出组内的所有控件
            for i in range(self.outputs_layout.count()):
                item = self.outputs_layout.itemAt(i)
                if item.widget():
                    item.widget().show()
                elif item.layout():
                    for j in range(item.layout().count()):
                        sub_item = item.layout().itemAt(j)
                        if sub_item.widget():
                            sub_item.widget().show()
        else:
            self.outputs_toggle_button.setText("▶ 输出")
            # 隐藏输出结果
            self.outputs_group.hide()
            # 隐藏输出组内的所有控件
            for i in range(self.outputs_layout.count()):
                item = self.outputs_layout.itemAt(i)
                if item.widget():
                    item.widget().hide()
                elif item.layout():
                    for j in range(item.layout().count()):
                        sub_item = item.layout().itemAt(j)
                        if sub_item.widget():
                            sub_item.widget().hide()
    
    def toggle_exceptions(self):
        """切换异常处理的显示/隐藏"""
        self.exceptions_expanded = not self.exceptions_expanded
        if self.exceptions_expanded:
            self.exceptions_toggle_button.setText("▼ 异常处理")
            # 显示异常处理
            self.exceptions_group.show()
        else:
            self.exceptions_toggle_button.setText("▶ 异常处理")
            # 隐藏异常处理
            self.exceptions_group.hide()
    
    def on_input_item_changed(self, item, column):
        """处理输入变量项的编辑事件"""
        if not self.selected_node:
            return
        
        # 跳过根节点
        if not item.parent():
            return
        
        # 获取项的索引（子节点索引）
        index = item.parent().indexOfChild(item)
        
        # 根据列索引更新不同的属性
        if column == 0:  # 变量名
            # 获取新的变量名
            new_name = item.text(0)
            
            # 更新对应的输入变量名称
            inputs = self.selected_node.variables.get('inputs', [])
            if index < len(inputs):
                inputs[index]['name'] = new_name
        elif column == 2:  # 值
            # 获取新的值
            new_value = item.text(2)
            
            # 更新对应的输入变量值
            inputs = self.selected_node.variables.get('inputs', [])
            if index < len(inputs):
                inputs[index]['value'] = new_value
        
        # 保存更新后的输入变量
        self.selected_node.variables['inputs'] = inputs
        
        # 调用节点的update_variables方法，确保节点内部状态得到更新
        self.selected_node.update_variables()
        
        # 触发节点重绘
        self.selected_node.update()
    
    def on_output_item_changed(self, item, column):
        """处理输出变量项的编辑事件"""
        if not self.selected_node:
            return
        
        # 跳过根节点
        if not item.parent():
            return
        
        # 只处理变量名列的编辑
        if column == 0:
            # 获取项的索引（子节点索引）
            index = item.parent().indexOfChild(item)
            
            # 获取新的变量名
            new_name = item.text(0)
            
            # 更新对应的输出变量名称
            outputs = self.selected_node.variables.get('outputs', [])
            if index < len(outputs):
                outputs[index]['name'] = new_name
            
            # 保存更新后的输出变量
            self.selected_node.variables['outputs'] = outputs
            
            # 调用节点的update_variables方法，确保节点内部状态得到更新
            self.selected_node.update_variables()
            
            # 触发节点重绘
            self.selected_node.update()
    
    def execute_all(self):
        """执行所有节点，基于依赖图的拓扑排序执行（ComfyUI模式）"""
        # 如果正在执行中，不重复执行
        if self.is_executing:
            print("正在执行中，忽略重复运行请求")
            return
        
        # 设置执行标志
        self.is_executing = True
        self.should_stop = False
        
        # 显示停止按钮，隐藏运行按钮
        self.run_button.hide()
        self.stop_button.show()
        QApplication.processEvents()
        
        # 保存当前选中节点的输入值
        if self.selected_node:
            # 直接遍历所有输入控件，获取它们的值，确保无论是否触发了信号，都能获取到最新的值
            inputs = self.selected_node.variables.get('inputs', [])
            # 创建一个字典来映射输入变量名到值
            input_values = {}
            for i, input_widget in enumerate(self.param_inputs):
                if not hasattr(input_widget, 'original_input'):  # 只处理输入变量输入框或下拉框
                    if i < len(inputs):
                        input_name = inputs[i].get('name')
                        if input_name:
                            if isinstance(input_widget, QLineEdit):
                                value = input_widget.text().strip()
                            elif isinstance(input_widget, QComboBox):
                                value = input_widget.currentText().strip()
                            elif isinstance(input_widget, QTextEdit):
                                value = input_widget.toPlainText().strip()
                            elif isinstance(input_widget, SwitchButton):
                                value = '是' if input_widget.isChecked() else '否'
                            else:
                                value = ''
                            input_values[input_name] = value
            # 更新输入变量
            for input_var in inputs:
                input_name = input_var.get('name')
                if input_name in input_values:
                    input_var['value'] = input_values[input_name]
            # 保存更新后的输入变量
            self.selected_node.variables['inputs'] = inputs
            # 调用节点的update_variables方法，确保节点内部状态得到更新
            self.selected_node.update_variables()
            # 触发节点重绘
            self.selected_node.update()
        
        # 收集所有节点
        all_nodes = []
        nodes_dict = {}
        for item in self.view.scene.items():
            if hasattr(item, 'ports') and hasattr(item, 'execute'):
                all_nodes.append(item)
                nodes_dict[item.id] = item
        
        # 重置所有节点的执行状态和选中状态
        for node in all_nodes:
            node.reset_execution_status()
            # 设置执行标记
            node.executed = False
            # 取消选中状态
            node.is_selected = False
            node.setSelected(False)
            # 触发重绘
            node.update()
        
        # 取消所有连线的选中状态
        for item in self.view.scene.items():
            if hasattr(item, 'is_selected') and not (hasattr(item, 'ports') and hasattr(item, 'execute')):
                item.is_selected = False
                item.update()
        
        # 创建上下文对象
        context = Context()
        context.set_stop_requested(False)
        # 保存当前上下文对象
        self.current_context = context
        
        # 找到StartNode
        start_node = None
        for node in all_nodes:
            if node.__class__.__name__ == 'StartNode':
                start_node = node
                break
        
        if not start_node:
            # 如果没有StartNode，直接返回
            return
        
        # 收集StartNode及其下游节点
        def collect_downstream_nodes(node):
            nodes = set()
            nodes.add(node)
            # 遍历所有输出端口
            for port in node.ports:
                if port.port_type == "output":
                    # 确保port.connections存在
                    connections = getattr(port, 'connections', [])
                    for connection in connections:
                        if connection and hasattr(connection, 'end_port') and connection.end_port:
                            end_node = connection.end_port.parentItem()
                            if end_node and hasattr(end_node, 'execute') and end_node not in nodes:
                                nodes.update(collect_downstream_nodes(end_node))
            return nodes
        
        executable_nodes_set = collect_downstream_nodes(start_node)
        executable_nodes = list(executable_nodes_set)
        
        # 构建依赖图
        dependency_graph = {}
        for node in executable_nodes:
            # 确保node.dependencies存在
            dependencies = getattr(node, 'dependencies', [])
            dependency_graph[node.id] = [dep.id for dep in dependencies if dep and hasattr(dep, 'id')]
        
        # 拓扑排序
        executed_nodes = set()
        
        while True:
            # 找到所有没有未执行依赖的节点
            current_executable = []
            for node in executable_nodes_set:
                # 检查是否已经执行过
                if hasattr(node, 'executed') and node.executed:
                    print(f"拓扑排序跳过已执行的节点: {node.title} (id: {node.id})")
                    executed_nodes.add(node.id)
                    continue
                    
                if node.id not in executed_nodes:
                    # 检查所有依赖是否已执行
                    all_deps_executed = True
                    # 确保节点ID在依赖图中
                    if node.id in dependency_graph:
                        for dep_id in dependency_graph[node.id]:
                            if dep_id not in executed_nodes:
                                all_deps_executed = False
                                break
                    else:
                        # 如果节点不在依赖图中，说明它没有依赖
                        all_deps_executed = True
                    if all_deps_executed:
                        current_executable.append(node)
            
            if not current_executable:
                # 没有可执行的节点，结束执行
                break
            
            # 执行这些节点，实现走马灯效果
            for node in current_executable:
                # 检查是否应该停止执行
                if self.should_stop:
                    print("执行被用户停止")
                    # 设置上下文的停止标志
                    context.set_stop_requested(True)
                    # 重置执行标志
                    self.is_executing = False
                    return
                
                # 检查是否已经执行过
                if hasattr(node, 'executed') and node.executed:
                    # 打印调试信息
                    print(f"跳过已执行的节点: {node.title} (id: {node.id})")
                    continue
                
                # 检查是否是循环节点内部的执行（快速模式）
                is_fast_mode = hasattr(context, 'is_inside_loop') and context.is_inside_loop
                
                if not is_fast_mode:
                    # 正常执行模式，显示高亮效果
                    # 执行前高亮
                    node.flash()
                    # 强制重绘
                    node.update()
                    # 处理事件，确保高亮显示
                    QApplication.processEvents()
                    # 短暂延迟，以便用户能看到高亮效果
                    import time
                    time.sleep(0.03)
                
                # 执行节点
                node.execute(context, nodes_dict)
                # 标记为已执行
                node.executed = True
                
                if not is_fast_mode:
                    # 正常执行模式，取消高亮
                    # 执行后取消高亮
                    node.stop_flash()
                    node.update()
                    QApplication.processEvents()
                
                # 检查执行状态，如果出错则停止执行
                if node.execution_status == "error":
                    return
                executed_nodes.add(node.id)
        
        # 执行完成后，更新当前选中节点的属性面板
        if self.selected_node:
            self.update_property_panel(self.selected_node)
        
        # 恢复运行按钮，隐藏停止按钮
        self.run_button.show()
        self.stop_button.hide()
        QApplication.processEvents()
        
        # 重置执行标志
        self.is_executing = False
        # 清空当前上下文对象
        self.current_context = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())