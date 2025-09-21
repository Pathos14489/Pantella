print('Loading base_speech_input_processor.py...')
from src.logging import logging
logging.info('Imported required libraries in base_speech_input_processor.py')

speech_input_processor_slug = "base_speech_input_processor"

class base_Speech_Input_Processor:
    def __init__(self, transcriber):
        global speech_input_processor_slug
        self.transcriber = transcriber
        self.game_interface = self.transcriber.game_interface
        self.speech_input_processor_slug = speech_input_processor_slug
        self.conversation_manager = self.game_interface.conversation_manager
        self.config = self.conversation_manager.config
        self.language = self.config.stt_language

    def get_audio_from_mic(self) -> bytes:
        """Gets audio from the microphone and returns the audio data"""
        logging.error("get_audio_from_mic method not implemented in base_Speech_Input_Processor. Please use a subclass of base_Speech_Input_Processor. If you're adding a new Speech Input Processor type, you must implement this method.")
        raise NotImplementedError