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
import random
logging.info("Imported required libraries in xtts_api.py")

tts_slug = "xtts_api"
default_settings = {
    "temperature": 0.75,
    "length_penalty": 1.0,
    "repetition_penalty": 3.0,
    "top_k": 40,
    "top_p": 0.80,
    "speed": 1.25,
}
settings_description = {
    "temperature": "The temperature of the generated audio. 0.75 is normal temperature, 0.5 is low temperature, 1.0 is high temperature.",
    "length_penalty": "The length penalty of the generated audio. 1.0 is normal length penalty, 0.5 is low length penalty, 1.5 is high length penalty.",
    "repetition_penalty": "The repetition penalty of the generated audio. 3.0 is normal repetition penalty, 2.0 is low repetition penalty, 4.0 is high repetition penalty.",
    "top_k": "The top-k sampling of the generated audio. 40 is normal top-k, 20 is low top-k, 60 is high top-k.",
    "top_p": "The top-p sampling of the generated audio. 0.80 is normal top-p, 0.50 is low top-p, 0.90 is high top-p.",
}
options = {}
settings = {}
loaded = False
imported = True
description = "xTTS 2 is a really good TTS for human sounding voices, but it struggles for dragons, robots, etc. It is basically unusable on CPU and requires an additional 4GB of VRAM usage on top of Skyrim to run it, and it's slower than xVASynth or PiperTTS."
class Synthesizer(base_tts.base_Synthesizer): 
    def __init__(self, conversation_manager):
        global tts_slug, default_settings, loaded
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._default_settings = default_settings
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
        self.speaker_wavs_folders.append(os.path.abspath(self.xtts_api_dir + "speakers\\" if self.xtts_api_dir.endswith("\\") else self.xtts_api_dir + "\\speakers\\"))
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
        self.set_model(self.default_model)
        self._voices = None
        # self.official_model_list = ["main","v2.0.3","v2.0.2","v2.0.1","v2.0.0"]
        logging.config(f'xTTS_api - Available xTTS_api models: {self.available_models()}')
        logging.config(f'xTTS_api - Available xTTS_api voices: {self.voices()}')
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("Ecks T T S is ready to go.",str(random_voice))
        loaded = True

    @property
    def speaker_wavs_folders(self):
        if self.config.linux_mode:
            speaker_wavs_folders = [
                os.path.abspath(f"./data/voice_samples/{self.config.game_id}/"),
            ]
        else:
            speaker_wavs_folders = [
                os.path.abspath(f".\\data\\voice_samples\\{self.config.game_id}\\"),
            ]
        for addon_slug in self.config.addons: # Add the speakers folder from each addon to the list of speaker wavs folders
            addon = self.config.addons[addon_slug]
            if "speakers" in addon["addon_parts"]: 
                if self.config.linux_mode:
                    addon_speaker_wavs_folder = os.path.abspath(f"./addons/{addon_slug}/speakers/")
                else:
                    addon_speaker_wavs_folder = self.config.addons_dir + addon_slug + "\\speakers\\"
                if os.path.exists(addon_speaker_wavs_folder):
                    speaker_wavs_folders.append(addon_speaker_wavs_folder)
                else:
                    logging.error(f'speakers folder not found at: {addon_speaker_wavs_folder}')
        # make all the paths absolute
        speaker_wavs_folders = [os.path.abspath(folder) for folder in speaker_wavs_folders]
        return speaker_wavs_folders
    
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
    def default_temperature(self):
        return self.config.xtts_api_default_temperature
    @property
    def default_length_penalty(self):
        return self.config.xtts_api_default_length_penalty
    @property
    def default_repetition_penalty(self):
        return self.config.xtts_api_default_repetition_penalty
    @property
    def default_top_k(self):
        return self.config.xtts_api_default_top_k
    @property
    def default_top_p(self):
        return self.config.xtts_api_default_top_p
    @property
    def default_speed(self):
        return self.config.xtts_api_default_speed
    @property
    def enable_text_splitting(self):
        return self.config.xtts_api_enable_text_splitting
    @property
    def stream_chunk_size(self):
        return self.config.xtts_api_stream_chunk_size
    @property
    def default_voice_model_settings(self):
        return {
            "temperature": self.default_temperature,
            "length_penalty": self.default_length_penalty,
            "repetition_penalty": self.default_repetition_penalty,
            "top_k": self.default_top_k,
            "top_p": self.default_top_p,
            "speed": self.default_speed,
            "enable_text_splitting": self.enable_text_splitting,
            "stream_chunk_size": self.stream_chunk_size,
            "tts_language_code": self.language["tts_language_code"],
        }
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
            if "voice_samples" in addon["addon_parts"]:
                addon_latents_folder = self.config.addons_dir + addon_slug + "\\voice_samples\\"
                if os.path.exists(addon_latents_folder):
                    voice_latent_folders.append(addon_latents_folder)
                else:
                    logging.error(f'voice_samples folder not found at: {addon_latents_folder}')
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
                if base_lang in response:
                    response = response[base_lang]["speakers"]
                    response.sort()
            response = [voice for voice in response if voice not in self.config.xtts_api_banned_voice_models] 
            self._voices = response
        for banned_voice in self.config.xtts_api_banned_voice_models:
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
            print("Checking if xTTS server is running...", self.default_voice_model_settings)
            response = requests.post(self.xtts_set_tts_settings, json=self.default_voice_model_settings)
            response.raise_for_status()  # If the response contains an HTTP error status code, 
            return True
        except:
            return False
        
    def set_settings(self, settings):
        """Set the xTTS settings"""
        try:
            response = requests.post(self.xtts_set_tts_settings, json=settings)
            response.raise_for_status()  # If the response contains an HTTP error status code, raise an exception
            logging.info(f'Successfully set xTTS settings: {settings}')
            return True
        except Exception as e:
            logging.error(f'Failed to set xTTS settings: {settings}')
            logging.error(e)
            tb = traceback.format_exc()
            logging.error(tb)
            return False

    def run_tts(self):
        """Run the xTTS server -- Required for Pantella to manage addon voice lantents"""
        try:
            logging.info(f'CWD: {os.getcwd()} - xTTS_API CWD: {self.config.xtts_api_dir}')
            speaker_wavs_folders = ["\""+folder+"\"" for folder in self.speaker_wavs_folders]
            voice_latent_folders = ["\""+folder+"\"" for folder in self.voice_latent_folders]
            if self.config.linux_mode:
                speaker_wavs_folders = [folder.replace("\\","/") for folder in speaker_wavs_folders]
                voice_latent_folders = [folder.replace("\\","/") for folder in voice_latent_folders]
            command = f'{self.config.python_binary} -m xtts_api_server -sf {",".join(speaker_wavs_folders)} -lsf {",".join(voice_latent_folders)}'
            # start the process without waiting for a response
            if self.config.linux_mode:
                logging.info(f'Running xTTS API server for Linux with command: {command}')
                threading.Thread(target=subprocess.run, args=(command), kwargs={'shell': True, 'cwd': self.config.xtts_api_dir}).start()
            else:
                logging.info(f'Running xTTS API server for Windows with command: {command}')
                subprocess.Popen(command, cwd=self.config.xtts_api_dir)
        except Exception as e:
            logging.error(f'Could not run xTTS API. Ensure that the paths "{self.config.xtts_api_dir}" and "{self.config.python_binary}" are correct.')
            logging.error(e)
            tb = traceback.format_exc()
            logging.error(tb)
            input('\nPress any key to stop Pantella...')
            raise e

    @utils.time_it
    def change_voice(self, character_or_voice_model, settings=None):
        """Change the voice model to the character's voice model if it exists, else use the default model"""
        if type(character_or_voice_model) == str:
            voice_model = character_or_voice_model
        else:
            voice_model = self.get_valid_voice_model(character_or_voice_model) # character.voice_model
        logging.info(f'Checking for Custom xTTS Model for {voice_model}...') 
        if voice_model in self.available_models():
            logging.info(f'Custom xTTS Model found for {voice_model}!')
            self.set_model(voice_model)
        else:
            logging.info(f'Custom xTTS Model not found for {voice_model}! Using default model...')
            self.set_model(self.default_model)
        # settings = self.voice_model_settings(character)
        if settings == None:
            self.set_settings(settings)
          
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
            options.append(character.voice_folder)
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
    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize a line using the xTTS API"""
        base_lang = settings.get("tts_language_code", self.language["tts_language_code"])
        logging.output(f'{self.tts_slug} - synthesizing {voiceline} with voice model "{voice_model}"...')
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
            logging.error(e)
            raise FileNotFoundError()
        logging.output(f'{self.tts_slug} - synthesized {voiceline} with voice model "{voice_model}"')