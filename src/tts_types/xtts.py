import src.utils as utils
import src.tts_types.base_tts as base_tts
import logging
import json
import winsound
import sys
import os
from pathlib import Path
import requests

tts_slug = "xtts"
class Synthesizer(base_tts.base_Synthesizer): # Gets token count from OpenAI's embedding API -- WARNING SLOW AS HELL -- Only use if you don't want to set up the right tokenizer for your local model or if you don't know how to do that
    def __init__(self, conversation_manager):
        super().__init__(conversation_manager)
        self.xtts_data = self.config.xtts_data
        self.xtts_base_url = self.config.xtts_base_url
        self.synthesize_url_xtts = self.xtts_base_url + "/tts_to_audio/"
        self.switch_model_url = self.xtts_base_url + "/switch_model"
        self.xtts_set_tts_settings = self.xtts_base_url + "/set_tts_settings/"
        self.xtts_get_models_list = self.xtts_base_url + "/get_models_list/"
        self._set_tts_settings_and_test_if_serv_running()
        self.available_models = self._get_available_models()
        self.official_model_list = ["main","v2.0.3","v2.0.2","v2.0.1","v2.0.0"]
        logging.info(f'Available models: {self.available_models}')

    def _get_available_models(self):
        # Code to request and return the list of available models
        response = requests.get(self.xtts_get_models_list)
        return response.json() if response.status_code == 200 else []
    
    def voices(self):
        return self._get_available_models()
    
    def get_first_available_official_model(self):
        # Check in the available models list if there is an official model
        for model in self.official_model_list:
            if model in self.available_models:
                return model
        return None
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
        voice = character.voice_model
        
        logging.info('Loading voice model...')

        # Format the voice string to match the model naming convention
        voice_path = f"{voice.lower().replace(' ', '')}"
        model_voice = voice_path
        # Check if the specified voice is available
        if voice_path not in self.available_models and voice != self.last_voice:
            logging.info(f'Voice "{voice}" not in available models. Available models: {self.available_models}')
            # Use the first available official model as a fallback
            model_voice = self.get_first_available_official_model()
            if model_voice is None:
                # Handle the case where no official model is available
                raise ValueError("No available voice model found.")
            # Update the voice_path with the fallback model
            model_voice = f"{model_voice.lower().replace(' ', '')}"

        # Request to switch the voice model
        requests.post(self.switch_model_url, json={"model_name": model_voice})

        # Update the last used voice
        self.last_voice = voice

        logging.info('Voice model loaded.')
          
    @utils.time_it
    def _synthesize_line_xtts(self, line, save_path, voice, aggro=0):
        voice_path = f"{voice.lower().replace(' ', '')}"
        data = {
        'text': line,
        'speaker_wav': voice_path,
        'language': self.language,
        'save_path': save_path
        }       
        requests.post(self.synthesize_url_xtts, json=data)
          
    def synthesize(self, character, voiceline, aggro=0):
        # If the voice has changed, update it
        if character.voice_model != self.last_voice:
            self.change_voice(character)

        logging.info(f'Synthesizing voiceline: {voiceline}')

        # make voice model folder if it doesn't already exist
        if not os.path.exists(f"{self.output_path}/voicelines/{self.last_voice}"):
            os.makedirs(f"{self.output_path}/voicelines/{self.last_voice}")

        final_voiceline_file_name = 'voiceline'
        final_voiceline_file =  f"{self.output_path}/voicelines/{self.last_voice}/{final_voiceline_file_name}.wav"

        try:
            if os.path.exists(final_voiceline_file):
                os.remove(final_voiceline_file)
            if os.path.exists(final_voiceline_file.replace(".wav", ".lip")):
                os.remove(final_voiceline_file.replace(".wav", ".lip"))
        except:
            logging.warning("Failed to remove spoken voicelines")

        # Synthesize voicelines
        self._synthesize_line_xtts(voiceline, final_voiceline_file, voice, aggro)

        if not os.path.exists(final_voiceline_file):
            logging.error(f'xTTS failed to generate voiceline at: {Path(final_voiceline_file)}')
            raise FileNotFoundError()

        # check if FonixData.cdf file is besides FaceFXWrapper.exe
        cdf_path = f'{self.xtts_base_url}/plugins/lip_fuz/FonixData.cdf'
        if not os.path.exists(Path(cdf_path)):
            logging.error(f'Could not find FonixData.cdf in "{Path(cdf_path).parent}" required by FaceFXWrapper. Look for the Lip Fuz plugin of xVASynth.')
            raise FileNotFoundError()

        # generate .lip file from the .wav file with FaceFXWrapper
        face_wrapper_executable = f'{self.xtts_base_url}/plugins/lip_fuz/FaceFXWrapper.exe';
        if os.path.exists(face_wrapper_executable):
            # Run FaceFXWrapper.exe
            self.run_command(f'{face_wrapper_executable} "Skyrim" "USEnglish" "{self.xtts_base_url}/plugins/lip_fuz/FonixData.cdf" "{final_voiceline_file}" "{final_voiceline_file.replace(".wav", "_r.wav")}" "{final_voiceline_file.replace(".wav", ".lip")}" "{voiceline}"')
        else:
            logging.error(f'Could not find FaceFXWrapper.exe in "{Path(face_wrapper_executable).parent}" with which to create a Lip Sync file, download it from: https://github.com/Nukem9/FaceFXWrapper/releases')
            raise FileNotFoundError()

        # remove file created by FaceFXWrapper
        if os.path.exists(final_voiceline_file.replace(".wav", "_r.wav")):
            os.remove(final_voiceline_file.replace(".wav", "_r.wav"))

        # if Debug Mode is on, play the audio file
        if (self.debug_mode == '1') & (self.play_audio_from_script == '1'):
            winsound.PlaySound(final_voiceline_file, winsound.SND_FILENAME)

        return final_voiceline_file
    