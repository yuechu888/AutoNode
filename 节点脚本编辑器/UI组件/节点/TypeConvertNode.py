from 节点核心.节点基类端口 import BaseNode
from PySide6.QtGui import QFont, QColor, QPen
from PySide6.QtCore import Qt

class TypeConvertNode(BaseNode):
    """类型转换节点
    
    设计特点：
    1. 只有执行端口
    2. 参数从属性面板控制
    3. 数据通过执行上下文传递
    """
    
    def __init__(self, width=280, height=60, x=0, y=0):
        super().__init__("类型转换", QColor("#9B59B6"), width, height, x, y)
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
        
        # 保留现有的目标类型
        current_target_type = '字符串'
        input_value = '0'
        
        # 检查是否已有输入变量
        current_inputs = self.variables.get('inputs', [])
        for input_var in current_inputs:
            input_name = input_var.get('name')
            if input_name == '目标类型':
                value = input_var.get('value', '字符串')
                if value != '':
                    current_target_type = value
            elif input_name == '输入值':
                value = input_var.get('value', '0')
                if value != '':
                    input_value = value
        
        # 定义所有可用的类型
        available_types = ['字符串', '整数', '浮点数', '布尔值']
        
        # 输入变量：在属性面板中可修改
        self.variables['inputs'] = [
            {'name': '输入值', 'type': 'string', 'value': input_value},
            {'name': '目标类型', 'type': 'select', 'value': current_target_type, 'options': available_types}
        ]
        
        # 输出变量
        self.variables['outputs'] = [
            {'name': '结果', 'type': 'any'}
        ]

    def get_current_type(self, value):
        """获取当前值的类型"""
        if value is None:
            return "None"
        elif isinstance(value, str):
            return "字符串"
        elif isinstance(value, int):
            return "整数"
        elif isinstance(value, float):
            return "浮点数"
        elif isinstance(value, bool):
            return "布尔值"
        else:
            return str(type(value).__name__)

    def _execute(self, context, resolved_inputs=None, all_nodes=None):
        """执行类型转换逻辑"""
        # 获取属性面板中的参数
        input_value = "0"
        target_type = "字符串"
        result_var_name = "result"
        
        # 从解析后的输入值获取参数
        if resolved_inputs:
            for input_var in resolved_inputs:
                if input_var.get('name') == '输入值':
                    input_value = input_var.get('value', '0')
                elif input_var.get('name') == '目标类型':
                    target_type = input_var.get('value', '字符串')
        else:
            # 回退到原始变量
            for input_var in self.variables.get('inputs', []):
                if input_var.get('name') == '输入值':
                    input_value = input_var.get('value', '0')
                elif input_var.get('name') == '目标类型':
                    target_type = input_var.get('value', '字符串')
        
        # 执行类型转换
        result = None
        try:
            if target_type == '字符串':
                result = str(input_value)
            elif target_type == '整数':
                try:
                    # 先尝试直接转换
                    result = int(input_value)
                except ValueError:
                    # 如果是字符串形式的浮点数，先转换为浮点数再转换为整数
                    try:
                        result = int(float(input_value))
                    except ValueError:
                        error_msg = f"无法将 {input_value} 转换为整数"
                        context.add_error(error_msg)
                        self.execution_status = "error"
                        self.error_message = error_msg
                        return None
            elif target_type == '浮点数':
                try:
                    result = float(input_value)
                except ValueError:
                    error_msg = f"无法将 {input_value} 转换为浮点数"
                    context.add_error(error_msg)
                    self.execution_status = "error"
                    self.error_message = error_msg
                    return None
            elif target_type == '布尔值':
                if isinstance(input_value, str):
                    input_lower = input_value.lower()
                    if input_lower in ['true', '1', 'yes', 'y', 't']:
                        result = True
                    elif input_lower in ['false', '0', 'no', 'n', 'f']:
                        result = False
                    else:
                        error_msg = f"无法将 {input_value} 转换为布尔值"
                        context.add_error(error_msg)
                        self.execution_status = "error"
                        self.error_message = error_msg
                        return None
                else:
                    result = bool(input_value)
        except Exception as e:
            error_msg = f"类型转换错误: {str(e)}"
            context.add_error(error_msg)
            self.execution_status = "error"
            self.error_message = error_msg
            return None
        
        # 存储输出结果到上下文
        # 使用节点标题作为变量前缀，确保变量名称唯一
        full_var_name = f"{self.title}.{result_var_name}"
        unique_var_name = f"{result_var_name}_{self.id}"
        context.set_variable(full_var_name, result)
        context.set_variable(unique_var_name, result)  # 使用带ID的唯一变量名
        context.set_node_output(self.id, result)
        
        # 更新输出变量
        self.variables['outputs'][0]['value'] = result
        
        # 不再触发后续节点执行，由execute_all方法中的拓扑排序决定执行顺序
        
        return result