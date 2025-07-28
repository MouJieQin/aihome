import azure.cognitiveservices.speech as speechsdk
from typing import Dict, Callable
from libs.log_config import logger


class Recognizer:
    def __init__(self, configure: Dict, recognized_callback: Callable):
        self.azure_config = configure["azure"]
        self.azure_key = self.azure_config["key"]
        self.azure_region = self.azure_config["region"]
        self.recognized_callback = recognized_callback
        self.is_stopping_recognizer = False
        self.max_len_recogized_words = 0
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.azure_key,
            region=self.azure_region,
            speech_recognition_language="zh-CN",
        )
        microphone = configure["microphone"]["azure_recognizer"]
        device_name = microphone["input_device_id"]
        self.audio_config = speechsdk.audio.AudioConfig(device_name=device_name)
        self._init_recognizer()

    def _init_recognizer(self):
        self.auto_speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config, audio_config=self.audio_config
        )

        self.auto_speech_recognizer.recognizing.connect(
            self._azure_stt_input_auto_recognizing
        )
        self.auto_speech_recognizer.recognized.connect(
            self._azure_stt_input_auto_recognized
        )

        self.auto_speech_recognizer.session_started.connect(
            self._azure_auto_stt_recognizer_session_started
        )
        self.auto_speech_recognizer.session_stopped.connect(
            self._azure_auto_stt_recognizer_session_stopped
        )
        self.auto_speech_recognizer.canceled.connect(
            self._azure_auto_stt_recognizer_canceled
        )

    def is_stopping(self) -> bool:
        return self.is_stopping_recognizer

    def get_max_len_recogized_words(self) -> int:
        return self.max_len_recogized_words

    def start_recognizer(self):
        self.is_stopping_recognizer = False
        # self.auto_speech_recognizer.start_continuous_recognition()
        self.auto_speech_recognizer.recognize_once_async()
        self.max_len_recogized_words = 0

    def stop_recognizer(self):
        self.is_stopping_recognizer = True
        # self.auto_speech_recognizer.stop_continuous_recognition_async()
        self.max_len_recogized_words = 0

    def stop_recognizer_sync(self):
        self.is_stopping_recognizer = True
        # self.auto_speech_recognizer.stop_continuous_recognition()
        self.max_len_recogized_words = 0

    def _azure_stt_input_auto_recognizing(self, evt):
        cur_recognized_text = evt.result.text
        size = len(cur_recognized_text)
        if size > self.max_len_recogized_words:
            self.max_len_recogized_words = size
        print("RECOGNIZING: {}".format(cur_recognized_text))

    def _azure_stt_input_auto_recognized(self, evt):
        cur_recognized_text = evt.result.text
        size = len(cur_recognized_text)
        if size > self.max_len_recogized_words:
            self.max_len_recogized_words = size
        logger.info("RECOGNIZED: {}".format(cur_recognized_text))
        if not self.is_stopping_recognizer:
            self.recognized_callback(cur_recognized_text)

    def _azure_auto_stt_recognizer_session_started(self, evt):
        logger.info(f"SESSION STARTED : {evt}")

    def _azure_auto_stt_recognizer_session_stopped(self, evt):
        logger.info(f"SESSION STOPPED : {evt}")

    def _azure_auto_stt_recognizer_canceled(self, evt):
        logger.info(f"SESSION CANCELED : {evt}")
        detailed_reason = evt.result.cancellation_details.reason
        if detailed_reason == speechsdk.CancellationReason.EndOfStream:
            logger.warning(f"SESSION CANCELED : {detailed_reason}")
            self._init_recognizer()
        elif detailed_reason == speechsdk.CancellationReason.Error:
            self._init_recognizer()
        else:
            logger.warning(f"SESSION CANCELED : {detailed_reason}")
