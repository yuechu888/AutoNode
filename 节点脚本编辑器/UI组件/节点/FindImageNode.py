from 节点核心.节点基类端口 import BaseNode
from PySide6.QtGui import QFont, QColor, QPen
from PySide6.QtCore import Qt, QThread, Signal
from 脚本.自动化 import Automation
from 工具类.日志管理器 import log_manager

import random
import time

class FindImageThread(QThread):
    """查找图像的线程类"""
    finished = Signal(bool, str)  # 信号，参数为(结果, 位置)
    
    def __init__(self, image_name, region, threshold, max_attempts, find_interval, click_method, x_offset, y_offset, target_x, target_y, do_click, do_move, move_x, move_y, multi_scale, preprocess, match_method):
        super().__init__()
        self.image_name = image_name
        self.region = region
        self.threshold = threshold
        self.max_attempts = max_attempts
        self.delay = find_interval  # 查找间隔时间
        self.click_method = click_method
        self.x_offset = x_offset
        self.y_offset = y_offset
        self.target_x = target_x
        self.target_y = target_y
        self.do_click = do_click  # 是否执行点击操作
        self.do_move = do_move  # 是否执行鼠标移动
        self.move_x = move_x  # 鼠标移动的X坐标
        self.move_y = move_y  # 鼠标移动的Y坐标
        self.multi_scale = multi_scale  # 是否启用多尺度匹配
        self.preprocess = preprocess  # 是否启用图像预处理
        self.match_method = match_method  # 模板匹配方法
        self.random_range = 5  # 固定随机范围为5
        self._stop_requested = False
    
    def run(self):
        """线程执行函数"""
        auto = None
        result = False
        position = ""
        
        try:
            auto = Automation()
            # 先查找图像
            found_position = None
            for attempt in range(self.max_attempts):
                # 检查是否请求停止
                if self._stop_requested:
                    print("查找图像线程被停止")
                    position = "已停止"
                    break
                
                # 无论是否指定了区域，都先捕获全屏截图，确保获取最新画面
                auto.capture_full_screen()
                
                # 选择匹配方法
                import cv2
                method = cv2.TM_CCOEFF_NORMED
                if self.match_method == "平方差匹配":
                    method = cv2.TM_SQDIFF
                elif self.match_method == "归一化平方差匹配":
                    method = cv2.TM_SQDIFF_NORMED
                elif self.match_method == "相关性匹配":
                    method = cv2.TM_CCORR
                elif self.match_method == "归一化相关性匹配":
                    method = cv2.TM_CCORR_NORMED
                
                found_position = auto.find_image(
                    self.image_name, 
                    threshold=self.threshold, 
                    region=self.region,
                    multi_scale=self.multi_scale,
                    preprocess=self.preprocess,
                    method=method
                )
                if found_position:
                    break
                time.sleep(self.delay)
            
            # 检查是否请求停止
            if self._stop_requested:
                print("查找图像线程被停止")
                position = "已停止"
            elif found_position:
                # 根据点击方法执行不同的点击逻辑
                click_position = None
                
                if self.click_method == "随机点击":
                    # 随机点击：点击找到的坐标，添加随机偏移
                    random_x = random.randint(-self.random_range, self.random_range)
                    random_y = random.randint(-self.random_range, self.random_range)
                    click_position = (found_position[0] + random_x, found_position[1] + random_y)
                    position = f"({found_position[0]}, {found_position[1]}) -> 随机偏移到 ({click_position[0]}, {click_position[1]})"
                elif self.click_method == "随机偏移点击":
                    # 随机偏移点击：找到后进行坐标偏移，然后添加随机偏移
                    offset_x = found_position[0] + self.x_offset
                    offset_y = found_position[1] + self.y_offset
                    random_x = random.randint(-self.random_range, self.random_range)
                    random_y = random.randint(-self.random_range, self.random_range)
                    click_position = (offset_x + random_x, offset_y + random_y)
                    position = f"({found_position[0]}, {found_position[1]}) -> 偏移到 ({offset_x}, {offset_y}) -> 随机偏移到 ({click_position[0]}, {click_position[1]})"
                elif self.click_method == "随机指点点击":
                    # 随机指点点击：找到后直接点击指定的坐标
                    click_position = (self.target_x, self.target_y)
                    position = f"找到图像位置 ({found_position[0]}, {found_position[1]}) -> 点击指定位置 ({click_position[0]}, {click_position[1]})"
                else:
                    # 默认随机点击
                    random_x = random.randint(-self.random_range, self.random_range)
                    random_y = random.randint(-self.random_range, self.random_range)
                    click_position = (found_position[0] + random_x, found_position[1] + random_y)
                    position = f"({found_position[0]}, {found_position[1]}) -> 随机偏移到 ({click_position[0]}, {click_position[1]})"
                
                # 执行点击（如果需要）
                click_success = True
                if self.do_click and click_position:
                    # 检查是否请求停止
                    if self._stop_requested:
                        print("查找图像线程被停止")
                        position = "已停止"
                    else:
                        # 尝试执行点击，捕获可能的异常
                        try:
                            click_success = auto.click(click_position[0], click_position[1], duration=0.05)
                            result = click_success
                            if not click_success:
                                position += " (点击失败)"
                        except Exception as e:
                            print(f"点击时出错: {e}")
                            click_success = False
                            result = False
                            position += " (点击失败)"
                else:
                    # 不执行点击，只返回查找结果
                    result = True
                    if not self.do_click:
                        position += " (未执行点击)"
                
                # 执行鼠标移动（如果需要），只有当操作成功时才执行
                move_success = True
                if self.do_move and result:
                    # 检查是否请求停止
                    if self._stop_requested:
                        print("查找图像线程被停止")
                        position = "已停止"
                    else:
                        # 尝试执行鼠标移动，捕获可能的异常
                        try:
                            move_success = auto.move_to(self.move_x, self.move_y, duration=0.1)
                            position += f" (已执行鼠标移动到: ({self.move_x}, {self.move_y}))"
                            if not move_success:
                                position += " (移动失败)"
                        except Exception as e:
                            print(f"移动鼠标时出错: {e}")
                            move_success = False
                
                # 综合判断操作结果
                # 如果执行了移动，结果应该是点击成功且移动成功
                if self.do_move:
                    result = result and move_success
            else:
                position = "未找到"
        except Exception as e:
            error_msg = f"查找图像时出错: {str(e)}"
            print(error_msg)
            result = False
            position = "错误"
        finally:
            if auto:
                try:
                    auto.close()
                except Exception as e:
                    print(f"关闭自动化实例时出错: {e}")
        
        # 发送完成信号
        self.finished.emit(result, position)
    
    def stop(self):
        """请求停止线程"""
        self._stop_requested = True

class FindImageNode(BaseNode):
    """查找图像节点
    
    设计特点：
    1. 只有执行端口
    2. 参数从属性面板控制
    3. 使用自动化库执行图像查找和点击
    4. 使用线程执行耗时操作，避免阻塞主线程
    """
    
    def __init__(self, width=200, height=60, x=0, y=0):
        super().__init__("查找图像", QColor("#3498DB"), width, height, x, y)
        self.init_ports()
        self.update_variables()
        self.thread = None

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
            value = input_var.get('value', '')
            if value != '':
                input_values[input_name] = value
        
        # 映射旧的方法名称到新的方法名称
        method_mapping = {
            '方法1': '随机点击',
            '方法2': '随机偏移点击',
            '方法3': '随机指点点击',
            '随机偏移': '随机点击',
            '坐标偏移+随机': '随机偏移点击',
            '指定坐标': '随机指点点击'
        }
        
        # 获取当前的点击方法，并转换为新的名称
        current_click_method = input_values.get('点击方法', '随机点击')
        # 如果是旧的方法名称，转换为新的
        if current_click_method in method_mapping:
            current_click_method = method_mapping[current_click_method]
        
        # 构建输入变量列表
        inputs = [
            {'name': '图像名称', 'type': 'string', 'value': input_values.get('图像名称', 'target.png'), 'description': '要查找的图像文件名（在Pic目录中）'},
            {'name': '搜索区域', 'type': 'string', 'value': input_values.get('搜索区域', '0,0,1920,1080'), 'description': '搜索区域坐标和大小，格式：x,y,width,height'},
            {'name': '匹配阈值', 'type': 'number', 'value': input_values.get('匹配阈值', '0.8'), 'description': '图像匹配的阈值（0-1）'},
            {'name': '最大尝试次数', 'type': 'number', 'value': input_values.get('最大尝试次数', '1'), 'description': '查找图像的最大尝试次数'},
            {'name': '查找间隔', 'type': 'number', 'value': input_values.get('查找间隔', '0.05'), 'description': '每次尝试查找的间隔时间（秒），值越小速度越快'},
            {'name': '是否点击', 'type': 'string', 'value': input_values.get('是否点击', '是'), 'description': '找到图像后是否执行点击操作', 'options': ['是', '否']},
            {'name': '点击方法', 'type': 'string', 'value': current_click_method, 'description': '点击方法选择', 'options': ['随机点击', '随机偏移点击', '随机指点点击']},
            
            # 根据点击方法添加相应的参数
            {'name': '执行下一步操作', 'type': 'string', 'value': input_values.get('执行下一步操作', input_values.get('是否移动鼠标', '否')), 'description': '找到图像后是否执行鼠标移动', 'options': ['是', '否']},
            {'name': '移动X坐标', 'type': 'number', 'value': input_values.get('移动X坐标', '0'), 'description': '鼠标移动的X坐标'},
            {'name': '移动Y坐标', 'type': 'number', 'value': input_values.get('移动Y坐标', '0'), 'description': '鼠标移动的Y坐标'},
            {'name': '多尺度匹配', 'type': 'string', 'value': input_values.get('多尺度匹配', '否'), 'description': '是否启用多尺度匹配（提高准确性，降低速度）', 'options': ['是', '否']},
            {'name': '图像预处理', 'type': 'string', 'value': input_values.get('图像预处理', '否'), 'description': '是否启用图像预处理（提高准确性，降低速度）', 'options': ['是', '否']},
            {'name': '匹配方法', 'type': 'string', 'value': input_values.get('匹配方法', '归一化相关系数匹配'), 'description': '模板匹配方法', 'options': ['归一化相关系数匹配', '平方差匹配', '归一化平方差匹配', '相关性匹配', '归一化相关性匹配']}
        ]
        
        # 根据点击方法添加相应的参数
        if current_click_method == '随机偏移点击':
            # 随机偏移点击需要X偏移和Y偏移
            inputs.insert(7, {'name': 'X偏移', 'type': 'number', 'value': input_values.get('X偏移', '0'), 'description': 'X方向偏移量（随机偏移点击使用）'})
            inputs.insert(8, {'name': 'Y偏移', 'type': 'number', 'value': input_values.get('Y偏移', '0'), 'description': 'Y方向偏移量（随机偏移点击使用）'})
        elif current_click_method == '随机指点点击':
            # 随机指点点击需要指定X坐标和Y坐标
            inputs.insert(7, {'name': '指定X坐标', 'type': 'number', 'value': input_values.get('指定X坐标', '0'), 'description': '指定的点击X坐标（随机指点点击使用）'})
            inputs.insert(8, {'name': '指定Y坐标', 'type': 'number', 'value': input_values.get('指定Y坐标', '0'), 'description': '指定的点击Y坐标（随机指点点击使用）'})
        
        # 输入变量：在属性面板中可修改
        self.variables['inputs'] = inputs
        
        # 输出变量
        self.variables['outputs'] = [
            {'name': '查找结果', 'type': 'boolean', 'description': '是否找到并点击了图像'},
            {'name': '找到的位置', 'type': 'string', 'description': '找到图像的坐标位置'}
        ]

    def _execute(self, context, resolved_inputs=None, all_nodes=None):
        """执行查找图像逻辑"""
        # 获取参数
        image_name = "target.png"
        region = (0, 0, 1920, 1080)  # 默认全屏
        threshold = 0.8
        max_attempts = 1
        
        # 解析搜索区域的函数
        def parse_region(region_str):
            try:
                parts = region_str.split(',')
                if len(parts) == 4:
                    x = int(parts[0].strip())
                    y = int(parts[1].strip())
                    width = int(parts[2].strip())
                    height = int(parts[3].strip())
                    return (x, y, width, height)
            except Exception as e:
                print(f"解析区域时出错: {e}")
                pass
            return (0, 0, 1920, 1080)  # 默认值
        
        # 点击方法相关参数
        click_method = "方法1"
        x_offset = 0
        y_offset = 0
        target_x = 0
        target_y = 0
        do_click = True  # 默认执行点击
        do_move = True  # 默认执行鼠标移动
        move_x = 0  # 默认移动X坐标
        move_y = 0  # 默认移动Y坐标
        find_interval = 0.05  # 默认查找间隔（更快）
        multi_scale = False  # 默认禁用多尺度匹配（提高速度）
        preprocess = False  # 默认禁用图像预处理（提高速度）
        match_method = "归一化相关系数匹配"  # 默认匹配方法
        
        # 从解析后的输入值获取参数
        try:
            if resolved_inputs:
                for input_var in resolved_inputs:
                    if input_var.get('name') == '图像名称':
                        image_name = input_var.get('value', 'target.png')
                    elif input_var.get('name') == '搜索区域':
                        region_str = input_var.get('value', '0,0,1920,1080')
                        region = parse_region(region_str)
                    elif input_var.get('name') == '匹配阈值':
                        try:
                            threshold = float(input_var.get('value', '0.8'))
                        except:
                            threshold = 0.8
                    elif input_var.get('name') == '最大尝试次数':
                        try:
                            max_attempts = int(input_var.get('value', '1'))
                        except:
                            max_attempts = 1
                    elif input_var.get('name') == '查找间隔':
                        try:
                            find_interval = float(input_var.get('value', '0.08'))
                        except:
                            find_interval = 0.08
                    elif input_var.get('name') == '是否点击':
                        do_click = input_var.get('value', '是') == '是'
                    elif input_var.get('name') == '执行下一步操作':
                        do_move = input_var.get('value', '是') == '是'
                    elif input_var.get('name') == '移动X坐标':
                        try:
                            move_x = int(input_var.get('value', '0'))
                        except:
                            move_x = 0
                    elif input_var.get('name') == '移动Y坐标':
                        try:
                            move_y = int(input_var.get('value', '0'))
                        except:
                            move_y = 0
                    elif input_var.get('name') == '点击方法':
                        click_method = input_var.get('value', '方法1')
                    elif input_var.get('name') == 'X偏移':
                        try:
                            x_offset = int(input_var.get('value', '0'))
                        except:
                            x_offset = 0
                    elif input_var.get('name') == 'Y偏移':
                        try:
                            y_offset = int(input_var.get('value', '0'))
                        except:
                            y_offset = 0
                    elif input_var.get('name') == '指定X坐标':
                        try:
                            target_x = int(input_var.get('value', '0'))
                        except:
                            target_x = 0
                    elif input_var.get('name') == '指定Y坐标':
                        try:
                            target_y = int(input_var.get('value', '0'))
                        except:
                            target_y = 0
                    elif input_var.get('name') == '多尺度匹配':
                        multi_scale = input_var.get('value', '否') == '是'
                    elif input_var.get('name') == '图像预处理':
                        preprocess = input_var.get('value', '否') == '是'
                    elif input_var.get('name') == '匹配方法':
                        match_method = input_var.get('value', '归一化相关系数匹配')
            else:
                # 回退到原始变量
                for input_var in self.variables.get('inputs', []):
                    if input_var.get('name') == '图像名称':
                        image_name = input_var.get('value', 'target.png')
                    elif input_var.get('name') == '搜索区域':
                        region_str = input_var.get('value', '0,0,1920,1080')
                        region = parse_region(region_str)
                    elif input_var.get('name') == '匹配阈值':
                        try:
                            threshold = float(input_var.get('value', '0.8'))
                        except:
                            threshold = 0.8
                    elif input_var.get('name') == '最大尝试次数':
                        try:
                            max_attempts = int(input_var.get('value', '1'))
                        except:
                            max_attempts = 1
                    elif input_var.get('name') == '查找间隔':
                        try:
                            find_interval = float(input_var.get('value', '0.08'))
                        except:
                            find_interval = 0.08
                    elif input_var.get('name') == '是否点击':
                        do_click = input_var.get('value', '是') == '是'
                    elif input_var.get('name') == '执行下一步操作':
                        do_move = input_var.get('value', '是') == '是'
                    elif input_var.get('name') == '移动X坐标':
                        try:
                            move_x = int(input_var.get('value', '0'))
                        except:
                            move_x = 0
                    elif input_var.get('name') == '移动Y坐标':
                        try:
                            move_y = int(input_var.get('value', '0'))
                        except:
                            move_y = 0
                    elif input_var.get('name') == '点击方法':
                        click_method = input_var.get('value', '方法1')
                    elif input_var.get('name') == 'X偏移':
                        try:
                            x_offset = int(input_var.get('value', '0'))
                        except:
                            x_offset = 0
                    elif input_var.get('name') == 'Y偏移':
                        try:
                            y_offset = int(input_var.get('value', '0'))
                        except:
                            y_offset = 0
                    elif input_var.get('name') == '指定X坐标':
                        try:
                            target_x = int(input_var.get('value', '0'))
                        except:
                            target_x = 0
                    elif input_var.get('name') == '指定Y坐标':
                        try:
                            target_y = int(input_var.get('value', '0'))
                        except:
                            target_y = 0
                    elif input_var.get('name') == '多尺度匹配':
                        multi_scale = input_var.get('value', '否') == '是'
                    elif input_var.get('name') == '图像预处理':
                        preprocess = input_var.get('value', '否') == '是'
                    elif input_var.get('name') == '匹配方法':
                        match_method = input_var.get('value', '归一化相关系数匹配')
        except Exception as e:
            print(f"获取参数时出错: {e}")
        
        # 输出执行信息到日志
        try:
            print(f"开始执行查找图像节点: 图像名称={image_name}, 搜索区域={region}")
        except Exception as e:
            print(f"日志输出失败: {e}")
        
        # 使用线程执行耗时操作，但不阻塞主线程
        result = False
        position = ""
        
        # 使用标志和事件来处理线程完成
        from PySide6.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        
        def on_thread_finished(thread_result, thread_position):
            nonlocal result, position
            result = thread_result
            position = thread_position
            loop.quit()
        
        # 创建并启动线程
        self.thread = FindImageThread(image_name, region, threshold, max_attempts, find_interval, click_method, x_offset, y_offset, target_x, target_y, do_click, do_move, move_x, move_y, multi_scale, preprocess, match_method)
        self.thread.finished.connect(on_thread_finished)
        self.thread.start()
        
        # 等待线程完成，但允许事件循环处理其他事件
        # 使用较小的超时，以便能够处理UI事件
        timeout = 30000  # 30秒超时
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 处理事件循环一小段时间
            loop.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 100)
            # 检查线程是否已完成
            if not self.thread.isRunning():
                break
            # 检查是否请求停止
            if hasattr(context, 'is_stop_requested') and context.is_stop_requested():
                print("查找图像节点执行被用户停止")
                # 停止线程
                if self.thread and self.thread.isRunning():
                    self.thread.stop()
                    # 等待线程结束
                    self.thread.wait(1000)  # 等待1秒
                break
            # 短暂休眠，避免CPU占用过高
            time.sleep(0.01)
        
        # 处理执行结果
        if position == "错误":
            error_msg = "查找图像时出错"
            context.add_error(error_msg)
            self.execution_status = "error"
            self.error_message = error_msg
        else:
            # 输出执行结果到日志
            try:
                if result:
                    log_manager.ui_log(f"成功找到图像，位置: {position}")
                else:
                    log_manager.ui_log("未找到图像")
            except Exception as e:
                print(f"日志输出失败: {e}")
        
        # 存储输出结果到上下文
        try:
            full_var_name = f"{self.title}.find_result"
            unique_var_name = f"find_result_{self.id}"
            context.set_variable(full_var_name, result)
            context.set_variable(unique_var_name, result)
            context.set_node_output(self.id, result)
            
            # 存储位置信息
            position_var_name = f"{self.title}.position"
            position_unique_name = f"position_{self.id}"
            context.set_variable(position_var_name, position)
            context.set_variable(position_unique_name, position)
            
            # 更新输出变量
            self.variables['outputs'][0]['value'] = result
            self.variables['outputs'][1]['value'] = position
        except Exception as e:
            print(f"存储结果时出错: {e}")
        
        # 输出执行结果到日志
        try:
            log_manager.ui_log(f"查找图像节点执行完成，结果: {result}")
        except Exception as e:
            print(f"日志输出失败: {e}")
        
        return result