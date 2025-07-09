"""
工具函数模块
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import numpy as np


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """
    设置日志配置
    
    Args:
        log_level: 日志级别
        log_file: 日志文件路径
    """
    # 创建日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 配置根日志器
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（如果指定了日志文件）
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def load_config(config_file: str) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        配置字典
    """
    if not os.path.exists(config_file):
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载配置文件失败: {e}")
        return {}


def save_config(config: Dict[str, Any], config_file: str) -> bool:
    """
    保存配置文件
    
    Args:
        config: 配置字典
        config_file: 配置文件路径
        
    Returns:
        是否保存成功
    """
    try:
        # 确保目录存在
        config_dir = os.path.dirname(config_file)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"保存配置文件失败: {e}")
        return False


def create_vtk_cube(center: List[float] = [0, 0, 0], 
                   size: List[float] = [1, 1, 1],
                   color: List[float] = [1, 0, 0]) -> Dict[str, Any]:
    """
    创建VTK立方体数据
    
    Args:
        center: 中心点坐标
        size: 尺寸 [x, y, z]
        color: 颜色 [r, g, b]
        
    Returns:
        立方体数据字典
    """
    return {
        "type": "cube",
        "center": center,
        "size": size,
        "color": color,
        "visible": True
    }


def create_vtk_sphere(center: List[float] = [0, 0, 0],
                     radius: float = 0.5,
                     color: List[float] = [0, 1, 0]) -> Dict[str, Any]:
    """
    创建VTK球体数据
    
    Args:
        center: 中心点坐标
        radius: 半径
        color: 颜色 [r, g, b]
        
    Returns:
        球体数据字典
    """
    return {
        "type": "sphere",
        "center": center,
        "radius": radius,
        "color": color,
        "visible": True
    }


def create_vtk_cylinder(center: List[float] = [0, 0, 0],
                       radius: float = 0.5,
                       height: float = 2.0,
                       color: List[float] = [0, 0, 1]) -> Dict[str, Any]:
    """
    创建VTK圆柱体数据
    
    Args:
        center: 中心点坐标
        radius: 半径
        height: 高度
        color: 颜色 [r, g, b]
        
    Returns:
        圆柱体数据字典
    """
    return {
        "type": "cylinder",
        "center": center,
        "radius": radius,
        "height": height,
        "color": color,
        "visible": True
    }


def generate_random_points(num_points: int = 100,
                          bounds: List[float] = [-5, 5, -5, 5, -5, 5]) -> np.ndarray:
    """
    生成随机点云数据
    
    Args:
        num_points: 点的数量
        bounds: 边界 [x_min, x_max, y_min, y_max, z_min, z_max]
        
    Returns:
        点云数组
    """
    x = np.random.uniform(bounds[0], bounds[1], num_points)
    y = np.random.uniform(bounds[2], bounds[3], num_points)
    z = np.random.uniform(bounds[4], bounds[5], num_points)
    
    return np.column_stack([x, y, z])


def calculate_bounding_box(points: np.ndarray) -> List[float]:
    """
    计算点云的边界框
    
    Args:
        points: 点云数组
        
    Returns:
        边界框 [x_min, x_max, y_min, y_max, z_min, z_max]
    """
    if len(points) == 0:
        return [0, 0, 0, 0, 0, 0]
    
    x_min, y_min, z_min = np.min(points, axis=0)
    x_max, y_max, z_max = np.max(points, axis=0)
    
    return [x_min, x_max, y_min, y_max, z_min, z_max]


def normalize_points(points: np.ndarray) -> np.ndarray:
    """
    标准化点云数据到单位立方体
    
    Args:
        points: 点云数组
        
    Returns:
        标准化后的点云数组
    """
    if len(points) == 0:
        return points
    
    # 计算边界框
    bbox = calculate_bounding_box(points)
    
    # 计算缩放因子
    scale = max(bbox[1] - bbox[0], bbox[3] - bbox[2], bbox[5] - bbox[4])
    if scale == 0:
        return points
    
    # 标准化
    normalized_points = (points - np.array([bbox[0], bbox[2], bbox[4]])) / scale
    
    return normalized_points 