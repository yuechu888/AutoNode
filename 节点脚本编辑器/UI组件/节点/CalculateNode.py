import math
from 节点核心.节点基类端口 import BaseNode
from PySide6.QtGui import QFont, QColor, QPen
from PySide6.QtCore import Qt

class CalculateNode(BaseNode):
    """计算节点
    
    设计特点：
    1. 只有执行端口
    2. 参数从属性面板控制
    3. 数据通过执行上下文传递
    """
    
    def __init__(self, width=200, height=60, x=0, y=0):
        super().__init__("计算", QColor("#27AE60"), width, height, x, y)
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
        
        # 保留现有的输入变量值
        current_inputs = self.variables.get('inputs', [])
        input_values = {}
        for input_var in current_inputs:
            input_name = input_var.get('name')
            value = input_var.get('value', '0')
            if value != '':
                input_values[input_name] = value
        
        # 保留现有的计算方法
        current_method = '加法'
        for input_var in current_inputs:
            if input_var.get('name') == '计算方法':
                value = input_var.get('value', '加法')
                if value != '':
                    current_method = value
                break
        
        # 定义所有可用的计算方法
        available_methods = ['加法', '减法', '乘法', '除法', '取模', '幂运算', '平方根', '绝对值',
                           '向上取整', '向下取整', '四舍五入',
                           '正弦', '余弦', '正切',
                           '自然对数', '以10为底的对数',
                           '最大值', '最小值', '求和']
        
        # 输入变量：在属性面板中可修改
        self.variables['inputs'] = [
            {'name': '操作数1', 'type': 'number', 'value': input_values.get('操作数1', '0'), 'description': '第一个参与计算的数值'},
            {'name': '操作数2', 'type': 'number', 'value': input_values.get('操作数2', '0'), 'description': '第二个参与计算的数值'},
            {'name': '计算方法', 'type': 'select', 'value': current_method, 'options': available_methods, 'description': '选择要执行的计算操作'}
        ]
        
        # 输出变量
        self.variables['outputs'] = [
            {'name': '结果', 'type': 'number', 'description': '计算的最终结果'}
        ]

    def _execute(self, context, resolved_inputs=None, all_nodes=None):
        """执行计算逻辑"""
        # 每次执行都重新计算，不使用执行标记
        # 获取操作数
        val1 = 0
        val2 = 0
        method = "加法"
        result_var_name = "result"
        
        # 从解析后的输入值获取参数
        if resolved_inputs:
            for input_var in resolved_inputs:
                if input_var.get('name') == '操作数1':
                    try:
                        val1 = float(input_var.get('value', '0'))
                    except:
                        val1 = 0
                elif input_var.get('name') == '操作数2':
                    try:
                        val2 = float(input_var.get('value', '0'))
                    except:
                        val2 = 0
                elif input_var.get('name') == '计算方法':
                    method = input_var.get('value', '加法')
        else:
            # 回退到原始变量
            for input_var in self.variables.get('inputs', []):
                if input_var.get('name') == '操作数1':
                    try:
                        val1 = float(input_var.get('value', '0'))
                    except:
                        val1 = 0
                elif input_var.get('name') == '操作数2':
                    try:
                        val2 = float(input_var.get('value', '0'))
                    except:
                        val2 = 0
                elif input_var.get('name') == '计算方法':
                    method = input_var.get('value', '加法')
        
        # 根据计算方法执行计算
        result = 0
        try:
            if method == '加法':
                result = val1 + val2
            elif method == '减法':
                result = val1 - val2
            elif method == '乘法':
                result = val1 * val2
            elif method == '除法':
                if val2 != 0:
                    result = val1 / val2
                else:
                    error_msg = "除数不能为零"
                    context.add_error(error_msg)
                    self.execution_status = "error"
                    self.error_message = error_msg
                    return None
            elif method == '取模':
                if val2 != 0:
                    result = val1 % val2
                else:
                    error_msg = "除数不能为零"
                    context.add_error(error_msg)
                    self.execution_status = "error"
                    self.error_message = error_msg
                    return None
            elif method == '幂运算':
                result = val1 ** val2
            elif method == '平方根':
                if val1 >= 0:
                    result = math.sqrt(val1)
                else:
                    error_msg = "不能对负数取平方根"
                    context.add_error(error_msg)
                    self.execution_status = "error"
                    self.error_message = error_msg
                    return None
            elif method == '绝对值':
                result = abs(val1)
            elif method == '向上取整':
                result = math.ceil(val1)
            elif method == '向下取整':
                result = math.floor(val1)
            elif method == '四舍五入':
                result = round(val1)
            elif method == '正弦':
                # 将角度转换为弧度
                radians = math.radians(val1)
                result = math.sin(radians)
            elif method == '余弦':
                # 将角度转换为弧度
                radians = math.radians(val1)
                result = math.cos(radians)
            elif method == '正切':
                # 将角度转换为弧度
                radians = math.radians(val1)
                # 避免除以零的错误
                if abs(math.cos(radians)) < 1e-10:
                    error_msg = "正切函数在90°的奇数倍处无定义"
                    context.add_error(error_msg)
                    self.execution_status = "error"
                    self.error_message = error_msg
                    return None
                result = math.tan(radians)
            elif method == '自然对数':
                if val1 > 0:
                    result = math.log(val1)
                else:
                    error_msg = "自然对数只对正数有效"
                    context.add_error(error_msg)
                    self.execution_status = "error"
                    self.error_message = error_msg
                    return None
            elif method == '以10为底的对数':
                if val1 > 0:
                    result = math.log10(val1)
                else:
                    error_msg = "对数只对正数有效"
                    context.add_error(error_msg)
                    self.execution_status = "error"
                    self.error_message = error_msg
                    return None
            elif method == '最大值':
                result = max(val1, val2)
            elif method == '最小值':
                result = min(val1, val2)
            elif method == '求和':
                result = val1 + val2
        except Exception as e:
            error_msg = f"计算错误: {str(e)}"
            context.add_error(error_msg)
            self.execution_status = "error"
            self.error_message = error_msg
            return None
        
        # 处理结果类型：如果结果是浮点数但小数部分为0，则转换为整数
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        
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