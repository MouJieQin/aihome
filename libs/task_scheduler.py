import sqlite3
import threading
import datetime
import json
from libs.log_config import logger
from typing import Callable, Dict, Any, Optional, Tuple, List, Union


class TaskScheduler:
    """增强型任务调度器，支持低CPU负载运行和程序重启后恢复未完成的任务"""

    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"  # 时间格式

    # 任务状态常量
    STATUS_WAITING = "WAITING"  # 等待执行
    STATUS_RUNNING = "RUNNING"  # 运行中（正在执行）
    STATUS_COMPLETED = "COMPLETED"  # 已完成
    STATUS_FAILED = "FAILED"  # 执行失败
    STATUS_OVERDUE = "OVERDUE"  # 已过期

    def __init__(self, config: Dict[str, Any], _task_scheduler_callback: Callable):
        """初始化任务调度器并连接到数据库"""
        self.db_file = config["task_scheduler"]["db_file"]
        self._task_scheduler_callback = _task_scheduler_callback
        self._stop_event = threading.Event()
        self._reload_event = threading.Event()  # 任务变更事件
        self._scheduler_thread = None
        self._init_database()

    def _init_database(self) -> None:
        """初始化SQLite数据库"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    callback TEXT NOT NULL,
                    args_json TEXT,                 -- JSON格式的函数参数
                    next_run_time TEXT NOT NULL,    -- YYYY-MM-DD HH:MM:SS格式
                    interval TEXT,                  -- DD HH:MM:SS格式
                    last_run_time TEXT,             -- YYYY-MM-DD HH:MM:SS格式
                    is_active BOOLEAN NOT NULL DEFAULT 1,  -- 任务是否激活
                    status TEXT NOT NULL DEFAULT 'WAITING'   -- 任务状态
                );
            """
            )
            conn.commit()

    @staticmethod
    def _datetime_to_str(dt: datetime.datetime) -> str:
        """将datetime对象转换为YYYY-MM-DD HH:MM:SS格式字符串"""
        return dt.strftime(TaskScheduler.DATE_FORMAT)

    @staticmethod
    def _str_to_datetime(time_str: str) -> datetime.datetime:
        """将YYYY-MM-DD HH:MM:SS格式字符串转换为datetime对象"""
        return datetime.datetime.strptime(time_str, TaskScheduler.DATE_FORMAT)

    @staticmethod
    def _now_str() -> str:
        """获取当前时间的YYYY-MM-DD HH:MM:SS格式字符串"""
        return datetime.datetime.now().strftime(TaskScheduler.DATE_FORMAT)

    @staticmethod
    def _interval_to_str(days: int, hours: int, minutes: int, seconds: int) -> str:
        """将天时分秒转换为DD HH:MM:SS格式字符串"""
        return f"{days} {hours:02d}:{minutes:02d}:{seconds:02d}"

    @staticmethod
    def _str_to_interval(interval_str: str) -> Tuple[int, int, int, int]:
        """将DD HH:MM:SS格式字符串转换为天时分秒元组"""
        try:
            days_part, time_part = interval_str.split(" ", 1)
            days = int(days_part)
            hours, minutes, seconds = map(int, time_part.split(":"))
            return days, hours, minutes, seconds
        except ValueError:
            raise ValueError("无效的间隔格式，应为DD HH:MM:SS")

    @staticmethod
    def _interval_to_seconds(days: int, hours: int, minutes: int, seconds: int) -> int:
        """将天时分秒转换为总秒数"""
        return days * 86400 + hours * 3600 + minutes * 60 + seconds

    @staticmethod
    def _get_next_run_time(cur_next_run_time_str: str, interval_str: str) -> str:
        """计算下一次运行时间"""
        cur_next_run_time = TaskScheduler._str_to_datetime(cur_next_run_time_str)
        now = datetime.datetime.now()
        if cur_next_run_time > now:
            return cur_next_run_time_str
        time_diff = now - cur_next_run_time
        seconds_diff = time_diff.total_seconds()
        days, hours, minutes, seconds = TaskScheduler._str_to_interval(interval_str)
        seconds_interval = TaskScheduler._interval_to_seconds(
            days, hours, minutes, seconds
        )
        ceil = (seconds_diff // seconds_interval) + (
            1 if (seconds_diff % seconds_interval) != 0 else 0
        )

        next_run_str = TaskScheduler._datetime_to_str(
            cur_next_run_time + datetime.timedelta(seconds=ceil * seconds_interval)
        )
        return next_run_str

    def _trigger_reload(self) -> None:
        """触发重新加载事件"""
        self._reload_event.set()
        # 不需要清除事件状态，在等待时会处理

    def add_task(
        self,
        task_name: str,
        run_at: Union[datetime.datetime, str],
        interval: Union[Tuple[int, int, int, int], str, None] = None,
        args: Optional[Dict[str, Any]] = None,
    ) -> int:
        """添加一个新任务到调度器

        Args:
            task_name: 任务名称
            run_at: 任务首次运行时间，可以是datetime对象或YYYY-MM-DD HH:MM:SS格式字符串
            interval: 任务的重复间隔，可以是(天, 时, 分, 秒)元组或DD HH:MM:SS格式字符串
            args: 任务的参数，将作为回调函数的参数传递，必须是JSON可序列化的字典
        Returns:
            任务ID
        """
        next_run_str = (
            run_at if isinstance(run_at, str) else self._datetime_to_str(run_at)
        )
        interval_str = (
            interval
            if isinstance(interval, str)
            else (self._interval_to_str(*interval) if interval else None)
        )

        # 序列化参数为JSON
        args_json = json.dumps(args, ensure_ascii=False)

        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO tasks (task_name, callback, args_json, next_run_time, interval, is_active) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                # fmt: off
                (task_name, self._task_scheduler_callback.__name__, args_json, next_run_str, interval_str, 1,),
                # fmt: on
            )
            task_id = cursor.lastrowid
            conn.commit()

        # 触发重新加载，确保调度器能立即响应新任务
        self._trigger_reload()
        return task_id  # type: ignore

    def delete_task(self, task_id: int) -> bool:
        """删除指定ID的任务

        Returns:
            是否成功删除
        """
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            deleted = cursor.rowcount > 0

        # 如果删除成功，触发重新加载
        if deleted:
            self._trigger_reload()
        return deleted

    def activate_task(self, task_id: int, active: bool = True) -> bool:
        """激活或暂停指定ID的任务

        Args:
            active: True表示激活任务，False表示暂停任务
        Returns:
            是否成功更新
        """
        if self._renew_task(task_id) == False:
            return False
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE tasks SET is_active = ? WHERE id = ? AND status != ?",
                (1 if active else 0, task_id, self.STATUS_COMPLETED),
            )
            conn.commit()
            updated = cursor.rowcount > 0

        # 如果更新成功，触发重新加载
        if updated:
            self._trigger_reload()
        return updated

    def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks ORDER BY next_run_time")
            return [dict(row) for row in cursor.fetchall()]

    def _renew_task(self, task_id: int) -> bool:
        """重新计算指定任务的下一次运行时间"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT next_run_time, interval FROM tasks WHERE id =?", (task_id,)
            )
            task = cursor.fetchone()
            if task:
                next_run_str, interval_str = task
                if not interval_str:
                    if next_run_str > self._now_str():
                        return True
                    else:
                        cursor.execute(
                            "UPDATE tasks SET status =? WHERE id =?",
                            (self.STATUS_OVERDUE, task_id),
                        )
                        logger.error(f"任务ID {task_id} 已过期")
                        return False
                else:
                    new_next_run_str = self._get_next_run_time(
                        next_run_str, interval_str
                    )
                    if new_next_run_str != next_run_str:
                        cursor.execute(
                            "UPDATE tasks SET next_run_time =? WHERE id =?",
                            (new_next_run_str, task_id),
                        )
                        conn.commit()
                    return True
            else:
                logger.error(f"任务ID {task_id} 不存在")
                return False
        return False

    def _renew_all_tasks(self) -> None:
        """重新计算所有任务的下一次运行时间"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, next_run_time, interval, status FROM tasks")
            tasks = cursor.fetchall()
            for task in tasks:
                task_id, next_run_str, interval_str, status = task
                if interval_str:
                    new_next_run_str = self._get_next_run_time(
                        next_run_str, interval_str
                    )
                    cursor.execute(
                        "UPDATE tasks SET next_run_time =? WHERE id =?",
                        (new_next_run_str, task_id),
                    )
                else:
                    if status == self.STATUS_WAITING and next_run_str < self._now_str():
                        cursor.execute(
                            "UPDATE tasks SET status =? WHERE id =?",
                            (self.STATUS_OVERDUE, task_id),
                        )
            conn.commit()

    def _get_next_run_time_str(self, cur_next_run_str: str, interval_str: str) -> str:
        """计算下一次运行时间"""
        cur_next_run_time = self._str_to_datetime(cur_next_run_str)
        days, hours, minutes, seconds = self._str_to_interval(interval_str)
        total_seconds = self._interval_to_seconds(days, hours, minutes, seconds)
        next_run_str = self._datetime_to_str(
            cur_next_run_time + datetime.timedelta(seconds=total_seconds)
        )
        return next_run_str

    def _task_status_hanlder(self, exception_flag: bool, task_id: int) -> None:
        # 更新任务状态
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT next_run_time, interval FROM tasks WHERE id = ?", (task_id,)
            )
            task = cursor.fetchone()
            if not task:
                return
            cur_next_run_str, interval_str = task
            if interval_str:
                next_run_str = self._get_next_run_time_str(
                    cur_next_run_str, interval_str
                )
                task_status = (
                    self.STATUS_WAITING if not exception_flag else self.STATUS_FAILED
                )
                cursor.execute(
                    """UPDATE tasks SET next_run_time = ?, status = ? 
                    WHERE id = ?""",
                    (next_run_str, task_status, task_id),
                )
            else:
                task_status = (
                    self.STATUS_COMPLETED if not exception_flag else self.STATUS_FAILED
                )
                cursor.execute(
                    "UPDATE tasks SET status = ? WHERE id = ?",
                    (task_status, task_id),
                )
            conn.commit()

    def _execute_task(self, task_id: int, args_json: str) -> None:
        """执行指定任务"""
        exception_flag_outer = False
        try:
            # 解析参数
            args_data = json.loads(args_json)
            # 执行带参数的回调函数

            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE tasks SET status = ?, last_run_time =?
                        WHERE id = ?""",
                    (self.STATUS_RUNNING, self._now_str(), task_id),
                )
                conn.commit()

            def _execute_task_imple() -> None:
                """执行任务的内部函数"""
                exception_flag = False
                try:
                    self._task_scheduler_callback(args_data)
                except Exception as e:
                    logger.exception(f"任务执行失败: {e}")
                    exception_flag = True
                finally:
                    self._task_status_hanlder(exception_flag, task_id)

            threading.Thread(target=_execute_task_imple, daemon=False).start()
        except Exception as e:
            logger.exception(f"执行任务时出错: {e}")
            exception_flag_outer = True
        finally:
            if exception_flag_outer:
                self._task_status_hanlder(exception_flag_outer, task_id)

    def _get_next_task(self) -> Optional[Dict[str, Any]]:
        """获取下一个要执行的任务"""
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, task_name, callback, args_json, next_run_time, interval 
                FROM tasks 
                WHERE is_active = 1 
                AND status != ? 
                AND ( 
                    (interval IS NULL AND status = ?) 
                    OR (interval IS NOT NULL) 
                )
                ORDER BY next_run_time 
                LIMIT 1""",
                (
                    self.STATUS_RUNNING,
                    self.STATUS_WAITING,
                ),
            )
            result = cursor.fetchone()
            return dict(result) if result else None

    def _scheduler_loop(self) -> None:
        """调度器主循环，使用事件等待机制减少CPU占用"""
        while not self._stop_event.is_set():
            next_task = self._get_next_task()

            if next_task:
                now = datetime.datetime.now()
                next_run_dt = self._str_to_datetime(next_task["next_run_time"])

                # 计算距离下一个任务执行的时间（秒）
                wait_time = (next_run_dt - now).total_seconds()

                if wait_time <= 0:
                    # 执行到期的任务
                    self._execute_task(next_task["id"], next_task["args_json"])
                else:
                    # 等待直到下一个任务执行时间或任务变更事件
                    # 使用最小等待时间和事件轮询的方式
                    check_interval = min(wait_time, 1.0)  # 最大检查间隔为1秒

                    while wait_time > 0 and not self._stop_event.is_set():
                        # 等待较短的时间，以便及时响应事件
                        self._reload_event.wait(timeout=check_interval)

                        if self._reload_event.is_set():
                            # 任务变更事件触发，重置并重新评估
                            self._reload_event.clear()
                            break

                        # 重新计算剩余等待时间
                        now = datetime.datetime.now()
                        wait_time = (next_run_dt - now).total_seconds()
                        check_interval = min(wait_time, 1.0)
            else:
                # 没有待执行的任务，等待任务变更事件或每小时检查一次
                self._reload_event.wait(timeout=3600)

    def start(self) -> None:
        """启动任务调度器"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            return
        self._renew_all_tasks()
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop, daemon=True
        )
        self._scheduler_thread.start()
        print("任务调度器已启动")

    def stop(self) -> None:
        """停止任务调度器"""
        self._stop_event.set()
        self._reload_event.set()  # 确保等待中的线程可以退出
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=1.0)
        print("任务调度器已停止")
