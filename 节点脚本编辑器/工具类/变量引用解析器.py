import re
from 节点核心.上下文 import Context

class VariableReferenceResolver:
    """变量引用解析器
    
    支持通过 ${node_id.variable_name} 格式引用其他节点的变量
    """
    
    # 变量引用正则表达式，支持 ${...} 和 {...} 格式
    VARIABLE_REFERENCE_PATTERN = r'\$?\{([^}]+)\}'
    
    @staticmethod
    def parse_variable_reference(ref_str):
        """解析变量引用字符串
        
        Args:
            ref_str: 变量引用字符串，格式如 "node_id.variable_name"、"节点标题 (cn_id:node_id).variable_name" 或 "cn_in3.结果"
            
        Returns:
            tuple: (node_id, variable_name) 或 (None, None) 如果格式不正确
        """
        if not ref_str:
            return None, None
        
        parts = ref_str.split('.', 1)
        if len(parts) != 2:
            return None, None
        
        node_identifier, variable_name = parts
        
        # 尝试直接解析为数字ID
        try:
            node_id = int(node_identifier)
            return node_id, variable_name
        except ValueError:
            # 尝试从节点标题格式中提取ID，如 "计算 (cn_id:3)" 或 "计算 (cn_id: 3)"
            import re
            match = re.search(r'\(cn_id:\s*(\d+)\s*\)', node_identifier)
            if match:
                try:
                    node_id = int(match.group(1))
                    return node_id, variable_name
                except ValueError:
                    pass
            # 尝试从简洁格式中提取ID，如 "cn_in3.结果"
            match = re.search(r'[a-zA-Z]+(\d+)', node_identifier)
            if match:
                try:
                    node_id = int(match.group(1))
                    return node_id, variable_name
                except ValueError:
                    pass
        
        return None, None
    
    @staticmethod
    def resolve_references(text, context, all_nodes=None):
        """解析文本中的变量引用
        
        Args:
            text: 包含变量引用的文本
            context: 执行上下文
            all_nodes: 所有节点的字典，格式为 {node_id: node}
            
        Returns:
            str: 解析后的文本
        """
        if not text or not isinstance(text, str):
            return text
        
        def replace_match(match):
            ref_str = match.group(1)
            node_id, variable_name = VariableReferenceResolver.parse_variable_reference(ref_str)
            
            if node_id is None:
                return match.group(0)  # 格式不正确，保持原样
            
            # 尝试从上下文获取节点输出
            if context:
                node_output = context.get_node_output(node_id)
                if node_output is not None:
                    if isinstance(node_output, dict) and variable_name in node_output:
                        return str(node_output[variable_name])
                    elif variable_name == 'output':
                        return str(node_output)
            
            # 尝试从节点变量获取
            if all_nodes and node_id in all_nodes:
                node = all_nodes[node_id]
                if hasattr(node, 'variables'):
                    if variable_name in node.variables:
                        value = node.variables[variable_name]
                        return str(value)
                    # 尝试从输入变量中获取
                    inputs = node.variables.get('inputs', [])
                    for input_var in inputs:
                        if input_var.get('name') == variable_name:
                            return str(input_var.get('value', ''))
                    # 尝试从输出变量中获取
                    outputs = node.variables.get('outputs', [])
                    for output_var in outputs:
                        if output_var.get('name') == variable_name:
                            return str(output_var.get('value', ''))
            
            # 无法解析，保持原样
            return match.group(0)
        
        return re.sub(VariableReferenceResolver.VARIABLE_REFERENCE_PATTERN, replace_match, text)
    
    @staticmethod
    def resolve_value(value, context, all_nodes=None):
        """解析值中的变量引用
        
        Args:
            value: 可能包含变量引用的值
            context: 执行上下文
            all_nodes: 所有节点的字典
            
        Returns:
            解析后的值
        """
        if isinstance(value, str):
            return VariableReferenceResolver.resolve_references(value, context, all_nodes)
        elif isinstance(value, dict):
            return {k: VariableReferenceResolver.resolve_value(v, context, all_nodes) for k, v in value.items()}
        elif isinstance(value, list):
            return [VariableReferenceResolver.resolve_value(item, context, all_nodes) for item in value]
        else:
            return value
    
    @staticmethod
    def validate_references(text, all_nodes=None):
        """验证文本中的变量引用
        
        Args:
            text: 包含变量引用的文本
            all_nodes: 所有节点的字典
            
        Returns:
            list: 错误信息列表
        """
        if not text or not isinstance(text, str):
            return []
        
        errors = []
        matches = re.finditer(VariableReferenceResolver.VARIABLE_REFERENCE_PATTERN, text)
        
        for match in matches:
            ref_str = match.group(1)
            node_id, variable_name = VariableReferenceResolver.parse_variable_reference(ref_str)
            
            if node_id is None:
                errors.append(f"无效的变量引用格式: {match.group(0)}")
                continue
            
            if all_nodes and node_id not in all_nodes:
                errors.append(f"引用的节点不存在: {node_id}")
                continue
            
            if all_nodes and node_id in all_nodes:
                node = all_nodes[node_id]
                if hasattr(node, 'variables'):
                    # 检查变量是否存在
                    if variable_name not in node.variables:
                        # 检查输入变量
                        inputs = node.variables.get('inputs', [])
                        input_names = [input_var.get('name') for input_var in inputs]
                        # 检查输出变量
                        outputs = node.variables.get('outputs', [])
                        output_names = [output_var.get('name') for output_var in outputs]
                        
                        if variable_name not in input_names and variable_name not in output_names and variable_name != 'output':
                            errors.append(f"节点 {node_id} 中不存在变量: {variable_name}")
        
        return errors
    
    @staticmethod
    def extract_references(text):
        """提取文本中的所有变量引用
        
        Args:
            text: 包含变量引用的文本
            
        Returns:
            list: 变量引用列表，每个元素为 (node_id, variable_name)
        """
        if not text or not isinstance(text, str):
            return []
        
        references = []
        matches = re.finditer(VariableReferenceResolver.VARIABLE_REFERENCE_PATTERN, text)
        
        for match in matches:
            ref_str = match.group(1)
            node_id, variable_name = VariableReferenceResolver.parse_variable_reference(ref_str)
            if node_id is not None:
                references.append((node_id, variable_name))
        
        return references