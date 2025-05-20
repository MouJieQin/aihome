from pygame import mixer
import os
from typing import *
import threading
import asyncio

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"


class Speaker:
    def __init__(self):
        self.start_record_wav = "./voices/BubbleAppear.aiff.wav"
        self.end_record_wav = "./voices/BubbleDisappear.aiff.wav"
        self.send_message_wav = "./voices/SentMessage.aiff.wav"
        self.receive_response_wav = "./voices/Blow.aiff.wav"
        mixer.init()
        # 缓存已加载的音频文件和播放状态
        self.audio_cache = {}

    async def play_audio(
        self, vfile: str, is_cache: bool = False, event: asyncio.Event = None
    ):
        try:
            if not is_cache:
                # 非缓存模式使用 music 模块
                mixer.music.load(vfile)
                mixer.music.play()

                # 等待播放完成或事件触发
                while mixer.music.get_busy() and (event is None or not event.is_set()):
                    await asyncio.sleep(0.1)

                if event and event.is_set():
                    mixer.music.stop()
            else:
                # 缓存模式使用 Sound 模块
                if vfile not in self.audio_cache:
                    # 首次加载，缓存音频对象
                    sound = mixer.Sound(vfile)
                    self.audio_cache[vfile] = sound
                else:
                    sound = self.audio_cache[vfile]

                # 播放音频并获取 Channel 对象
                channel = sound.play()

                # 等待播放完成或事件触发
                while (
                    channel
                    and channel.get_busy()
                    and (event is None or not event.is_set())
                ):
                    await asyncio.sleep(0.1)

                if event and event.is_set() and channel:
                    channel.stop()  # 停止当前 channel 的播放

        except Exception as e:
            print(f"播放音频时发生错误: {e}")
        # finally:
        # mixer.quit()  # 注意：如果要后续控制音频，不要在这里退出mixer

    def play_audio_blocking(self, vfile: str, is_cache: bool = False):
        """阻塞调用异步音频播放，直到播放完成"""
        loop = asyncio.get_event_loop()

        def run_async_play():
            asyncio.run(self.play_audio(vfile, is_cache))
            # 创建新的事件循环
            # new_loop = asyncio.new_event_loop()
            # asyncio.set_event_loop(new_loop)

            # try:
            #     # 在新循环中运行音频播放协程
            #     new_loop.run_until_complete(self.play_audio(vfile, is_cache))
            # finally:
            #     new_loop.close()

        if loop.is_running():
            # 如果事件循环已在运行，创建新线程运行音频播放
            thread = threading.Thread(target=run_async_play)
            thread.start()
            thread.join()  # 阻塞直到线程完成
        else:
            # 否则直接运行事件循环
            asyncio.run(self.play_audio(vfile, is_cache))

    # def play_audio_blocking(self, vfile: str, is_cache: bool = False):
    #     """阻塞调用异步音频播放，直到播放完成"""
    #     loop = asyncio.get_event_loop()
    #     if loop.is_running():
    #         # 如果事件循环已在运行（例如在Jupyter中），使用run_coroutine_threadsafe
    #         print("loop is running.")
    #         future = asyncio.run_coroutine_threadsafe(
    #             self.play_audio(vfile, is_cache), loop
    #         )
    #         print("22222")
    #         future.result()  # 阻塞直到完成
    #         print("3333")
    #     else:
    #         # 否则直接运行事件循环
    #         asyncio.run(self.play_audio(vfile, is_cache))
    def play_audio_nonblocking(self, vfile: str, is_cache=False) -> threading.Thread:
        """非阻塞调用异步音频播放，在单独线程中运行"""

        def run_async_play():
            asyncio.run(self.play_audio(vfile, is_cache))

        thread = threading.Thread(target=run_async_play)
        thread.daemon = True  # 设置为守护线程，主线程退出时自动终止
        thread.start()
        return thread

    def play_start_record(self, blocking=True):
        self.play_audio_nonblocking(self.start_record_wav, True)

    def play_end_record(self, blocking=True):
        self.play_audio_nonblocking(self.end_record_wav, True)

    def play_send_message(self, blocking=True):
        self.play_audio_nonblocking(self.send_message_wav, True)

    def play_receive_response(self, blocking=True):
        self.play_audio_nonblocking(self.receive_response_wav, True)


# sp=Speaker()
# sp.play_start_record()
