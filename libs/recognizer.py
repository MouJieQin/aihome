import azure.cognitiveservices.speech as speechsdk
from typing import Dict, Callable


class Recognizer:
    def __init__(self, configure: Dict, recognized_callback: Callable):
        self.azure_config = configure["azure"]
        self.azure_key = self.azure_config["key"]
        self.azure_region = self.azure_config["region"]
        self.recognized_callback = recognized_callback
        self.is_stopping_recognizer = False
        speech_config = speechsdk.SpeechConfig(
            subscription=self.azure_key,
            region=self.azure_region,
            speech_recognition_language="zh-CN",
        )

        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        self.auto_speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
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
            lambda evt: print("CANCELED {}".format(evt))
        )

    def is_stopping(self):
        return self.is_stopping_recognizer

    def start_recognizer(self):
        self.is_stopping_recognizer = False
        self.auto_speech_recognizer.start_continuous_recognition()

    def stop_recognizer(self):
        self.is_stopping_recognizer = True
        self.auto_speech_recognizer.stop_continuous_recognition_async()

    def stop_recognizer_sync(self):
        self.auto_speech_recognizer.stop_continuous_recognition()

    def _azure_stt_input_auto_recognizing(self, evt):
        cur_recognized_text = evt.result.text
        print("RECOGNIZING: {}".format(cur_recognized_text))

    def _azure_stt_input_auto_recognized(self, evt):
        cur_recognized_text = evt.result.text
        print("RECOGNIZED: {}".format(cur_recognized_text))
        if not self.is_stopping_recognizer:
            self.recognized_callback(cur_recognized_text)

    def _azure_auto_stt_recognizer_session_started(self, evt):
        print(f"SESSION STARTED : {evt}")

    def _azure_auto_stt_recognizer_session_stopped(self, evt):
        print(f"SESSION STOPPED : {evt}")
