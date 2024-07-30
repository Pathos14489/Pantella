print('Loading faster_whisper.py...')
from src.logging import logging
from src.stt_types.base_whisper import base_Transcriber
faster_whisper_imported = False
try:
    logging.info('Importing faster-whisper...')
    from faster_whisper import WhisperModel
    faster_whisper_imported = True
except ImportError as e:
    logging.warning("Could not import faster-whisper. Please make sure you have it installed by running 'pip install faster-whisper'.")
    logging.warning(e)
import src.utils as utils
logging.info('Imported required libraries in faster_whisper.py')

stt_slug = "faster_whisper"

class Transcriber(base_Transcriber):
    def __init__(self, game_interface):
        global stt_slug
        super().__init__(game_interface)
        self.stt_slug = stt_slug
        if not faster_whisper_imported:
            logging.error("faster-whisper not imported. Please make sure you have it installed by running 'pip install faster-whisper'. Check your log file for more information.")
            raise ImportError("faster-whisper not imported. Please make sure you have it installed by running 'pip install faster-whisper'. Check your log file for more information.")

    def initialize(self):
        super().initialize()
        self.transcribe_model = WhisperModel(
            self.config.whisper_model,
            device=self.config.whisper_process_device,
            compute_type=self.config.whisper_compute_type,
            cpu_threads=self.config.whisper_cpu_threads
        )

    def unload(self):
        super().unload()
        logging.info('Unloading faster-whisper transcribe_model...')
        del self.transcribe_model
        
    @utils.time_it
    def whisper_transcribe(self, audio, prompt=None):
        logging.info('Transcribing audio using faster-whisper...')
        if prompt is None:
            logging.info('Prompt is None. Transcribing audio without prompt...')
            prompt = ''
        task = "transcribe"
        if self.config.stt_translate:
            # translate to English
            task = "translate"
        segments, info = self.transcribe_model.transcribe(audio,
            task=task,
            language=self.language,
            beam_size=self.config.beam_size,
            vad_filter=self.config.vad_filter,
            initial_prompt=prompt,
        )
        result_text = ' '.join(segment.text for segment in segments)

        return result_text