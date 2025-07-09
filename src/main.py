"""
主程序入口
启动trame服务器
"""

import os
import sys
from dotenv import load_dotenv
from .app import create_app

def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()
    
    # 创建应用实例
    app = create_app()
    
    # 获取配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8080))
    debug = os.getenv("DEBUG", "True").lower() == "true"
    
    print(f"Starting Trame Server on {host}:{port}")
    print(f"Debug mode: {debug}")
    print(f"Access URL: http://{host}:{port}")
    
    # 启动服务器
    app.start(
        host=host,
        port=port,
        debug=debug
    )


if __name__ == "__main__":
    main() 