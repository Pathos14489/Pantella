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

            # conversation_ended = self.game_interface.load_data_when_available('_pantella_end_conversation', '')
            # conversation_ended = self.conversation_manager.conversation_ended
            # if conversation_ended.lower() == 'true':
            #     return 'goodbye'

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
        # @utils.time_it
        # def whisper_transcribe(audio, prompt):
            # if using faster_whisper (default) return based on faster_whisper's code, if not assume player wants to use server mode and send query to whisper_url set by player.
            # if self.whisper_type == 'faster_whisper':
            #     segments, info = self.transcribe_model.transcribe(audio,
            #         task=self.task,
            #         language=self.language,
            #         beam_size=self.config.beam_size,
            #         vad_filter=self.config.vad_filter,
            #         initial_prompt=prompt,
            #     )
            #     result_text = ' '.join(segment.text for segment in segments)

            #     return result_text
            # # this code queries the whispercpp server set by the user to obtain the response, this format also allows use of official openai whisper API
            # else:
            #     url = self.whisper_url
            #     if 'openai' in url:
            #         headers = {"Authorization": f"Bearer {openai.api_key}",}
            #     else:
            #         logging.warn('Whisper URL not set to OpenAI API. If you are using a custom whisper server, please ensure the server is running and the URL is correct in config.json.')
            #         headers = {"Authorization": "Bearer apikey",}
            #     data = {'model': self.model}
            #     files = {'file': open(audio, 'rb')}
            #     response = requests.post(url, headers=headers, files=files, data=data)
            #     response_data = json.loads(response.text)
            #     if 'text' in response_data:
            #         return response_data['text'].strip()

        # with self.microphone as source:
        #     try:
        #         audio = self.recognizer.listen(source, timeout=self.listen_timeout)
        #     except sr.WaitTimeoutError:
        #         return ''
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