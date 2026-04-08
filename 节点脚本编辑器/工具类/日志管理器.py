"""日志管理器

区分用户看到的UI日志和开发用的print输出
"""

class LogManager:
    """日志管理器类"""
    
    def __init__(self):
        self.ui_log_stream = None
    
    def set_ui_log_stream(self, ui_log_stream):
        """设置UI日志流"""
        self.ui_log_stream = ui_log_stream
    
    def ui_log(self, message):
        """输出到UI日志"""
        try:
            if self.ui_log_stream:
                self.ui_log_stream.write(message + '\n')
        except Exception as e:
            print(f"UI日志输出失败: {e}")
    
    def ui_error(self, message):
        """输出错误到UI日志"""
        try:
            if self.ui_log_stream:
                self.ui_log_stream.write(f"[错误] {message}\n")
        except Exception as e:
            print(f"UI错误日志输出失败: {e}")

# 创建全局日志管理器实例
log_manager = LogManager()
