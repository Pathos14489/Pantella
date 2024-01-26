import src.utils as utils
import src.tts_types.base_tts as base_tts
import logging
import winsound
import sys
import os
from pathlib import Path
import torch
import torchaudio
import torchaudio.transforms as T
import requests
import io

tts_slug = "xtts"
class Synthesizer(base_tts.base_Synthesizer): # Gets token count from OpenAI's embedding API -- WARNING SLOW AS HELL -- Only use if you don't want to set up the right tokenizer for your local model or if you don't know how to do that
    def __init__(self, conversation_manager):
        super().__init__(conversation_manager)
        self.xtts_data = self.config.xtts_data
        self.xtts_base_url = self.config.xtts_base_url
        self.xtts_server_folder = self.config.xtts_server_folder
        self.synthesize_url_xtts = self.xtts_base_url + "/tts_to_audio/"
        # self.switch_model_url = self.xtts_base_url + "/switch_model"
        self.xtts_set_tts_settings = self.xtts_base_url + "/set_tts_settings/"
        self.xtts_get_models_list = self.xtts_base_url + "/speakers_list/"
        self._set_tts_settings_and_test_if_serv_running()
        self.available_models = self.voices()
        # self.official_model_list = ["main","v2.0.3","v2.0.2","v2.0.1","v2.0.0"]
        logging.info(f'Available models: {self.available_models}')
    
    def voices(self):
        # Code to request and return the list of available models
        response = requests.get(self.xtts_get_models_list)
        return response.json() if response.status_code == 200 else []
    
    def _set_tts_settings_and_test_if_serv_running(self):
        try:
            # Sending a POST request to the API endpoint
            logging.info(f'Attempting to connect to xTTS...')
            response = requests.post(self.xtts_set_tts_settings, json=self.xtts_data)
            response.raise_for_status() 
        except requests.exceptions.RequestException as e:
            # Log the error
            logging.error(f'Could not reach the API at "{self.xtts_set_tts_settings}". Error: {e}')
            # Wait for user input before exiting
            logging.error(f'You should run xTTS api server before running Mantella.')
            input('\nPress any key to stop Mantella...')
            sys.exit(0)

    @utils.time_it
    def change_voice(self, character):
        logging.info(f'Changing voice to {character.voice_model}...') 
        logging.info(f'(Redundant Method, xTTS does not support changing voice models as all voices are calculated at runtime)')
          
    @utils.time_it
    def _synthesize_line_xtts(self, line, save_path, voice, aggro=0):
        voice_path = f"{voice.replace(' ', '')}"
        data = {
            'text': line,
            'speaker_wav': voice_path,
            'language': self.language
        }       
        response = requests.post(self.synthesize_url_xtts, json=data)
        if response.status_code == 200: # if the request was successful, write the wav file to disk at the specified path
            audio_tensor, _ = torchaudio.load(io.BytesIO(response.content)) # load the wav file into a tensor
            audio_tensor = audio_tensor.to(torch.float32) # convert to float32
            audio_16bit = T.Resample(orig_freq=24000, new_freq=24000, resampling_method='sinc_interpolation')(audio_tensor) # resample to 24000Hz
            audio_16bit = torch.clamp(audio_16bit, -1.0, 1.0) # clamp to -1.0 to 1.0
            audio_16bit = (audio_16bit * 32767).to(torch.int16) # convert back to int16
            torchaudio.save(save_path, audio_16bit, 24000)
                

        else:
            logging.error(f'xTTS failed to generate voiceline at: {Path(save_path)}')
            raise FileNotFoundError()
          
    def synthesize(self, character, voiceline, aggro=0):
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
        self._synthesize_line_xtts(voiceline, final_voiceline_file, character.voice_model, aggro)

        if not os.path.exists(final_voiceline_file):
            logging.error(f'xTTS failed to generate voiceline at: {Path(final_voiceline_file)}')
            raise FileNotFoundError()

        self.lip_gen(voiceline, final_voiceline_file)
        self.debug(final_voiceline_file)

        return final_voiceline_file
    