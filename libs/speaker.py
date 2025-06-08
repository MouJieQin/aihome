import os

# Set the environment variable before importing pygame
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
from pygame import mixer
from collections import deque
import threading
import asyncio
from typing import Dict, Optional
from libs.log_config import logger
import azure.cognitiveservices.speech as speechsdk
import time


class PygameAudioOutputStream(speechsdk.audio.PushAudioOutputStreamCallback):
    """自定义音频输出流，将语音数据传递给Pygame"""

    def __init__(self, audio_channel: pygame.mixer.Channel):
        super().__init__()
        # 创建一个内存流句柄
        self._audio_buffer = bytearray()  # 累积音频数据的缓冲区
        self.audio_queue = deque()
        self.clock = pygame.time.Clock()
        self.audio_channel = audio_channel
        self.CHUNK_SIZE = 192000

    def write(self, audio_buffer: memoryview) -> int:
        """实现写入方法，将音频数据添加到Pygame音频队列"""
        audio_data = bytes(audio_buffer)
        self._audio_buffer.extend(audio_data)

        # 当缓冲区积累足够数据时，创建音频块并添加到队列
        while len(self._audio_buffer) >= self.CHUNK_SIZE:
            chunk = self._audio_buffer[: self.CHUNK_SIZE]
            self._audio_buffer = self._audio_buffer[self.CHUNK_SIZE :]

            # 创建Pygame声音对象并添加到队列
            try:
                sound = pygame.sndarray.make_sound(
                    pygame.sndarray.array(pygame.mixer.Sound(buffer=chunk))
                )
                # 如果通道当前未播放，立即开始播放
                if not self.audio_channel.get_busy():
                    self.audio_channel.play(sound)
                else:
                    # 如果通道正在播放，将声音对象排队等待播放
                    self.audio_queue.append(sound)
            except Exception as e:
                logger.exception(f"Error creating sound chunk: {e}")
        return len(audio_buffer)

    def close(self) -> None:
        """关闭流时的清理工作"""
        self._audio_data = bytearray()
        logger.info("Audio stream closed")

    def handel_tail(self):
        if self._audio_buffer:
            try:
                sound = pygame.sndarray.make_sound(
                    pygame.sndarray.array(pygame.mixer.Sound(buffer=self._audio_buffer))
                )
                self._audio_buffer = bytearray()  # 清空缓冲区
                if self.audio_channel.get_busy():
                    self.audio_queue.append(sound)
                else:
                    self.audio_channel.play(sound)  # 直接播放
                while self.audio_channel.get_busy():
                    if not self.audio_channel.get_queue() and len(self.audio_queue) > 0:
                        self.audio_channel.queue(self.audio_queue.popleft())
                    time.sleep(0.1)
            except Exception as e:
                logger.exception(f"Error processing remaining audio: {e}")


class Speaker:
    def __init__(self, configure: Dict):
        self.audio_files = {
            "start_record": "./voices/BubbleAppear.aiff.wav",
            "end_record": "./voices/BubbleDisappear.aiff.wav",
            "send_message": "./voices/SentMessage.aiff.wav",
            "receive_response": "./voices/Blow.aiff.wav",
        }
        self.azure_config = configure["azure"]
        self.azure_key = self.azure_config["key"]
        self.azure_region = self.azure_config["region"]
        self.speaker_config = configure["speaker"]
        # Cache loaded audio files
        self.audio_cache = {}
        self._init_mixer()
        self._init_speech_synthesizer()
        self.lock = threading.Lock()

    def _init_mixer(self):
        """Initialize the Pygame mixer."""
        device_name = self.speaker_config["ai_assistant"]["device_name"]
        pygame.mixer.init(
            frequency=16000, size=-16, channels=1, buffer=4096, devicename=device_name
        )
        self.clock = pygame.time.Clock()
        self.audio_channel_assistant_synthesizer = pygame.mixer.Channel(0)
        self.audio_channel_system_prompt = pygame.mixer.Channel(1)

        self.keep_alive_channel = pygame.mixer.Channel(2)
        self.keep_alive_channel.set_volume(0.1)
        self.silent_sound = mixer.Sound(self.audio_files["send_message"])
        self.silent_sound.set_volume(0.1)

    def close(self):
        """Close the Pygame mixer."""
        pygame.mixer.quit()

    async def keep_alive_playback(self):
        while True:
            self.keep_alive_channel.play(self.silent_sound, loops=5)  # 循环播放
            await asyncio.sleep(30)

    def _init_speech_synthesizer(self, voice_name: str = "zh-CN-XiaochenNeural"):
        """Initialize the speech synthesizer."""
        speech_config = speechsdk.SpeechConfig(
            subscription=self.azure_key, region=self.azure_region
        )

        self.output_stream = PygameAudioOutputStream(
            self.audio_channel_assistant_synthesizer
        )
        audio_output_config = speechsdk.audio.AudioOutputConfig(
            stream=speechsdk.audio.PushAudioOutputStream(self.output_stream)
        )
        # audio_output_config.
        speech_config.speech_synthesis_voice_name = voice_name
        self.real_time_speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config, audio_config=audio_output_config
        )

    def _handle_tts_result(
        self,
        tts_result_future: speechsdk.ResultFuture,
        text_to_speak: str,
        file_name: Optional[str] = None,
    ) -> bool:
        """Handle the result of text-to-speech synthesis."""
        if not tts_result_future:
            return False
        speech_synthesis_result = tts_result_future.get()
        if (
            speech_synthesis_result.reason
            == speechsdk.ResultReason.SynthesizingAudioCompleted
        ):
            logger.info(f"\nSpeech synthesized for text [{text_to_speak}]")
            thread = threading.Thread(target=self.output_stream.handel_tail)
            thread.daemon = True
            thread.start()
            if file_name:
                audio_data_stream = speechsdk.AudioDataStream(speech_synthesis_result)
                audio_data_stream.save_to_wav_file(file_name)
                return True
            return True
        elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_synthesis_result.cancellation_details
            logger.info(f"\nSpeech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                if cancellation_details.error_details:
                    logger.error(
                        f"\nError details: {cancellation_details.error_details}"
                    )
                    logger.warning(
                        "\nDid you set the speech resource key and region values?"
                    )
        else:
            logger.error(
                f"\nspeech_synthesis_result.reason: {speech_synthesis_result.reason}"
            )
        return False

    def _get_volume_based_on_time(self):
        """Get the volume based on the current time."""
        current_time = time.localtime()
        hour = current_time.tm_hour
        if hour < 8 or hour >= 21:
            return 0.3
        elif 8 <= hour < 12:
            return 0.8
        elif 12 <= hour < 16:
            return 0.5
        else:
            return 0.8

    def _set_volume_based_on_time(self):
        """Set the volume based on the current time."""
        volume = self._get_volume_based_on_time()
        self.audio_channel_assistant_synthesizer.set_volume(volume)
        self.audio_channel_system_prompt.set_volume(volume)

    def speak_text(self, text: str):
        """Speak the given text in real-time."""
        with self.lock:
            self._set_volume_based_on_time()
            result = self.real_time_speech_synthesizer.speak_text_async(text)
            return self._handle_tts_result(result, text)

    def start_speaking_text(self, text: str):
        """Start speaking the given text in real-time."""
        with self.lock:
            self._set_volume_based_on_time()
            result = self.real_time_speech_synthesizer.speak_text_async(text)
            return self._handle_tts_result(result, text)

    def tts(self, text: str) -> bool:
        """Perform text-to-speech synthesis and handle the result."""
        with self.lock:
            self._set_volume_based_on_time()
            result = self.real_time_speech_synthesizer.speak_text_async(text)
            return self._handle_tts_result(result, text)

    async def _play_audio_core(
        self, vfile: str, is_cache: bool, event: Optional[asyncio.Event]
    ):
        """Core logic for playing audio."""
        with self.lock:
            try:
                if not is_cache:
                    sound = mixer.Sound(vfile)
                    self.audio_channel_system_prompt.play(sound)
                    while self.audio_channel_system_prompt.get_busy() and (
                        event is None or not event.is_set()
                    ):
                        await asyncio.sleep(0.1)
                    if event and event.is_set():
                        self.audio_channel_system_prompt.stop()
                else:
                    if vfile not in self.audio_cache:
                        sound = mixer.Sound(vfile)
                        self.audio_cache[vfile] = sound
                    else:
                        sound = self.audio_cache[vfile]
                    self.audio_channel_system_prompt.play(sound)
                    while self.audio_channel_system_prompt.get_busy() and (
                        event is None or not event.is_set()
                    ):
                        await asyncio.sleep(0.1)
                    if event and event.is_set():
                        self.audio_channel_system_prompt.stop()
            except Exception as e:
                logger.exception(f"An error occurred while playing the audio: {e}")

    async def play_audio(
        self, vfile: str, is_cache: bool = False, event: Optional[asyncio.Event] = None
    ):
        """Play audio asynchronously."""
        await self._play_audio_core(vfile, is_cache, event)

    def play_audio_blocking(self, vfile: str, is_cache: bool = False):
        """Blocking call to play audio until playback is complete."""
        if asyncio.get_event_loop().is_running():

            def run_async_play():
                asyncio.run(self.play_audio(vfile, is_cache))

            thread = threading.Thread(target=run_async_play)
            thread.start()
            thread.join()
        else:
            asyncio.run(self.play_audio(vfile, is_cache))

    def play_audio_nonblocking(
        self, vfile: str, is_cache: bool = False
    ) -> threading.Thread:
        """Non-blocking call to play audio in a separate thread."""

        def run_async_play():
            asyncio.run(self.play_audio(vfile, is_cache))
            # if vfile == self.audio_files["start_record"]:
            #     asyncio.run(self.play_audio(vfile, is_cache))

        thread = threading.Thread(target=run_async_play)
        thread.daemon = True
        thread.start()
        return thread

    def play_start_record(self):
        """Play the start record audio."""
        self.play_audio_nonblocking(self.audio_files["start_record"], True)

    def play_end_record(self):
        """Play the end record audio."""
        self.play_audio_nonblocking(self.audio_files["end_record"], True)

    def play_send_message(self):
        """Play the send message audio."""
        self.play_audio_nonblocking(self.audio_files["send_message"], True)

    def play_receive_response(self):
        """Play the receive response audio."""
        self.play_audio_nonblocking(self.audio_files["receive_response"], True)
