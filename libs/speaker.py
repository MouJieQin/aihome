from pygame import mixer
import os
import threading
import asyncio
from typing import Dict, Optional
from libs.log_config import logger
import azure.cognitiveservices.speech as speechsdk

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"


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
        mixer.init()
        # Cache loaded audio files
        self.audio_cache = {}
        self._init_speech_synthesizer()

    def _init_speech_synthesizer(self, voice_name: str = "zh-CN-XiaochenNeural"):
        """Initialize the speech synthesizer."""
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

    def _handle_tts_result(
        self, tts_result_future, text_to_speak: str, file_name: Optional[str] = None
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

    def speak_text(self, text: str):
        """Speak the given text in real-time."""
        self.real_time_speech_synthesizer.speak_text(text)

    def start_speaking_text(self, text: str):
        """Start speaking the given text in real-time."""
        self.real_time_speech_synthesizer.start_speaking_text(text)

    def tts(self, text: str) -> bool:
        """Perform text-to-speech synthesis and handle the result."""
        result = self.real_time_speech_synthesizer.speak_text_async(text)
        return self._handle_tts_result(result, text)

    async def _play_audio_core(
        self, vfile: str, is_cache: bool, event: Optional[asyncio.Event]
    ):
        """Core logic for playing audio."""
        try:
            if not is_cache:
                mixer.music.load(vfile)
                mixer.music.play()
                while mixer.music.get_busy() and (event is None or not event.is_set()):
                    await asyncio.sleep(0.1)
                if event and event.is_set():
                    mixer.music.stop()
            else:
                if vfile not in self.audio_cache:
                    sound = mixer.Sound(vfile)
                    self.audio_cache[vfile] = sound
                else:
                    sound = self.audio_cache[vfile]
                channel = sound.play()
                while (
                    channel
                    and channel.get_busy()
                    and (event is None or not event.is_set())
                ):
                    await asyncio.sleep(0.1)
                if event and event.is_set() and channel:
                    channel.stop()
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
            if vfile == self.audio_files["start_record"]:
                asyncio.run(self.play_audio(vfile, is_cache))

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
