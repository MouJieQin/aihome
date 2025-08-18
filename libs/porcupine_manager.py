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
        self.mode = "azure"
        if self.mode == "porcupine":
            self._init_porcupine()
        elif self.mode == "azure":
            self._init_awake_recognizer()
        self._init_silent_mode_recognizer()

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

    def _init_porcupine(self):
        """Initialize Porcupine with optimized parameters for better accuracy."""
        config_porcupine = self.configure["porcupine"]
        config_microphone = self.configure["microphone"]

        # 增加灵敏度控制，降低误唤醒概率
        self.porcupine = pvporcupine.create(
            access_key=config_porcupine["access_key"],
            model_path=config_porcupine["model_path"],
            keyword_paths=[config_porcupine["keyword_paths"]],
            sensitivities=[0.5],  # 调整唤醒词灵敏度
        )

        self.pa = pyaudio.PyAudio()
        input_device_name = config_microphone["ai_assistant"]["input_device_name"]
        input_device_index = self._get_input_device_index_by_name(input_device_name)

        if input_device_index is None:
            logger.error(f"未找到名为 {input_device_name} 的输入设备")
            exit(1)

        # 优化音频流参数
        self.audio_stream = self.pa.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            input_device_index=input_device_index,
            frames_per_buffer=self.porcupine.frame_length,
            start=False,  # 不立即启动流，在需要时启动
        )

        # 添加背景噪声适应机制
        self._noise_threshold = self._calculate_noise_threshold()
        self._start_ai_awake_thread()

    def _calculate_noise_threshold(self, sample_duration=2.0):
        """计算环境本底噪声阈值"""
        if not self.audio_stream.is_active():
            self.audio_stream.start_stream()

        # 采集环境噪声样本
        noise_samples = []
        sample_frames = int(
            self.porcupine.sample_rate * sample_duration / self.porcupine.frame_length
        )

        for _ in range(sample_frames):
            pcm = self.audio_stream.read(
                self.porcupine.frame_length, exception_on_overflow=False
            )
            pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
            # 计算样本能量
            energy = sum(abs(x) for x in pcm) / len(pcm)
            noise_samples.append(energy)

        # 计算噪声阈值（取平均值的1.2倍作为基准）
        avg_energy = sum(noise_samples) / len(noise_samples)
        threshold = avg_energy * 1.2

        if not self._is_in_silent_mode and not self.audio_stream.is_active():
            self.audio_stream.stop_stream()

        return threshold

    def _start_ai_awake_thread(self) -> threading.Thread:
        """Start the thread for wake word detection with improved accuracy logic."""

        def run_ai_awake():
            """Run the wake word detection loop with noise filtering and confirmation."""
            try:
                if not self.audio_stream.is_active():
                    self.audio_stream.start_stream()
                while True:
                    if self._is_in_silent_mode:
                        time.sleep(0.5)  # 静默模式下减少CPU占用
                    else:
                        if self.porcupine is None:
                            break
                        try:
                            # 读取音频数据
                            pcm = self.audio_stream.read(
                                self.porcupine.frame_length, exception_on_overflow=False
                            )
                            pcm = struct.unpack_from(
                                "h" * self.porcupine.frame_length, pcm
                            )
                            result = self.porcupine.process(pcm)
                            if result >= 0:
                                logger.info(f"确认检测到唤醒词: あすな")
                                self.awake_callback()

                            # # 能量检测过滤背景噪声
                            # current_energy = sum(abs(x) for x in pcm) / len(pcm)
                            # # 低于噪声阈值，可能是背景噪声
                            # if current_energy > self._noise_threshold:
                            #     # 处理音频帧
                            #     result = self.porcupine.process(pcm)
                            #     if result >= 0:
                            #         logger.info(f"确认检测到唤醒词: あすな")
                            #         self.awake_callback()
                        except Exception as e:
                            logger.warning(f"音频处理异常: {e}")
                            time.sleep(0.1)  # 短暂暂停恢复
            finally:
                if self.audio_stream.is_active():
                    self.audio_stream.stop_stream()

        thread = threading.Thread(target=run_ai_awake)
        thread.daemon = True
        thread.start()
        return thread

    def close_porcupine(self):
        """Close Porcupine resources."""
        if self.mode == "porcupine":
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

    def _init_awake_recognizer(self):
        """Initialize the wake word recognizer."""
        self.wake_word_model = speechsdk.KeywordRecognitionModel(
            "./voices/models/wake-word.table"
        )
        self.start_recognize_wake_word()

    def _create_wake_word_recognizer(self) -> speechsdk.KeywordRecognizer:
        """Create a silent mode recognizer."""
        wake_word_recognizer = speechsdk.KeywordRecognizer()
        wake_word_recognizer.canceled.connect(
            lambda evt: logger.info(f"Wake word recognizer canceled: {evt}")
        )
        wake_word_recognizer.recognized.connect(self._create_wake_word_bk())
        return wake_word_recognizer

    def start_recognize_wake_word(self):
        """Start recognizing the wake word."""
        self.wake_word_recognizer = self._create_wake_word_recognizer()
        self.wake_word_recognizer.recognize_once_async(self.wake_word_model)

    def _create_wake_word_bk(self) -> Callable:
        """Create a callback function for wake word activation."""

        def callback(evt):
            """Handle the event when the wake word is recognized."""
            if evt.result.reason == speechsdk.ResultReason.RecognizedKeyword:
                keyword = evt.result.text
                logger.info(f"确认检测到唤醒词: {keyword}")
                self.awake_callback()
                self.start_recognize_wake_word()
            else:
                logger.debug(f"Keyword not recognized: {evt.result.reason}")

        return callback

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
