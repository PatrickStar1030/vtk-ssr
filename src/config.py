"""
配置文件
"""

import os
from typing import Dict, Any


class Config:
    """基础配置类"""
    
    # 应用配置
    APP_NAME = "Trame Server"
    APP_VERSION = "1.0.0"
    
    # 服务器配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8080))
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    
    # 安全配置
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/trame_server.log")
    
    # VTK配置
    VTK_BACKGROUND_COLOR = (0.1, 0.1, 0.1)  # 深灰色背景
    VTK_DEFAULT_CAMERA_POSITION = (0, 0, 5)
    VTK_DEFAULT_FOCAL_POINT = (0, 0, 0)
    VTK_DEFAULT_VIEW_UP = (0, 1, 0)


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = "WARNING"


class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True
    LOG_LEVEL = "DEBUG"


# 配置字典
config: Dict[str, Any] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig
} 