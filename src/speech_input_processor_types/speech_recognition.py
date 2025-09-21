print('Loading speech_recognition.py...')
from src.logging import logging
from src.speech_input_processor_types.base_Speech_Input_Processor import base_Speech_Input_Processor
speech_recognition_imported = False
try:
    logging.info('Importing speech_recognition in base_speech_input_processor.py...')
    import speech_recognition as sr
except ImportError:
    logging.error('Could not import speech_recognition in base_speech_input_processor.py. Please ensure the speech_recognition package is installed and try again.')
    raise ImportError('Could not import speech_recognition in base_speech_input_processor.py. Please ensure the speech_recognition package is installed and try again.')
import src.utils as utils
logging.info('Imported required libraries in speech_recognition.py')

speech_input_processor_slug = "speech_recognition"

class Speech_Input_Processor(base_Speech_Input_Processor):
    def __init__(self, transcriber):
        global speech_input_processor_slug
        super().__init__(transcriber)
        self.stt_slug = speech_input_processor_slug

        logging.info('Initializing speech recognizer...')
        self.audio_threshold = self.config.audio_threshold
        self.listen_timeout = self.config.listen_timeout
        self.pause_threshold = self.config.pause_threshold

        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = self.pause_threshold
        self.microphone = sr.Microphone()

        if self.audio_threshold == 'auto':
            logging.info(f"Audio threshold set to 'auto'. Adjusting microphone for ambient noise...")
            logging.info("If the mic is not picking up your voice, try setting this audio_threshold value manually in config.json.\n")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=5)
        else:
            self.recognizer.dynamic_energy_threshold = False
            self.recognizer.energy_threshold = int(self.audio_threshold)
            logging.info(f"Audio threshold set to {self.audio_threshold}. If the mic is not picking up your voice, try lowering this value in config.json. If the mic is picking up too much background noise, try increasing this value.\n")
        logging.info('Speech recognizer initialized')

    def get_audio_from_mic(self) -> bytes:
        """Gets audio from the microphone and returns the audio data"""
        if not self.transcriber.initialized:
            logging.error('Speech recognizer not initialized. Please call the initialize() method before using this method.')
            raise ValueError('Speech recognizer not initialized. Please call the initialize() method before using this method.')
        with self.microphone as source:
            try:
                audio = self.recognizer.listen(source, timeout=self.listen_timeout)
            except sr.WaitTimeoutError:
                return None
        return audio.get_wav_data(convert_rate=16000)