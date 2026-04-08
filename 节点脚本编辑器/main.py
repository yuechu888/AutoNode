import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from UI组件.主界面 import MainWindow



if __name__ == "__main__":
    
    # 设置DPI感知，避免DPI警告
    try:
        from PySide6.QtCore import Qt
        # 尝试设置DPI感知模式
        import ctypes
        try:
            # 尝试设置进程DPI感知
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        except Exception as e:
            print(f"设置DPI感知失败: {e}")
        
        # 设置高DPI缩放因子的舍入策略
        QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception as e:
        print(f"DPI设置失败: {e}")
        pass
    
    app = QApplication(sys.argv)
    
    # 设置应用程序图标
    from PySide6.QtGui import QIcon
    icon_path = Path(__file__).parent / "UI组件" / "资源文件" / "头像.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


