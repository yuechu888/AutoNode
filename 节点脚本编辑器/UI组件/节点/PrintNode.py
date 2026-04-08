import sys
import re
from 节点核心.节点基类端口 import BaseNode
from PySide6.QtGui import QFont, QColor, QPen
from PySide6.QtCore import Qt

class PrintNode(BaseNode):
    """输出节点
    
    设计特点：
    1. 只有执行端口
    2. 参数从属性面板控制
    3. 数据通过执行上下文传递
    """
    
    def __init__(self, width=200, height=60, x=0, y=0):
        super().__init__("打印日志", QColor("#2E86AB"), width, height, x, y)
        self.init_ports()
        self.update_variables()

    def init_ports(self):
        # 清空端口列表
        self.ports.clear()
        # 只添加执行端口
        self.add_port("input", "exec", 16, 30, max_connections=-1)
        self.add_port("output", "exec", self.width - 16, 30, max_connections=-1)

    def paint(self, painter, option, widget):
        try:
            # 调用父类的paint方法
            super().paint(painter, option, widget)
        except Exception:
            # 忽略绘制错误，避免程序崩溃
            pass

    def update_variables(self):
        """更新内置变量
        
        这里定义的变量会在属性面板中显示，用户可以直接修改
        """
        super().update_variables()
        
        # 输入变量：在属性面板中可修改
        if 'inputs' not in self.variables or len(self.variables['inputs']) != 1:
            self.variables['inputs'] = [
                {'name': '输出文本', 'type': 'string', 'value': 'Hello World', 'description': '要输出的文本内容'}
            ]
        
        # 输出变量
        if 'outputs' not in self.variables or len(self.variables['outputs']) != 1:
            self.variables['outputs'] = [
                {'name': '打印', 'type': 'string', 'description': '实际输出的内容'}
            ]

    def _execute(self, context, resolved_inputs=None, all_nodes=None):
        """执行打印逻辑"""
        # 每次执行都重新解析，不使用执行标记
        # 移除执行标记检查，确保每次执行都能重新解析变量引用
        
        # 获取属性面板中的参数
        output_text = "Hello World"
        
        # 使用解析后的输入值
        if resolved_inputs:
            for input_var in resolved_inputs:
                if input_var.get('name') == '输出文本':
                    output_text = input_var.get('value', 'Hello World')
        else:
            # 回退到原始变量
            for input_var in self.variables.get('inputs', []):
                if input_var.get('name') == '输出文本':
                    output_text = input_var.get('value', 'Hello World')
        
        # 去除前后空格
        output_text = output_text.strip()
        
        # 使用新的变量引用解析器
        from 工具类.变量引用解析器 import VariableReferenceResolver
        output_text = VariableReferenceResolver.resolve_references(output_text, context, all_nodes)
        
        # 存储输出结果到上下文
        # 使用节点标题作为变量前缀，确保变量名称唯一
        full_var_name = f"{self.title}.print_output"
        unique_var_name = f"print_output_{self.id}"
        context.set_variable(full_var_name, output_text)
        context.set_variable(unique_var_name, output_text)  # 使用带ID的唯一变量名
        context.set_node_output(self.id, output_text)
        
        # 更新输出变量
        self.variables['outputs'][0]['value'] = output_text
        
        # 打印到UI日志窗口
        from 工具类.日志管理器 import log_manager
        log_manager.ui_log(output_text)
        
        return output_text