from pygame import mixer
import os
from typing import *
import threading
import asyncio
import azure.cognitiveservices.speech as speechsdk

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"


class Speaker:
    def __init__(self, configure: Dict):
        self.start_record_wav = "./voices/BubbleAppear.aiff.wav"
        self.end_record_wav = "./voices/BubbleDisappear.aiff.wav"
        self.send_message_wav = "./voices/SentMessage.aiff.wav"
        self.receive_response_wav = "./voices/Blow.aiff.wav"
        self.azure_config = configure["azure"]
        self.azure_key = self.azure_config["key"]
        self.azure_region = self.azure_config["region"]
        mixer.init()
        # 缓存已加载的音频文件和播放状态
        self.audio_cache = {}
        self.__init_speech_synthesizer()

    def __init_speech_synthesizer(self, voice_name="zh-CN-XiaochenNeural"):
        speech_config = speechsdk.SpeechConfig(
            subscription=self.azure_key, region=self.azure_region
        )
        audio_output_config = speechsdk.audio.AudioOutputConfig(
            use_default_speaker=True
        )

        speech_config.speech_synthesis_voice_name = voice_name
        self.speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_output_config
        )
        self.real_time_speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_output_config
        )

    def azure_tts_result(self, tts_resultfuture, text_to_speak, file_name=None):
        if not tts_resultfuture:
            return
        speech_synthesis_result = tts_resultfuture.get()
        if (
            speech_synthesis_result.reason
            == speechsdk.ResultReason.SynthesizingAudioCompleted
        ):
            print("\nSpeech synthesized for text [{}]".format(text_to_speak))

            if file_name:
                audio_data_stream = speechsdk.AudioDataStream(speech_synthesis_result)
                # You can save all the data in the audio data stream to a file
                audio_data_stream.save_to_wav_file(file_name)
                return True
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            print("\nSpeech synthesis canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    print(
                        "\nError details: {}".format(cancellation_details.error_details)
                    )
                    print("\nDid you set the speech resource key and region values?")
        else:
            print(
                "\nspeech_synthesis_result.reason: {}".format(
                    speech_synthesis_result.reason
                )
            )

    def tts(self, text):
        result = self.real_time_speech_synthesizer.speak_text_async(text)
        res = self.azure_tts_result(result, text)
        return res

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
    #         future.result()  # 阻塞直到完成
    #     else:
    #         # 否则直接运行事件循环
    #         asyncio.run(self.play_audio(vfile, is_cache))

    def play_audio_nonblocking(self, vfile: str, is_cache=False) -> threading.Thread:
        """非阻塞调用异步音频播放，在单独线程中运行"""

        def run_async_play():
            asyncio.run(self.play_audio(vfile, is_cache))
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


configure = {}
import json

with open("./configure.json", mode="r", encoding="utf-8") as f:
    configure = json.load(f)
sp=Speaker(configure)
sp.tts("当前室内温度25.3摄氏度，当前空气湿度43.2%，需要我为您开启空调吗？")
print("@out")
while True:
    import time
    time.sleep(10)
# sp.play_start_record()
