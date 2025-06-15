import os
from src.ai_server import AIserver
from libs.log_config import logger
import asyncio

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    AI = AIserver(configure_path="./configure.json")
    logger.info(AI.get_states_of_all_devices())
    try:
        asyncio.run(AI.main())
    except KeyboardInterrupt:
        logger.info("程序已停止")
    except Exception as e:
        logger.exception(f"发生错误: {e}")
