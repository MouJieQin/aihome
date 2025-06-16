import pvporcupine
import pyaudio
import struct
import time
import threading
import azure.cognitiveservices.speech as speechsdk
from typing import Optional, Callable
from libs.log_config import logger


class PorcupineManager:
    def __init__(
        self,
        configure: dict,
        awake_callback: Callable,
        enter_silent_mode_callback: Callable,
        exit_silent_mode_callback: Callable,
    ):
        """Initialize the PorcupineManager with configuration."""
        self.configure = configure
        self._is_in_silent_mode = False
        self._is_awaked = False
        self._is_last_silent_mode = False  # Workaround for SDK bug
        self.awake_callback = awake_callback
        self.enter_silent_mode_callback = enter_silent_mode_callback
        self.exit_silent_mode_callback = exit_silent_mode_callback
        self._init_porcupine()
        self._init_silent_mode_recognizer()

    def _init_porcupine(self):
        """Initialize Porcupine for wake word detection."""
        config_porcupine = self.configure["porcupine"]
        config_microphone = self.configure["microphone"]
        self.porcupine = pvporcupine.create(
            access_key=config_porcupine["access_key"],
            model_path=config_porcupine["model_path"],
            keyword_paths=[config_porcupine["keyword_paths"]],
        )
        self.pa = pyaudio.PyAudio()
        input_device_name = config_microphone["ai_assistant"]["input_device_name"]
        input_device_index = self._get_input_device_index_by_name(input_device_name)
        if input_device_index is None:
            logger.error(f"未找到名为 {input_device_name} 的输入设备")
            exit(1)
            return
        self.audio_stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            input_device_index=input_device_index,
            frames_per_buffer=self.porcupine.frame_length,
        )
        self._start_ai_awake_thread()

    def _get_input_device_index_by_name(self, device_name: str) -> Optional[int]:
        """Get the input device index by its name."""
        for i in range(self.pa.get_device_count()):
            device_info = self.pa.get_device_info_by_index(i)
            if (
                device_info["name"] == device_name
                and device_info["maxInputChannels"] != 0
            ):
                return i
        return None

    def _start_ai_awake_thread(self) -> threading.Thread:
        """Start the thread for wake word detection."""

        def run_ai_awake():
            """Run the wake word detection loop."""
            while True:
                if self._is_in_silent_mode:
                    time.sleep(3)
                else:
                    if self.porcupine is None:
                        return
                    pcm = self.audio_stream.read(
                        self.porcupine.frame_length, exception_on_overflow=False
                    )
                    pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                    result = self.porcupine.process(pcm)
                    if result >= 0:
                        logger.info(f"检测到唤醒词: あすな")
                        self.awake_callback()

        thread = threading.Thread(target=run_ai_awake)
        thread.daemon = True
        thread.start()
        return thread

    def close_porcupine(self):
        """Close Porcupine resources."""
        if self.pa is not None:
            self.pa.terminate()
        if self.audio_stream is not None:
            self.audio_stream.close()
        if self.porcupine is not None:
            self.porcupine.delete()

    def set_awake(self, is_awake: bool):
        """Set the activation state of the AI assistant."""
        self._is_awaked = is_awake
        if is_awake:
            logger.info("AI助手已激活")
        else:
            logger.info("AI助手已停用")

    def is_awaked(self) -> bool:
        """Check if the AI assistant is activated."""
        return self._is_awaked

    def is_in_silent_mode(self) -> bool:
        """Check if the AI assistant is in silent mode."""
        return self._is_in_silent_mode

    def _create_silent_mode_bk(self) -> Callable:
        """Create a callback function for silent mode activation."""

        def callback(evt):
            """Handle the event when silent mode is activated or deactivated."""
            if evt.result.reason == speechsdk.ResultReason.RecognizedKeyword:
                keyword = evt.result.text
                if keyword == "进入静默模式":
                    self._is_in_silent_mode = True
                    self.enter_silent_mode_callback()
                elif keyword == "退出静默模式":
                    self._is_in_silent_mode = False
                    self.exit_silent_mode_callback()
            else:
                logger.debug(f"Keyword not recognized: {evt.result.reason}")

        return callback

    def _init_silent_mode_recognizer(self):
        """Initialize the silent mode recognizer."""
        self.silent_mode_on_model = speechsdk.KeywordRecognitionModel(
            "./voices/models/enter-silent-mode.table"
        )
        self.silent_mode_off_model = speechsdk.KeywordRecognitionModel(
            "./voices/models/exit-silent-mode.table"
        )
        self.silent_mode_recognizer = self._create_silent_mode_recognizer()

    def _create_silent_mode_recognizer(self) -> speechsdk.KeywordRecognizer:
        """Create a silent mode recognizer."""
        silent_mode_recognizer = speechsdk.KeywordRecognizer()
        silent_mode_recognizer.canceled.connect(
            lambda evt: logger.info(f"Silent mode recognizer canceled: {evt}")
        )
        silent_mode_recognizer.recognized.connect(self._create_silent_mode_bk())
        return silent_mode_recognizer

    def start_recognize_silent_mode_off(self):
        """Start recognizing the silent mode deactivation keyword."""
        self.silent_mode_recognizer = self._create_silent_mode_recognizer()
        self._is_last_silent_mode = True  # Workaround for SDK bug
        self.silent_mode_recognizer.recognize_once_async(self.silent_mode_off_model)

    def start_recognize_silent_mode_on(self):
        """Start recognizing the silent mode activation keyword."""
        if self._is_last_silent_mode:  # Workaround for SDK bug
            self.silent_mode_recognizer = self._create_silent_mode_recognizer()
            self._is_last_silent_mode = False
        self.silent_mode_recognizer.recognize_once_async(self.silent_mode_on_model)

    def stop_recognize_silent_mode_on(self):
        """Stop recognizing the silent mode activation keyword."""
        self.silent_mode_recognizer.stop_recognition_async()
