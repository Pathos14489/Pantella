import src.utils as utils
import src.tts_types.base_tts as base_tts
from src.logging import logging
import sys
import os
from pathlib import Path
import requests
import io
import soundfile as sf
import numpy as np

tts_slug = "xtts_api"
class Synthesizer(base_tts.base_Synthesizer): 
    def __init__(self, conversation_manager):
        super().__init__(conversation_manager)
        self.xtts_data = self.config.xtts_data
        self.xtts_base_url = self.config.xtts_base_url
        self.xtts_server_folder = self.config.xtts_server_folder
        self.synthesize_url_xtts = self.xtts_base_url + "/tts_to_audio/"
        self.switch_model_url = self.xtts_base_url + "/switch_model"
        self.xtts_set_tts_settings = self.xtts_base_url + "/set_tts_settings/"
        self.xtts_get_speakers_list = self.xtts_base_url + "/speakers_list/"
        self.xtts_get_models_list = self.xtts_base_url + "/get_models_list/"
        self._set_tts_settings_and_test_if_serv_running()
        self.default_model = self.conversation_manager.config.default_xtts_model
        self.current_model = self.default_model
        self.set_model(self.default_model)
        # self.official_model_list = ["main","v2.0.3","v2.0.2","v2.0.1","v2.0.0"]
        logging.info(f'xTTS_api - Available models: {self.available_models()}')
        logging.info(f'xTTS_api - Available voices: {self.voices()}')
    
    def convert_to_16bit(self, input_file, output_file=None):
        if output_file is None:
            output_file = input_file
        # Read the audio file
        data, samplerate = sf.read(input_file)

        # Directly convert to 16-bit if data is in float format and assumed to be in the -1.0 to 1.0 range
        if np.issubdtype(data.dtype, np.floating):
            # Ensure no value exceeds the -1.0 to 1.0 range before conversion (optional, based on your data's characteristics)
            # data = np.clip(data, -1.0, 1.0)  # Uncomment if needed
            data_16bit = np.int16(data * 32767)
        elif not np.issubdtype(data.dtype, np.int16):
            # If data is not floating-point or int16, consider logging or handling this case explicitly
            # For simplicity, this example just converts to int16 without scaling
            data_16bit = data.astype(np.int16)
        else:
            # If data is already int16, no conversion is necessary
            data_16bit = data

        # Write the 16-bit audio data back to a file
        sf.write(output_file, data_16bit, samplerate, subtype='PCM_16')

    def voices(self):
        """Return a list of available voices"""
        # Code to request and return the list of available models
        response = requests.get(self.xtts_get_speakers_list)
        return response.json() if response.status_code == 200 else []
    
    def available_models(self):
        """Return a list of available models"""
        # Code to request and return the list of available models
        response = requests.get(self.xtts_get_models_list)
        return response.json() if response.status_code == 200 else []
    
    def set_model(self, model):
        """Set the voice model"""
        if model not in self.available_models(): # if the model is not available, log an error and raise an exception
            logging.error(f"xTTS Model {model} not available but was specifically assigned to this NPC! Please add it to the xTTS models directory for this to work. Normal users shouldn't see this error, if you do, let someone know in the Discord server. <3")
            input("Press enter to continue...")
            raise FileNotFoundError()
        if self.current_model == model: # if the model is already set, do nothing
            return
        self.current_model = model # else: set the current model to the new model
        requests.post(self.switch_model_url, json={"model_name": model}) # Request to switch the voice model
    
    def _set_tts_settings_and_test_if_serv_running(self):
        """Set the TTS settings and test if the server is running"""
        retry_count = 10
        try:
            if (retry_count > 10):
                # break loop
                logging.error('Ensure xtts is running - http://localhost:8020/docs - xTTS needs to start slightly before Mantella as it takes time to load.')
                input('\nPress any key to stop Mantella and try again...')
                sys.exit(0)

            # contact local xTTS server; ~2 second timeout
            logging.info(f'Attempting to connect to xTTS... ({retry_count})')
            retry_count -= 1
            response = requests.post(self.xtts_set_tts_settings, json=self.xtts_data)
            response.raise_for_status()  # If the response contains an HTTP error status code, raise an exception
        except requests.exceptions.RequestException as err:
            if (retry_count == 1):
                logging.info('xtts is not ready yet. Retrying in 10 seconds...')
            return self._set_tts_settings_and_test_if_serv_running() # do the web request again; LOOP!!!

    @utils.time_it
    def change_voice(self, character):
        logging.info(f'Checking for Custom xTTS Model for {character.voice_model}...') 
        if character.voice_model in self.available_models():
            logging.info(f'Custom xTTS Model found for {character.voice_model}!')
            self.set_model(character.voice_model)
        else:
            logging.info(f'Custom xTTS Model not found for {character.voice_model}! Using default model...')
            self.set_model(self.default_model)
          
    def get_valid_voice_model(self, character):
        default_voice_model = super().get_valid_voice_model(character)
        if default_voice_model == None:
            default_voice_model = character.voice_model
        basic_voice_model = f"{default_voice_model.replace(' ', '')}"
        racial_voice_model = f"{character.race}{basic_voice_model}"
        gendered_voice_model = f"{character.gender}{basic_voice_model}"
        gendered_racial_voice_model = f"{character.race}{character.gender}{basic_voice_model}"
        voice_model = None
        if character.ref_id in self.voices():
            voice_model = character.ref_id
        elif character.name in self.voices():
            voice_model = character.name
        elif gendered_racial_voice_model in self.voices():
            voice_model = gendered_racial_voice_model
        elif gendered_voice_model in self.voices():
            voice_model = gendered_voice_model
        elif racial_voice_model in self.voices():
            voice_model = racial_voice_model
        elif basic_voice_model in self.voices():
            voice_model = basic_voice_model
        elif default_voice_model in self.voices():
            voice_model = default_voice_model
        elif character.voice_model in self.voices():
            voice_model = character.voice_model
            
        if self.crashable and voice_model == None:
            logging.error(f'Voice model {voice_model} not available! Please add it to the xTTS voices list.')
            input("Press enter to continue...")
            raise FileNotFoundError()
        
        return voice_model

    @utils.time_it
    def _synthesize_line_xtts(self, line, save_path, character, aggro=0):
        """Synthesize a line using the xTTS API"""
        voice_model = self.get_valid_voice_model(character)
        data = {
            'text': line,
            'speaker_wav': voice_model,
            'language': character.language_code
        }
        print(data)
        response = requests.post(self.synthesize_url_xtts, json=data)
        if response.status_code == 200: # if the request was successful, write the wav file to disk at the specified path
            self.convert_to_16bit(io.BytesIO(response.content), save_path)
        else:
            logging.error(f'xTTS failed to generate voiceline at: {Path(save_path)}')
            raise FileNotFoundError()
          
    def synthesize(self, voiceline, character, aggro=0):
        logging.info(f'Synthesizing voiceline: {voiceline}')
        self.change_voice(character)
        # make voice model folder if it doesn't already exist
        if not os.path.exists(f"{self.output_path}/voicelines/{character.voice_model}"):
            os.makedirs(f"{self.output_path}/voicelines/{character.voice_model}")

        final_voiceline_file_name = 'voiceline'
        final_voiceline_file =  f"{self.output_path}/voicelines/{character.voice_model}/{final_voiceline_file_name}.wav"

        try:
            if os.path.exists(final_voiceline_file):
                os.remove(final_voiceline_file)
            if os.path.exists(final_voiceline_file.replace(".wav", ".lip")):
                os.remove(final_voiceline_file.replace(".wav", ".lip"))
        except:
            logging.warning("Failed to remove spoken voicelines")

        # Synthesize voicelines
        self._synthesize_line_xtts(voiceline, final_voiceline_file, character, aggro)

        if not os.path.exists(final_voiceline_file):
            logging.error(f'xTTS failed to generate voiceline at: {Path(final_voiceline_file)}')
            raise FileNotFoundError()

        self.lip_gen(voiceline, final_voiceline_file)
        self.debug(final_voiceline_file)

        return final_voiceline_file
    