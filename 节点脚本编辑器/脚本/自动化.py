import cv2
import numpy as np
import mss
import time
import pyautogui
import os
from typing import Optional, Tuple, List
from 工具类.日志管理器 import log_manager

class Automation:
    """前台自动化类，使用MSS截图和OpenCV识别"""
    
    def __init__(self):
        """初始化自动化类"""
        # 禁用pyautogui的FailSafe机制，避免鼠标移动到角落时触发异常
        import pyautogui
        pyautogui.FAILSAFE = False
        
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1]  # 主显示器
        self.current_screenshot = None  # 当前全屏截图缓存
        
        # 使用实际路径
        base_path = os.path.dirname(__file__)
        
        # 默认图像目录
        self.default_image_dir = os.path.join(base_path, "Pic")
        # 确保默认目录存在
        if not os.path.exists(self.default_image_dir):
            os.makedirs(self.default_image_dir)
            print(f"创建默认图像目录: {self.default_image_dir}")
        else:
            print(f"使用默认图像目录: {self.default_image_dir}")
    
    def _resolve_image_path(self, image_path: str) -> str:
        """解析图像路径，如果是相对路径则使用默认目录
        
        Args:
            image_path: 图像路径或图像名称
            
        Returns:
            完整的图像路径
        """
        # 如果已经是绝对路径，直接返回
        if os.path.isabs(image_path):
            return image_path
        
        # 如果包含路径分隔符，认为是相对路径
        if os.path.sep in image_path or '/' in image_path:
            return image_path
        
        # 否则认为是图像名称，使用默认目录
        return os.path.join(self.default_image_dir, image_path)
    
    def capture_full_screen(self) -> np.ndarray:
        """捕获全屏截图并缓存
        
        Returns:
            全屏截图的numpy数组
        """
        try:
            screenshot = self.sct.grab(self.monitor)
            img = np.array(screenshot)
            # 转换为BGR格式（OpenCV使用）
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            self.current_screenshot = img
            return img
        except Exception as e:
            log_manager.ui_error(f"捕获全屏截图时出错: {e}")
            # 返回一个空图像作为备用
            return np.zeros((100, 100, 3), dtype=np.uint8)
    
    def crop_screen(self, region: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """从缓存的全屏截图中裁剪指定区域
        
        Args:
            region: 区域坐标 (x, y, width, height)
            
        Returns:
            裁剪后的图像，未缓存全屏截图则返回None
        """
        try:
            if self.current_screenshot is None:
                log_manager.ui_log("未缓存全屏截图，请先调用 capture_full_screen()")
                return None
            
            x, y, width, height = region
            h, w = self.current_screenshot.shape[:2]
            
            # 确保区域在屏幕范围内
            x = max(0, x)
            y = max(0, y)
            width = min(width, w - x)
            height = min(height, h - y)
            
            if width <= 0 or height <= 0:
                log_manager.ui_log("裁剪区域无效")
                return None
            
            return self.current_screenshot[y:y+height, x:x+width]
        except Exception as e:
            log_manager.ui_error(f"裁剪屏幕时出错: {e}")
            return None
    
    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """捕获屏幕截图
        
        Args:
            region: 区域坐标 (x, y, width, height)，None表示全屏
            
        Returns:
            截图的numpy数组
        """
        try:
            if region:
                monitor = {
                    "top": region[1],
                    "left": region[0],
                    "width": region[2],
                    "height": region[3]
                }
            else:
                monitor = self.monitor
            
            screenshot = self.sct.grab(monitor)
            img = np.array(screenshot)
            # 转换为BGR格式（OpenCV使用）
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            return img
        except Exception as e:
            log_manager.ui_error(f"捕获屏幕截图时出错: {e}")
            # 返回一个空图像作为备用
            return np.zeros((100, 100, 3), dtype=np.uint8)
    
    def find_image(self, target_image_path: str, threshold: float = 0.8, 
                   region: Optional[Tuple[int, int, int, int]] = None, 
                   multi_scale: bool = False, 
                   preprocess: bool = False, 
                   method: int = cv2.TM_CCOEFF_NORMED) -> Optional[Tuple[int, int]]:
        """在屏幕上查找目标图像

        Args:
            target_image_path: 目标图像路径或图像名称
            threshold: 匹配阈值，0-1之间
            region: 搜索区域 (x, y, width, height)
            multi_scale: 是否启用多尺度匹配
            preprocess: 是否启用图像预处理
            method: 模板匹配方法

        Returns:
            找到的图像中心坐标 (x, y)，未找到返回None
        """
        try:
            # 解析图像路径
            resolved_path = self._resolve_image_path(target_image_path)
            # 检查路径是否存在
            if not os.path.exists(resolved_path):
                log_manager.ui_error(f"图像文件不存在: {resolved_path}")
                return None
            
            # 加载目标图像（支持中文路径）
            template = None
            try:
                # 直接使用np.fromfile+cv2.imdecode，确保支持中文路径
                import numpy as np
                with open(resolved_path, 'rb') as f:
                    img_data = np.fromfile(f, dtype=np.uint8)
                template = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                if template is None:
                    log_manager.ui_error(f"无法解码图像文件: {resolved_path}")
            except Exception as e:
                log_manager.ui_error(f"加载图像时出错: {e}")
                template = None
            
            if template is None:
                log_manager.ui_error(f"无法加载目标图像: {resolved_path}")
                return None
            
            # 捕获屏幕
            if region and self.current_screenshot is not None:
                # 使用缓存的全屏截图裁剪区域，提高性能
                screenshot = self.crop_screen(region)
                if screenshot is None:
                    # 裁剪失败，回退到直接捕获区域
                    screenshot = self.capture_screen(region)
            else:
                # 直接捕获屏幕或区域
                screenshot = self.capture_screen(region)
            
            # 图像预处理
            if preprocess:
                # 转换为灰度图
                screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                
                # 高斯模糊
                screenshot_gray = cv2.GaussianBlur(screenshot_gray, (5, 5), 0)
                template_gray = cv2.GaussianBlur(template_gray, (5, 5), 0)
                
                # 边缘检测
                screenshot_gray = cv2.Canny(screenshot_gray, 50, 150)
                template_gray = cv2.Canny(template_gray, 50, 150)
                
                screenshot = screenshot_gray
                template = template_gray
            
            # 多尺度匹配
            if multi_scale:
                best_match = None
                best_val = -1
                
                # 缩放范围
                scales = [0.8, 1.0, 1.2]
                
                for scale in scales:
                    # 缩放模板
                    h, w = template.shape[:2]
                    new_h, new_w = int(h * scale), int(w * scale)
                    
                    # 确保缩放后的模板大小合理
                    if new_h < 10 or new_w < 10:
                        continue
                    
                    resized_template = cv2.resize(template, (new_w, new_h))
                    
                    # 确保模板大小小于截图大小
                    if resized_template.shape[0] > screenshot.shape[0] or resized_template.shape[1] > screenshot.shape[1]:
                        continue
                    
                    # 模板匹配
                    result = cv2.matchTemplate(screenshot, resized_template, method)
                    
                    # 找到最匹配的位置
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    # 根据匹配方法选择最大值或最小值
                    if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                        current_val = 1 - min_val
                    else:
                        current_val = max_val
                    
                    if current_val > best_val and current_val >= threshold:
                        best_val = current_val
                        best_match = (max_loc, scale)
                
                if best_match:
                    max_loc, scale = best_match
                    h, w = template.shape[:2]
                    new_h, new_w = int(h * scale), int(w * scale)
                    center_x = max_loc[0] + new_w // 2
                    center_y = max_loc[1] + new_h // 2
                    
                    # 如果指定了区域，需要加上区域的偏移
                    if region:
                        center_x += region[0]
                        center_y += region[1]
                    
                    return (center_x, center_y)
            else:
                # 单尺度匹配
                result = cv2.matchTemplate(screenshot, template, method)
                
                # 找到最匹配的位置
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                # 根据匹配方法选择最大值或最小值
                if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                    current_val = 1 - min_val
                else:
                    current_val = max_val
                
                if current_val >= threshold:
                    # 计算中心坐标
                    h, w = template.shape[:2]
                    center_x = max_loc[0] + w // 2
                    center_y = max_loc[1] + h // 2
                    
                    # 如果指定了区域，需要加上区域的偏移
                    if region:
                        center_x += region[0]
                        center_y += region[1]
                    
                    return (center_x, center_y)
            
            return None
        except Exception as e:
            log_manager.ui_error(f"查找图像时出错: {e}")
            return None
    
    def click(self, x: int, y: int, duration: float = 0.05) -> bool:
        """点击指定坐标
        
        Args:
            x: x坐标
            y: y坐标
            duration: 点击持续时间
            
        Returns:
            操作是否成功
        """
        try:
            # 使用更短的默认点击持续时间
            pyautogui.click(x, y, duration=duration)
            return True
        except Exception as e:
            log_manager.ui_error(f"点击时出错: {e}")
            return False
    
    def move_to(self, x: int, y: int, duration: float = 0.1) -> bool:
        """移动鼠标到指定坐标
        
        Args:
            x: x坐标
            y: y坐标
            duration: 移动持续时间
            
        Returns:
            操作是否成功
        """
        try:
            # 使用更短的默认移动持续时间
            pyautogui.moveTo(x, y, duration=duration)
            return True
        except Exception as e:
            log_manager.ui_error(f"移动鼠标时出错: {e}")
            return False
    
    def find_and_click(self, target_image_path: str, threshold: float = 0.8, 
                      region: Optional[Tuple[int, int, int, int]] = None, 
                      max_attempts: int = 1) -> bool:
        """查找并点击目标图像
        
        Args:
            target_image_path: 目标图像路径
            threshold: 匹配阈值
            region: 搜索区域 (x, y, width, height)
            max_attempts: 最大尝试次数
            delay: 尝试间隔
            
        Returns:
            操作是否成功
        """
        for attempt in range(max_attempts):
            print(f"尝试查找图像 ({attempt + 1}/{max_attempts})...")
            
            # 对于区域搜索，使用缓存的全屏截图提高性能
            if region:
                # 每次尝试都重新捕获全屏，确保获取最新画面
                self.capture_full_screen()
                print(f"在区域 {region} 中搜索...")
            
            position = self.find_image(target_image_path, threshold, region)
            
            if position:
                log_manager.ui_log(f"找到图像，位置: {position}")
                success = self.click(position[0], position[1])
                if success:
                    log_manager.ui_log("点击成功")
                    time.sleep(0.1)
                    return True
                else:
                    log_manager.ui_error("点击失败")
            else:
                log_manager.ui_log("未找到图像")
            time.sleep(0.08)
        log_manager.ui_error("达到最大尝试次数，操作失败")
        return False
    
    def find_all_images(self, target_image_path: str, threshold: float = 0.8, 
                       region: Optional[Tuple[int, int, int, int]] = None) -> List[Tuple[int, int]]:
        """查找屏幕上所有匹配的图像
        
        Args:
            target_image_path: 目标图像路径或图像名称
            threshold: 匹配阈值
            region: 搜索区域
            
        Returns:
            所有找到的图像中心坐标列表
        """
        try:
            # 解析图像路径
            resolved_path = self._resolve_image_path(target_image_path)
            print(f"解析后的图像路径: {resolved_path}")
            
            # 检查路径是否存在
            if not os.path.exists(resolved_path):
                log_manager.ui_error(f"图像文件不存在: {resolved_path}")
                return []
            
            # 加载目标图像（支持中文路径）
            template = None
            try:
                # 直接使用np.fromfile+cv2.imdecode，确保支持中文路径
                import numpy as np
                with open(resolved_path, 'rb') as f:
                    img_data = np.fromfile(f, dtype=np.uint8)
                template = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                if template is None:
                    log_manager.ui_error(f"无法解码图像文件: {resolved_path}")
            except Exception as e:
                log_manager.ui_error(f"加载图像时出错: {e}")
                template = None
            
            if template is None:
                log_manager.ui_error(f"无法加载目标图像: {resolved_path}")
                return []
            
            # 捕获屏幕
            if region and self.current_screenshot is not None:
                # 使用缓存的全屏截图裁剪区域，提高性能
                screenshot = self.crop_screen(region)
                if screenshot is None:
                    # 裁剪失败，回退到直接捕获区域
                    screenshot = self.capture_screen(region)
            else:
                # 直接捕获屏幕或区域
                screenshot = self.capture_screen(region)
            
            # 模板匹配
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            
            # 找到所有匹配的位置
            locations = np.where(result >= threshold)
            
            positions = []
            h, w = template.shape[:2]
            
            # 去重处理
            seen = set()
            for pt in zip(*locations[::-1]):
                center_x = pt[0] + w // 2
                center_y = pt[1] + h // 2
                
                # 如果指定了区域，需要加上区域的偏移
                if region:
                    center_x += region[0]
                    center_y += region[1]
                
                # 去重（避免同一目标被多次检测）
                key = (center_x // 10, center_y // 10)  # 10px精度去重
                if key not in seen:
                    seen.add(key)
                    positions.append((center_x, center_y))
            
            return positions
        except Exception as e:
            log_manager.ui_error(f"查找所有图像时出错: {e}")
            return []
    
    def click_all_images(self, target_image_path: str, threshold: float = 0.8, 
                        region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """点击所有找到的目标图像
        
        Args:
            target_image_path: 目标图像路径
            threshold: 匹配阈值
            region: 搜索区域
            
        Returns:
            操作是否成功
        """
        positions = self.find_all_images(target_image_path, threshold, region)
        
        if not positions:
            log_manager.ui_log("未找到任何图像")
            return False
        
        log_manager.ui_log(f"找到 {len(positions)} 个匹配图像")
        
        for i, position in enumerate(positions):
            log_manager.ui_log(f"点击第 {i + 1} 个位置: {position}")
            success = self.click(position[0], position[1])
            if not success:
                log_manager.ui_error(f"点击位置 {position} 失败")
            time.sleep(0.2)  # 点击间隔
        
        return True
    
    def wait_for_image(self, target_image_path: str, threshold: float = 0.8, 
                      region: Optional[Tuple[int, int, int, int]] = None, 
                      timeout: float = 30.0, interval: float = 1.0) -> Optional[Tuple[int, int]]:
        """等待目标图像出现
        
        Args:
            target_image_path: 目标图像路径或图像名称
            threshold: 匹配阈值
            region: 搜索区域
            timeout: 超时时间（秒）
            interval: 检查间隔（秒）
            
        Returns:
            找到的图像中心坐标，超时返回None
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 每次循环都重新捕获屏幕，确保获取最新画面
            if region:
                # 对于区域搜索，直接捕获区域
                position = self.find_image(target_image_path, threshold, region)
            else:
                # 对于全屏搜索，先捕获全屏再搜索
                self.capture_full_screen()
                position = self.find_image(target_image_path, threshold)
            
            if position:
                log_manager.ui_log(f"找到图像，位置: {position}")
                return position
            
            time.sleep(interval)
        
        log_manager.ui_error("等待超时，未找到图像")
        return None
    
    def wait_and_click(self, target_image_path: str, threshold: float = 0.8, 
                      region: Optional[Tuple[int, int, int, int]] = None, 
                      timeout: float = 30.0, interval: float = 1.0) -> bool:
        """等待目标图像出现并点击
        
        Args:
            target_image_path: 目标图像路径
            threshold: 匹配阈值
            region: 搜索区域
            timeout: 超时时间
            interval: 检查间隔
            
        Returns:
            操作是否成功
        """
        position = self.wait_for_image(target_image_path, threshold, region, timeout, interval)
        
        if position:
            success = self.click(position[0], position[1])
            if success:
                log_manager.ui_log("点击成功")
                return True
            else:
                log_manager.ui_error("点击失败")
                return False
        
        return False
    
    def close(self):
        """关闭MSS实例"""
        if hasattr(self, 'sct'):
            self.sct.close()


# 示例用法
if __name__ == "__main__":
    auto = Automation()
    
    try:
        # 示例1: 普通查找并点击图像（使用默认目录）
        # 直接使用图像名称，会自动在 Pic 目录中查找
        # success = auto.find_and_click("target.png", threshold=0.8)
        # print(f"操作结果: {success}")
        
        # 示例2: 等待图像出现并点击（使用默认目录）
        # success = auto.wait_and_click("target.png", timeout=10)
        # print(f"操作结果: {success}")
        
        # 示例3: 点击所有匹配的图像（使用默认目录）
        # success = auto.click_all_images("target.png")
        # print(f"操作结果: {success}")
        
        # 示例4: 使用区域查找（推荐）- 自动捕获屏幕
        print("使用区域查找功能...")
        # 定义搜索区域 (x, y, width, height)
        search_region = (0, 0, 800, 600)
        # 直接调用查找并点击，不需要手动捕获屏幕
        success = auto.find_and_click("图1.png", threshold=0.8, region=search_region)
        print(f"区域查找操作结果: {success}")
        
        # 示例5: 在多个区域中搜索
        # print("在多个区域中搜索...")
        # regions = [
        #     (100, 100, 400, 300),  # 区域1
        #     (500, 100, 400, 300),  # 区域2
        #     (100, 400, 800, 400)   # 区域3
        # ]
        
        # target_image = "target.png"  # 直接使用图像名称
        # for i, region in enumerate(regions):
        #     print(f"搜索区域 {i+1}: {region}")
        #     # 直接调用，自动处理截图
        #     position = auto.find_image(target_image, region=region)
        #     if position:
        #         print(f"找到图像在区域 {i+1}: {position}")
        #         auto.click(position[0], position[1])
        #         break
        
        # 示例6: 使用绝对路径（仍然支持）
        # full_path = r"C:\path\to\image.png"
        # success = auto.find_and_click(full_path)
        # print(f"绝对路径操作结果: {success}")
        
        print("默认路径识别功能已就绪")
        print("自动化类初始化成功")
        print("True")
    finally:
        auto.close()