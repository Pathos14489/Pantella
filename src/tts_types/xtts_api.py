print("Loading xtts_api.py...")
from src.logging import logging
import src.utils as utils
import src.tts_types.base_tts as base_tts
import os
from pathlib import Path
import requests
import time
import subprocess
import threading
import traceback
import io
import numpy as np
logging.info("Imported required libraries in xtts_api.py")

tts_slug = "xtts_api"
class Synthesizer(base_tts.base_Synthesizer): 
    def __init__(self, conversation_manager):
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        if not self.xtts_api_dir == "" or not self.xtts_api_dir == None or not self.xtts_api_dir.lower() == "none":
            if conversation_manager.config.linux_mode:
                if not os.path.exists(self.xtts_api_dir+"/xtts_api_server/__init__.py"):
                    logging.error(f'xTTS API server not found at: {self.config.xtts_api_dir}')
                    logging.error(f'Please download the xTTS API server from: https://github.com/Pathos14489/xtts-api-server-pantella and place it in the directory specified in the config file, or update where the config file is looking for the xTTS API directory.')
                    input("Press enter to continue...")
                    raise FileNotFoundError()
            else:
                if not os.path.exists(self.xtts_api_dir+"\\xtts_api_server\\__init__.py"):
                    logging.error(f'xTTS API server not found at: {self.config.xtts_api_dir}')
                    logging.error(f'Please download the xTTS API server from: https://github.com/Pathos14489/xtts-api-server-pantella and place it in the directory specified in the config file, or update where the config file is looking for the xTTS API directory.')
                    input("Press enter to continue...")
                    raise FileNotFoundError()
        logging.info(f'xTTS API voice latent folders: {self.voice_latent_folders}')
        self.speaker_wavs_folders = [
            self.xtts_api_dir + "speakers\\" if self.xtts_api_dir.endswith("\\") else self.xtts_api_dir + "\\speakers\\",
            os.path.abspath(".\\data\\voice_samples\\")
        ]
        for addon_slug in self.config.addons:
            addon = self.config.addons[addon_slug]
            if "speakers" in addon["addon_parts"]:
                addon_speaker_wavs_folder = self.config.addons_dir + addon_slug + "\\speakers\\"
                if os.path.exists(addon_speaker_wavs_folder):
                    self.speaker_wavs_folders.append(addon_speaker_wavs_folder)
                else:
                    logging.error(f'speakers folder not found at: {addon_speaker_wavs_folder}')
        # make all the paths absolute
        self.speaker_wavs_folders = [os.path.abspath(folder) for folder in self.speaker_wavs_folders]
        logging.info(f'xTTS API speaker wavs folders: {self.speaker_wavs_folders}')
        if self.is_running():
            logging.warning(f'xTTS_API is already running. Voice latents added by addons will not be available until the server is closed and restarted by Pantella.')
        else:
            logging.info(f'Starting xTTS_API server...')
            self.run_tts()  # Start xTTS_API server if it isn't already running
        self.times_checked = 0
        
        while not self.is_running() and self.times_checked < 40:  # Check if xTTS_API is running
            time.sleep(2)  # Wait for xTTS_API server to start
            if self.times_checked == 20:
                logging.error(f'xTTS_API server is taking longer than expected to start. Please check the xTTS_API server logs for any errors. Or your computer may be a bit slower than expected.')
            self.times_checked += 1
        if self.times_checked >= 20:
            logging.error(f'xTTS_API server failed to start. Please check the xTTS_API server logs for any errors.')
            input('\nPress any key to stop Pantella...')
            raise Exception(f'xTTS_API server failed to start. Please check the xTTS_API server logs for any errors.')
        
        self.default_model = self.conversation_manager.config.default_xtts_api_model
        self.current_model = self.default_model
        self.mantella_server = False
        self.set_model(self.default_model)
        self._voices = None
        # self.official_model_list = ["main","v2.0.3","v2.0.2","v2.0.1","v2.0.0"]
        logging.config(f'xTTS_api - Available xTTS_api models: {self.available_models()}')
        logging.config(f'xTTS_api - Available xTTS_api voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = np.random.choice(self.voices())
            self._say("Ecks T T S is ready to go.",str(random_voice))

    @property
    def xtts_api_base_url(self):
        return self.config.xtts_api_base_url
    @property
    def synthesize_url_xtts(self):
        return self.xtts_api_base_url + "/tts_to_audio/"
    @property
    def switch_model_url(self):
        return self.xtts_api_base_url + "/switch_model"
    @property
    def xtts_set_tts_settings(self):
        return self.xtts_api_base_url + "/set_tts_settings/"
    @property
    def xtts_get_speakers_list(self):
        return self.xtts_api_base_url + "/speakers_list/"
    @property
    def xtts_get_models_list(self):
        return self.xtts_api_base_url + "/get_models_list/"
    @property
    def xtts_data(self):
        return self.config.xtts_api_data
    @property
    def xtts_api_dir(self):
        return self.config.xtts_api_dir
    @property
    def voice_latent_folders(self):
        voice_latent_folders = [
            self.xtts_api_dir + "latent_speaker_folder\\" if self.xtts_api_dir.endswith("\\") else self.xtts_api_dir + "\\latent_speaker_folder\\",
        ]
        for addon_slug in self.config.addons:
            addon = self.config.addons[addon_slug]
            if "xtts_voice_latents" in addon["addon_parts"]:
                addon_latents_folder = self.config.addons_dir + addon_slug + "\\xtts_voice_latents\\"
                if os.path.exists(addon_latents_folder):
                    voice_latent_folders.append(addon_latents_folder)
                else:
                    logging.error(f'xtts_voice_latents folder not found at: {addon_latents_folder}')
        # make all the paths absolute
        return [os.path.abspath(folder) for folder in voice_latent_folders]

    def voices(self):
        """Return a list of available voices"""
        # Code to request and return the list of available models
        if self._voices == None:
            response = requests.get(self.xtts_get_speakers_list)
            if response.status_code != 200:
                logging.error(f'Failed to get xTTS voices list: {response.status_code}')
                return []
            response = response.json()
            if type(response) == dict:
                base_lang = self.language["tts_language_code"]
                self.mantella_server = True
                if base_lang in response:
                    response = response[base_lang]["speakers"]
                    response.sort()
            response = [voice for voice in response if voice not in self.config.xtts_api_banned_voice_models] 
            self._voices = response
        for banned_voice in self.config.xtts_banned_voice_models:
            if banned_voice in self._voices:
                self._voices.remove(banned_voice)
        return self._voices
    
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
    
    def is_running(self):
        """Check if the xTTS server is running"""
        try:
            response = requests.post(self.xtts_set_tts_settings, json=self.xtts_data)
            response.raise_for_status()  # If the response contains an HTTP error status code, 
            return True
        except:
            return False


    def run_tts(self):
        """Run the xTTS server -- Required for Pantella to manage addon voice lantents"""
        try:
            logging.info(f'CWD: {os.getcwd()} - xTTS_API CWD: {self.config.xtts_api_dir}')
            speaker_wavs_folders = ["\""+folder+"\"" for folder in self.speaker_wavs_folders]
            voice_latent_folders = ["\""+folder+"\"" for folder in self.voice_latent_folders]
            command = f'{self.config.python_binary} -m xtts_api_server -sf {",".join(speaker_wavs_folders)} -lsf {",".join(voice_latent_folders)}'
            # start the process without waiting for a response
            if not self.config.linux_mode:
                logging.info(f'Running xTTS API server for Windows with command: {command}')
                subprocess.Popen(command, cwd=self.config.xtts_api_dir)
            else:
                logging.info(f'Running xTTS API server for Linux with command: {command}')
                threading.Thread(target=subprocess.run, args=(command), kwargs={'shell': True, 'cwd': self.config.xtts_api_dir}).start()
        except Exception as e:
            logging.error(f'Could not run xTTS API. Ensure that the paths "{self.config.xtts_api_dir}" and "{self.config.python_binary}" are correct.')
            logging.error(e)
            tb = traceback.format_exc()
            logging.error(tb)
            input('\nPress any key to stop Pantella...')
            raise e

    @utils.time_it
    def change_voice(self, character):
        """Change the voice model to the character's voice model if it exists, else use the default model"""
        voice_model = self.get_valid_voice_model(character)
        logging.info(f'Checking for Custom xTTS Model for {voice_model}...') 
        if voice_model in self.available_models():
            logging.info(f'Custom xTTS Model found for {voice_model}!')
            self.set_model(voice_model)
        else:
            logging.info(f'Custom xTTS Model not found for {voice_model}! Using default model...')
            self.set_model(self.default_model)
          
    def get_valid_voice_model(self, character, crashable=None, multi_tts=True, log=True):
        """Get the valid voice model for the character from the available voices - Order of preference: voice_model, voice_model without spaces, lowercase voice_model, uppercase voice_model, lowercase voice_model without spaces, uppercase voice_model without spaces"""
        if crashable == None:
            crashable = self.crashable
        if not multi_tts:
            default_voice_model = super().get_valid_voice_model(character,False)
        else:
            default_voice_model = None
        if type(character) == str:
            if default_voice_model == None:
                default_voice_model = character
            basic_voice_model = f"{default_voice_model.replace(' ', '')}"
        else:
            if default_voice_model == None:
                default_voice_model = character.voice_model
            basic_voice_model = f"{default_voice_model.replace(' ', '')}"
            racial_voice_model = f"{character.race}{basic_voice_model}"
            gendered_voice_model = f"{character.gender}{basic_voice_model}"
            gendered_racial_voice_model = f"{character.race}{character.gender}{basic_voice_model}"
        if type(character) == str:
            options = [default_voice_model, basic_voice_model]
        else:
            options = [default_voice_model, basic_voice_model, racial_voice_model, gendered_voice_model, gendered_racial_voice_model]
        captitalized_options = [option.capitalize() for option in options]
        lower_options = [option.lower() for option in options]
        upper_options = [option.upper() for option in options]
        lower_options_no_spaces = [option.replace(' ', '') for option in lower_options]
        options = options + captitalized_options + lower_options + upper_options + lower_options_no_spaces
        if type(character) != str:
            options.append(character.skyrim_voice_folder)
            if log:
                logging.info(f'Checking for valid voice model for "{character.name}" amongst:', options)
        else:
            if log:
                logging.info(f'Checking for valid voice model for "{character}" amongst:', options)
        voice_model = None
        for option in options:
            if option in self.voices():
                if log:
                    logging.info(f'Voice model \'{option}\' is available for xTTS_api!')
                voice_model = option
                break
        if voice_model == None:
            if log:
                logging.error(f'Voice model \'{basic_voice_model}\' not available in xtts_api! Please add it to the xTTS latents directory, or put a sample of the voice in the speakers directory then restart the xTTS server and Pantella.')
        if crashable and voice_model == None:
            input("Press enter to continue...")
            raise FileNotFoundError()
        
        return voice_model

    @utils.time_it
    def _synthesize(self, voiceline, character, voiceline_location, aggro=0):
        """Synthesize a line using the xTTS API"""
        if type(character) == str:
            voice_model = character
            base_lang = self.language["tts_language_code"]
        else:
            voice_model = self.get_valid_voice_model(character)
            base_lang = character.tts_language_code
        data = {
            'text': voiceline,
            'speaker_wav': voice_model,
            'language': base_lang
        }
        # print(data)
        try:
            response = requests.post(self.synthesize_url_xtts, json=data)
            if response.status_code == 200: # if the request was successful, write the wav file to disk at the specified path
                self.convert_to_16bit(io.BytesIO(response.content), voiceline_location)
            else:
                logging.error(f'xTTS failed to generate voiceline at: {Path(voiceline_location)}')
                raise FileNotFoundError()
        except Exception as e:
            logging.error(f'xTTS failed to generate voiceline at: {Path(voiceline_location)}')
            raise FileNotFoundError()