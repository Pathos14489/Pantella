print('Loading base_whisper.py...')
from src.logging import logging
try:
    logging.info('Importing speech_recognition in base_whisper.py...')
    import speech_recognition as sr
except ImportError:
    logging.error('Could not import speech_recognition in base_whisper.py. Please ensure the speech_recognition package is installed and try again.')
    raise ImportError('Could not import speech_recognition in base_whisper.py. Please ensure the speech_recognition package is installed and try again.')
from src.stt_types.base_stt import base_Transcriber as BASE_TRANSCRIBER
import src.utils as utils
logging.info('Imported required libraries in stt.py')

stt_slug = "base_whisper_stt"

class base_Transcriber(BASE_TRANSCRIBER):
    def __init__(self, game_interface):
        global stt_slug
        super().__init__(game_interface)
        self.stt_slug = stt_slug
            
    @utils.time_it
    def whisper_transcribe(self, audio, prompt):
        logging.error('Whisper transcribe method not implemented in base_Transcriber. Please use a subclass of base_Transcriber.')
        raise NotImplementedError
    
    def transcribe_audio_file(self, audio_file_path):
        logging.info('Transcribing audio file at path: ' + audio_file_path)
        return self.whisper_transcribe(audio_file_path, "")

    def recognize_input(self, possible_names_list):
        """
        Recognize input from mic and return transcript if activation tag (assistant name) exist
        """
        logging.info('Recognizing input...')
        prompt = ",".join(possible_names_list)
        while True:
            self.game_interface.display_status('Listening...')
            transcript = self._recognize_speech_from_mic(prompt)
            transcript_cleaned = utils.clean_text(transcript)

            # common phrases hallucinated by Whisper
            if transcript_cleaned in ['', 'thank you', 'thank you for watching', 'thanks for watching', 'the transcript is from the', 'the', 'thank you very much']:
                continue

            self.game_interface.display_status('Thinking...')
            break
        return transcript

    def _recognize_speech_from_mic(self, prompt):
        """
        Capture the words from the recorded audio (audio stream --> free text).
        Transcribe speech from recorded from `microphone`.
        """
        audio = None
        while audio is None:
            logging.info('Getting audio from mic...')
            audio = self.speech_processor.get_audio_from_mic()
            if audio is None:
                logging.info('No speech detected within the timeout period. Retrying...')

        audio_file = 'player_recording.wav'
        with open(audio_file, 'wb') as file:
            file.write(audio)
        
        transcript = self.whisper_transcribe(audio_file, prompt)
        logging.info(transcript)

        return transcript