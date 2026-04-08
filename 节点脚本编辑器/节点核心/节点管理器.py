from importlib import import_module
from pathlib import Path
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class NodeManager:
    """节点管理器，负责节点的注册、发现和创建"""
    
    # 类变量，用于存储已发现的节点类
    _discovered_nodes = {}
    _node_metadata = {}
    _instance = None
    
    def __new__(cls):
        """单例模式，确保只创建一个NodeManager实例"""
        if cls._instance is None:
            cls._instance = super(NodeManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化节点管理器"""
        # 确保只初始化一次
        if not hasattr(self, '_initialized'):
            self._initialized = True
            if not NodeManager._discovered_nodes:
                self.discover_nodes()
    
    def discover_nodes(self):
        """自动发现所有节点类"""
        # 遍历节点目录
        node_dir = Path(__file__).parent.parent / "UI组件" / "节点"
        if not node_dir.exists():
            print(f"节点目录不存在: {node_dir}")
            return
        
        print(f"发现节点目录: {node_dir}")
        
        # 导入所有节点模块
        for file_path in node_dir.glob("*.py"):
            if file_path.name == "__init__.py":
                continue
            
            print(f"发现节点文件: {file_path.name}")
            
            # 构建模块路径
            module_name = f"UI组件.节点.{file_path.stem}"
            try:
                # 导入模块
                module = import_module(module_name)
                print(f"成功导入模块: {module_name}")
                
                # 查找节点类
                for name in dir(module):
                    obj = getattr(module, name)
                    # 检查是否是节点类（继承自BaseNode）
                    if hasattr(obj, "__bases__") and any(base.__name__ == "BaseNode" for base in obj.__bases__):
                        # 注册节点类
                        if name not in NodeManager._discovered_nodes:
                            NodeManager._discovered_nodes[name] = obj
                            # 设置默认元数据
                            NodeManager._node_metadata[name] = {
                                "name": name,
                                "category": "内置",
                                "description": "内置节点"
                            }
                            print(f"注册节点类: {name}")
            except Exception as e:
                print(f"导入节点模块 {module_name} 时出错: {e}")
        
        print(f"最终注册的节点: {list(NodeManager._discovered_nodes.keys())}")
    
    def register_node(self, node_type, node_class, metadata=None):
        """注册新节点类型"""
        NodeManager._discovered_nodes[node_type] = node_class
        NodeManager._node_metadata[node_type] = metadata or {
            "name": node_type,
            "category": "自定义",
            "description": "自定义节点"
        }
        print(f"注册节点: {node_type}")
    
    def get_node_classes(self):
        """获取所有节点类"""
        return NodeManager._discovered_nodes
    
    def create_node(self, node_type, **kwargs):
        """创建节点实例"""
        # 检查是否是开始节点，如果是，确保只创建一个
        if node_type == 'StartNode':
            # 检查是否已经存在StartNode实例
            from UI组件.主界面 import MainWindow
            # 这里需要一种方式来检查是否已经存在StartNode
            # 由于主界面可能还未初始化，我们暂时不做严格检查
            # 实际的检查会在主界面初始化时进行
            pass
        
        if node_type in NodeManager._discovered_nodes:
            return NodeManager._discovered_nodes[node_type](**kwargs)
        return None
    
    def get_node_names(self):
        """获取所有节点名称"""
        return list(NodeManager._discovered_nodes.keys())
    
    def get_node_metadata(self, node_type):
        """获取节点元数据"""
        return NodeManager._node_metadata.get(node_type, {})
    
    def get_all_node_metadata(self):
        """获取所有节点的元数据"""
        return NodeManager._node_metadata

# 创建全局节点管理器实例
node_manager = NodeManager()