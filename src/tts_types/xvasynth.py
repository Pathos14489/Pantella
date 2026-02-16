print("Loading xvasynth.py")
from src.logging import logging, time
import src.utils as utils
import src.tts_types.base_tts as base_tts
import requests
import subprocess
import os
import soundfile as sf
import json
import re
import numpy as np
import requests
import threading
import traceback
import random
logging.info("Imported required libraries in xVASynth TTS")


ttw_voice_mapping = { # For converting between xVASynth Character Names and in game voice models for FNV/TTW
    # F3 voices
    "Amata": "FemaleUniqueAmata",
    "Butch": "MaleUniqueButch",
    "Colonel Autumn": "MaleUniqueAutumn",
    "Dad": "MaleUniqueDad",
    "President Eden": "MaleUniquePresident",
    "Elder Lyons": "MaleUniqueElderLyons",
    "Harkness": "MaleUniqueHarkness",
    "Moira": "FemaleUniqueMoira",
    "Robot MrHandy": "RobotMisterHandyDC",
    "Tenpenny": "MaleUniqueTenpenny",
    "Three Dog (Radio)": "MaleUniqueThreeDog",
    # FNV voices
    "Arcade": "MaleUniqueArcade",
    "Cass": "FemaleUniqueCass",
    "Doc Mitchell": "MaleUniqueDocMitchell",
    "Lanius": "MaleUniqueLanius",
    "MaleAdult01Defaultb": "MaleAdult01DefaultB",
    "Mr. House": "MaleUniqueMrHouse",
    "Mr New Vegas": "MaleUniqueMrNewVegas",
    "Narrator": "MaleUniqueNarrator",
    "The King": "MaleUniqueTheKing",
    "Ulysses": "NVDLC04MaleUniqueUlysses",
    "Veronica": "FemaleUniqueVeronica",
    "Yes Man":"RobotYesMan",
    "Femaleadult09": "FemaleAdult09",
    "FemaleAdult07, FemaleAdult12": "FemaleAdult07",
    "FemaleAdult07, FemaleAdult12": "FemaleAdult12"
}
reverse_ttw_voice_mapping = {v: k for k, v in ttw_voice_mapping.items()} # For converting between xVASynth Character Names and in game voice models for FNV/TTW
model_filename_mapping = {
    "falloutnv": {
        "MaleUniqueTheKing": "the_king",
    }
}

tts_slug = "xvasynth"
default_settings = {
    "pace": 1.0,
    "use_sr": True,
    "use_cleanup": True,
    "tts_language_code": "en",
}
settings_description = {
    "pace": "The pace of the generated audio. 1.0 is normal pace, 0.5 is half pace, 2.0 is double pace.",
    "use_sr": "Whether to use super resolution on the generated audio. This can improve the quality of the audio, but may take longer to generate.",
    "use_cleanup": "Whether to use cleanup on the generated audio. This can improve the quality of the audio, but may take longer to generate.",
    "tts_language_code": "The language code of the generated audio. This is used to determine the language of the audio, and can be used to improve the quality of the audio.",
}
options = {
    "tts_language_code": [
        {
            "name": "English",
            "value": "en",
            "description": "English",
            "default": True,
            "disabled": False
        },
        {
            "name": "Spanish",
            "value": "es",
            "description": "Spanish",
            "default": False,
            "disabled": False
        },
        {
            "name": "French",
            "value": "fr",
            "description": "French",
            "default": False,
            "disabled": False
        },
        {
            "name": "German",
            "value": "de",
            "description": "German",
            "default": False,
            "disabled": False
        },
        {
            "name": "Italian",
            "value": "it",
            "description": "Italian",
            "default": False,
            "disabled": False
        },
        {
            "name": "Portuguese",
            "value": "pt",
            "description": "Portuguese",
            "default": False,
            "disabled": False
        },
        {
            "name": "Russian",
            "value": "ru",
            "description": "Russian",
            "default": False,
            "disabled": False
        },
        {
            "name": "Chinese Mandarin",
            "value": "zh",
            "description": "Chinese Mandarin",
            "default": False,
            "disabled": False
        },
        {
            "name": "Japanese",
            "value": "jp",
            "description": "Japanese",
            "default": False,
            "disabled": False
        },
        {
            "name": "Korean",
            "value": "ko",
            "description": "Korean",
            "default": False,
            "disabled": False
        },
        {
            "name": "Hindi",
            "value": "hi",
            "description": "Hindi",
            "default": False,
            "disabled": False
        },
        {
            "name": "Arabic",
            "value": "ar",
            "description": "Arabic",
            "default": False,
            "disabled": False
        },
        {
            "name": "Turkish",
            "value": "tr",
            "description": "Turkish",
            "default": False,
            "disabled": False
        },
        {
            "name": "Swedish",
            "value": "sv",
            "description": "Swedish",
            "default": False,
            "disabled": False
        },
        {
            "name": "Danish",
            "value": "da",
            "description": "Danish",
            "default": False,
            "disabled": False
        },
        {
            "name": "Finnish",
            "value": "fi",
            "description": "Finnish",
            "default": False,
            "disabled": False
        },
        {
            "name": "Polish",
            "value": "pl",
            "description": "Polish",
            "default": False,
            "disabled": False
        },
        {
            "name": "Ukrainian",
            "value": "uk",
            "description": "Ukrainian",
            "default": False,
            "disabled": False
        },
        {
            "name": "Vietnamese",
            "value": "vi",
            "description": "Vietnamese",
            "default": False,
            "disabled": False
        },
        {
            "name": "Wolof",
            "value": "wo",
            "description": "Wolof",
            "default": False,
            "disabled": False
        },
        {
            "name": "Yoruba",
            "value": "yo",
            "description": "Yoruba",
            "default": False,
            "disabled": False
        },
        {
            "name": "Amharic",
            "value": "am",
            "description": "Amharic",
            "default": False,
            "disabled": False
        },
        {
            "name": "Greek",
            "value": "el",
            "description": "Greek",
            "default": False,
            "disabled": False
        },
        {
            "name": "Hungarian",
            "value": "hu",
            "description": "Hungarian",
            "default": False,
            "disabled": False
        },
        {
            "name": "Latin",
            "value": "la",
            "description": "Latin",
            "default": False,
            "disabled": False
        },
        {
            "name": "Mongolian",
            "value": "mn",
            "description": "Mongolian",
            "default": False,
            "disabled": False
        },
        {
            "name": "Hausa",
            "value": "ha",
            "description": "Hausa",
            "default": False,
            "disabled": False
        },
        {
            "name": "Thai",
            "value": "th",
            "description": "Thai",
            "default": False,
            "disabled": False
        },
        {
            "name": "Romanian",
            "value": "ro",
            "description": "Romanian",
            "default": False,
            "disabled": False
        },
        {
            "name": "Dutch",
            "value": "nl",
            "description": "Dutch",
            "default": False,
            "disabled": False
        },
        {
            "name": "Kiswahili",
            "value": "sw",
            "description": "Kiswahili",
            "default": False,
            "disabled": False
        }
    ]
}
settings = {}
loaded = False
imported = True
description = "xVASynth is a TTS that uses the xVASynth engine to generate voices. It's a bit more complicated to set up than the other TTSes, but it's a very good TTS that can run on CPU. It's better than PiperTTS, but it requires a bit more setup. It can run on CPU, but it's recommended to use a GPU for better performance. It supports multiple games and has a lot of voices available."
class Synthesizer(base_tts.base_Synthesizer): 
    def __init__(self, conversation_manager):
        global tts_slug, default_settings, loaded
        super().__init__(conversation_manager)
        self.tts_slug = tts_slug
        self._default_settings = default_settings
        self.xvasynth_path = self.config.xvasynth_path
        self.process_device = self.config.xvasynth_process_device
        self.times_checked_xvasynth = 0
        
        if self.is_running():
            # check if voices are available
            if len(self.voices()) == 0:
                logging.error(f'xVASynth is already running not in headless mode! Please close the xVASynth server before starting Pantella. xVASynth must be run in headless mode to work with Pantella.')
                input('\nPress any key to stop Pantella...')
                raise Exception(f'xVASynth is already running not in headless mode! Please close the xVASynth server before starting Pantella. xVASynth must be run in headless mode to work with Pantella.')
            else:
                logging.info(f'xVASynth server is already running in headless mode. Connecting without starting a new server...')
        else:
            logging.info(f'Starting xVASynth headless server...')
            self.run_tts()  # Start xVASynth server if it isn't already running
        time.sleep(2)  # Wait for xVASynth server to start
        while not self.is_running() and self.times_checked_xvasynth < 20:  # Check if xVASynth is running
            time.sleep(2)  # Wait for xVASynth server to start
            if self.times_checked_xvasynth == 5:
                logging.error(f'xVASynth server is taking longer than expected to start. Please check the xVASynth server logs for any errors. Or your computer may be a bit slower than expected.')
            self.times_checked_xvasynth += 1
        if self.times_checked_xvasynth >= 20:
            logging.error(f'xVASynth server failed to start. Please check the xVASynth server logs for any errors.')
            input('\nPress any key to stop Pantella...')
            raise Exception(f'xVASynth server failed to start. Please check the xVASynth server logs for any errors.')
            

        self.pace = self.config.xvasynth_default_pace
        self.use_sr = self.config.xvasynth_default_use_sr
        self.use_cleanup = self.config.xvasynth_default_use_cleanup

        self.last_voice = ''
        self.model_type = ''
        self.base_speaker_emb = ''
        
        # voice models path
        if not self.config.linux_mode:
            if not os.path.exists(f"{self.xvasynth_path}\\resources\\"):
                logging.error(f"xVASynth path invalid: {self.xvasynth_path}")
                logging.error(f"Please ensure that the path to xVASynth is correct in config.json (xvasynth_path)")
                input('\nPress any key to stop Pantella...')
                raise FileNotFoundError(f"xVASynth path invalid: {self.xvasynth_path}")
        else:
            if not os.path.exists(f"{self.xvasynth_path}/resources/"):
                logging.error(f"xVASynth path invalid: {self.xvasynth_path}")
                logging.error(f"Please ensure that the path to xVASynth is correct in config.json (xvasynth_path)")
                input('\nPress any key to stop Pantella...')
                raise FileNotFoundError(f"xVASynth path invalid: {self.xvasynth_path}")
            

        self._voices = None

        self.synthesize_url = f'{self.config.xvasynth_base_url}/synthesize'
        self.synthesize_batch_url = f'{self.config.xvasynth_base_url}/synthesize_batch'
        self.loadmodel_url = f'{self.config.xvasynth_base_url}/loadModel'
        self.setvocoder_url = f'{self.config.xvasynth_base_url}/setVocoder'
        logging.config(f'xVASynth - Available voices: {self.voices()}')
        logging.config(f"Total xVASynth Voices: {len(self.voices())}")
        if len(self.voices()) > 0:
            random_voice = random.choice(self.voices())
            self._say("Ecks Vee Ey Synth is ready to go.",str(random_voice))
        loaded = True

    @property
    def get_available_voices_url(self):
        return f'{self.config.xvasynth_base_url}/getAvailableVoices'
    
    @property
    def set_available_voices_url(self):
        return f'{self.config.xvasynth_base_url}/setAvailableVoices'
    
    @property
    def model_path(self):
        if self.game == "fallout4" or self.game == "fallout4vr": # get the correct voice model for Fallout 4
            model_path = f"{self.xvasynth_path}/resources/app/models/fallout4/"
        elif self.game == "falloutnv": # get the correct voice model for Fallout New Vegas
            model_path = f"{self.xvasynth_path}/resources/app/models/falloutnv/"
        elif self.game == "skyrim" or self.game == "skyrimvr": # get the correct voice model for Skyrim
            model_path = f"{self.xvasynth_path}/resources/app/models/skyrim/"
        else:
            logging.error(f'Game {self.game} not supported for xVASynth! Please ensure that the correct game is set in config.json (game) and that it is one of the following: "fallout4", "fallout4vr", "falloutnv", "skyrim", or "skyrimvr".')
            raise Exception(f'Game {self.game} not supported for xVASynth! Please ensure that the correct game is set in config.json (game) and that it is one of the following: "fallout4", "fallout4vr", "falloutnv", "skyrim", or "skyrimvr".')
        if self.config.linux_mode:
            model_path = model_path.replace("\\", "/")
        else:
            model_path = model_path.replace("/", "\\")
        return model_path

    def is_running(self):
        """Check if xVASynth is running and start it if it isn't"""
        try:
            # contact local xVASynth server; ~2 second timeout
            logging.info(f'Checking if xVASynth is already running...')
            response = requests.get(f'{self.config.xvasynth_base_url}/')
            response.raise_for_status()  # If the response contains an HTTP error status code, raise an exception
            return True
        except requests.exceptions.RequestException as err:
            logging.error(f'xVASynth is not running. Starting xVASynth server...')
            return False

    def run_tts(self):
        """Run xVASynth server in headless mode - Required for xVASynth to work with Pantella"""
        try:
            # start the process without waiting for a response
            if not self.config.linux_mode:
                subprocess.Popen(f'{self.xvasynth_path}/resources/app/cpython_{self.process_device}/server.exe', cwd=self.xvasynth_path)
            else:
                # subprocess.run(command, shell=False, cwd=self.xvasynth_path)
                if self.process_device == "cpu":
                    command = f'CUDA_VISIBLE_DEVICES= python3 {self.xvasynth_path}resources/app/server.py'
                    logging.info(f'Running xVASynth server with command: {command}')
                    threading.Thread(target=subprocess.run, args=(command,), kwargs={'shell': True, 'cwd': self.xvasynth_path}).start()
                else:
                    command = f'python3 {self.xvasynth_path}resources/app/server.py'
                    logging.info(f'Running xVASynth server with command: {command}')
                    threading.Thread(target=subprocess.run, args=(command,), kwargs={'shell': True, 'cwd': self.xvasynth_path}).start()
        except Exception as e:
            logging.error(f'Could not run xVASynth. Ensure that the path "{self.xvasynth_path}" is correct.')
            logging.error(e)
            tb = traceback.format_exc()
            logging.error(tb)
            input('\nPress any key to stop Pantella...')
            raise e
    
    def voices(self): # Send API request to xvasynth to get a list of characters
        """Return a list of available voices"""
        if self._voices is None:
            self._voices = []
            logging.config(f"Getting available voices from {self.get_available_voices_url}...")
            requests.post(self.set_available_voices_url, json={'modelsPaths': json.dumps({self.game: self.model_path})}) # Set the available voices to the ones in the models folder
            available_voices_request = requests.post(self.get_available_voices_url) # Get the available voices
            if available_voices_request.status_code == 200:
                logging.config(f"Got available voices from {self.get_available_voices_url}...")
                # logging.info(f"Response code: {r.status_code}")
                # logging.info(f"Response text: {r.text}")
                data = available_voices_request.json()
                for character in data[self.game]:
                    if self.game == "falloutnv" and character['voiceName'] not in ttw_voice_mapping:
                        self._voices.append(character['voiceName'])
                    else:
                        self._voices.append(ttw_voice_mapping[character['voiceName']])
            else:
                logging.info(f"Could not get available voices from {self.get_available_voices_url}...")
                # logging.info(f"Response code: {r.status_code}")
                # logging.info(f"Response text: {r.text}")
                data = None

            if self.game == "falloutnv":
                logging.config(f"Getting more available voices from {self.get_available_voices_url}...")
                requests.post(self.set_available_voices_url, json={'modelsPaths': json.dumps({"fallout3": f"{self.xvasynth_path}/resources/app/models/fallout3/"})}) # Set the available voices to the ones in the models folder
                available_voices_request = requests.post(self.get_available_voices_url) # Get the available voices
                if available_voices_request.status_code == 200:
                    logging.config(f"Got available voices from {self.get_available_voices_url}...")
                    # logging.info(f"Response code: {r.status_code}")
                    # logging.info(f"Response text: {r.text}")
                    data = available_voices_request.json()
                    for character in data["fallout3"]:
                        if character['voiceName'] not in ttw_voice_mapping:
                            self._voices.append(character['voiceName'])
                        else:
                            self._voices.append(ttw_voice_mapping[character['voiceName']])
                else:
                    logging.info(f"Could not get available voices from {self.get_available_voices_url}...")
                    # logging.info(f"Response code: {r.status_code}")
                    # logging.info(f"Response text: {r.text}")
                    data = None

            self._voices = [voice for voice in self._voices if voice not in self.config.xvasynth_banned_voice_models] 
        for banned_voice in self.config.xvasynth_banned_voice_models:
            if banned_voice in self._voices:
                self._voices.remove(banned_voice)
        return self._voices

    @property
    def default_voice_model_settings(self):
        return {
            "pace": self.config.xvasynth_default_pace,
            "use_cleanup": self.config.xvasynth_default_use_cleanup,
            "use_sr": self.config.xvasynth_default_use_sr,
        }
    
    @utils.time_it
    def _synthesize_line(self, line, save_path, settings, aggro=0):
        """Synthesize a line using xVASynth"""
        logging.info(f'Synthesizing voiceline: {line}')
        pluginsContext = {}
        # in combat
        if (aggro == 1):
            pluginsContext["mantella_settings"] = {
                "emAngry": 0.6
            }
        # settings = self.voice_model_settings(voice_model)
        line = ' ' + line.strip() + ' ' # xVASynth apparently performs better having spaces at the start and end of the voiceline for some reason
        data = {
            'pluginsContext': json.dumps(pluginsContext),
            'modelType': self.model_type,
            'sequence': line,
            'pace': self.pace,
            'outfile': save_path,
            'vocoder': 'n/a',
            'base_lang': settings["tts_language_code"],
            'base_emb': self.base_speaker_emb,
            'useSR': self.use_sr,
            'useCleanup': self.use_cleanup,
        }
        logging.out(f'Synthesizing voiceline: {line}')
        logging.config(f'Saving to: {save_path}')
        logging.info(f'Voice model: {self.last_voice}')
        logging.config(f'Base language: {settings["tts_language_code"]}')
        # logging.info(f'Base speaker emb: {self.base_speaker_emb}') # Too spammy
        logging.config(f'Pace: {self.pace}')
        logging.config(f'Use SR: {self.use_sr}')
        logging.config(f'Use Cleanup: {self.use_cleanup}')
        requests.post(self.synthesize_url, json=data)

    @utils.time_it
    def _batch_synthesize(self, grouped_sentences, voiceline_files, settings):
        """Batch synthesize multiple lines using xVASynth"""
        # line = [text, unknown 1, unknown 2, pace, output_path, unknown 5, unknown 6, pitch_amp]
        linesBatch = [[grouped_sentences[i], '', '', self.pace, voiceline_files[i], '', '', 1] for i in range(len(grouped_sentences))]

        # settings = self.voice_model_settings(voice_model)
        
        data = {
            'pluginsContext': '{}',
            'modelType': self.model_type,
            'linesBatch': linesBatch,
            'pace': settings.get("pace", self.default_voice_model_settings["pace"]),
            'speaker_i': None,
            'vocoder': 'n/a',
            'outputJSON': None,
            'base_lang': settings.get("tts_language_code", self.language["tts_language_code"]),
            'base_emb': self.base_speaker_emb if self.base_speaker_emb else None,
            'useSR': settings.get('use_sr', self.default_voice_model_settings["use_sr"]),
            'useCleanup': settings.get('use_cleanup', self.default_voice_model_settings["use_cleanup"]),
        }
        requests.post(self.synthesize_batch_url, json=data)

    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        voiceline = ' ' + voiceline.strip() + ' ' # xVASynth apparently performs better having spaces at the start and end of the voiceline for some reason
        voiceline_files = []
        phrases = self._split_voiceline(voiceline)
        for phrase in phrases:
            voiceline_file = f"{self.output_path}\\voicelines\\{self.last_voice}\\{utils.clean_text(phrase)[:150]}.wav"
            if self.config.linux_mode:
                voiceline_file = f"{self.output_path}/voicelines/{self.last_voice}/{utils.clean_text(phrase)[:150]}.wav"
            voiceline_files.append(voiceline_file)
        if len(phrases) == 1:
            self._synthesize_line(phrases[0], voiceline_location, settings, aggro)
        else:
            # TODO: include batch synthesis for v3 models (batch not needed very often)
            if self.model_type != 'xVAPitch':
                self._batch_synthesize(phrases, voiceline_files, settings)
            else:
                for i, voiceline_file in enumerate(voiceline_files):
                    self._synthesize_line(phrases[i], voiceline_files[i], settings)
            self.merge_audio_files(voiceline_files, voiceline_location)

    @utils.time_it
    def _group_sentences(self, voiceline_sentences, max_length=150):
        """
        Splits sentences into separate voicelines based on their length (max=max_length)
        Groups sentences if they can be done so without exceeding max_length
        """
        grouped_sentences = []
        temp_group = []
        for sentence in voiceline_sentences:
            if len(sentence) > max_length:
                grouped_sentences.append(sentence)
            elif len(' '.join(temp_group + [sentence])) <= max_length:
                temp_group.append(sentence)
            else:
                grouped_sentences.append(' '.join(temp_group))
                temp_group = [sentence]
        if temp_group:
            grouped_sentences.append(' '.join(temp_group))

        return grouped_sentences
    

    @utils.time_it
    def _split_voiceline(self, voiceline, max_length=150):
        """Split voiceline into phrases by commas, 'and', and 'or'"""

        # Split by commas and "and" or "or"
        chunks = re.split(r'(, | and | or )', voiceline)
        # Join the delimiters back to their respective chunks
        chunks = [chunks[i] + (chunks[i+1] if i+1 < len(chunks) else '') for i in range(0, len(chunks), 2)]
        # Filter out empty chunks
        chunks = [chunk for chunk in chunks if chunk.strip()]

        result = []
        for chunk in chunks:
            if len(chunk) <= max_length:
                if result and result[-1].endswith(' and'):
                    result[-1] = result[-1][:-4]
                    chunk = 'and ' + chunk.strip()
                elif result and result[-1].endswith(' or'):
                    result[-1] = result[-1][:-3]
                    chunk = 'or ' + chunk.strip()
                result.append(chunk.strip())
            else:
                # Split long chunks based on length
                words = chunk.split()
                current_line = words[0]
                for word in words[1:]:
                    if len(current_line + ' ' + word) <= max_length:
                        current_line += ' ' + word
                    else:
                        if current_line.endswith(' and'):
                            current_line = current_line[:-4]
                            word = 'and ' + word
                        if current_line.endswith(' or'):
                            current_line = current_line[:-3]
                            word = 'or ' + word
                        result.append(current_line.strip())
                        current_line = word
                result.append(current_line.strip())

        result = self._group_sentences(result, max_length)
        logging.info(f'Split sentence into:',result)

        return result

    def merge_audio_files(self, audio_files, voiceline_file_name, retries=3):
        """Merge multiple audio files into one file"""
        logging.info(f'Merging audio files: {audio_files}')
        logging.info(f'Output file: {voiceline_file_name}')
        merged_audio = np.array([])
        
        for audio_file in audio_files:
            tries_left = int(retries)
            while tries_left > 0:
                try:
                    audio, samplerate = sf.read(audio_file)
                    merged_audio = np.concatenate((merged_audio, audio))
                    break
                except:
                    logging.info(f'Could not find voiceline file: {audio_file}')
                    tries_left -= 1
                    if tries_left == 0:
                        logging.error(f'Could not find voiceline file: {audio_file}')
                        raise FileNotFoundError(f'Could not find voiceline file: {audio_file}')
                    else:
                        time.sleep(0.2)
        sf.write(voiceline_file_name, merged_audio, samplerate)
  
    @utils.time_it
    def change_voice(self, character_or_voice_model, settings=None):
        """Change the voice model to the specified character's voice model"""
        if type(character_or_voice_model) == str:
            voice = character_or_voice_model
        else:
            voice = self.get_valid_voice_model(character_or_voice_model) # character.voice_model
        
        if self.game == "falloutnv" and voice in reverse_ttw_voice_mapping:
            logging.info(f'Converting voice model {voice} to {reverse_ttw_voice_mapping[voice]} for Fallout New Vegas...')
            voice = reverse_ttw_voice_mapping[voice]

        if voice is None:
            logging.error(f'Voice model {voice} not available! Please add it to xVASynth voices list.')
        if self.crashable and voice is None:
            input("Press enter to continue...")
            raise base_tts.VoiceModelNotFound(f'Voice model {voice} not available! Please add it to xVASynth voices list.')

        logging.info(f'Loading voice model {voice}...')
        
        # TODO: Enhance to check every game for any voice model, just prefer the one for the current game if available
        if self.game == "fallout4" or self.game == "fallout4vr": # get the correct voice model for Fallout 4
            logging.config("Checking for Fallout 4 voice model...")
            XVASynthAcronym="f4_"
            XVASynthModNexusLink="https://www.nexusmods.com/fallout4/mods/49340?tab=files"
        elif self.game == "falloutnv": # get the correct voice model for Fallout New Vegas
            logging.config("Checking for Fallout New Vegas voice model...")
            XVASynthAcronym="nv_"
            XVASynthModNexusLink = "https://www.nexusmods.com/newvegas/mods/70815?tab=files"
        elif self.game == "skyrim" or self.game == "skyrimvr": # get the correct voice model for Skyrim
            logging.config("Checking for Skyrim voice model...")
            XVASynthAcronym="sk_"
            XVASynthModNexusLink = "https://www.nexusmods.com/skyrimspecialedition/mods/44184?tab=files"
        else:
            logging.error(f'Game {self.game} not supported for xVASynth! Please ensure that the correct game is set in config.json (game) and that it is one of the following: "fallout4", "fallout4vr", "falloutnv", "skyrim", or "skyrimvr".')
            raise Exception(f'Game {self.game} not supported for xVASynth! Please ensure that the correct game is set in config.json (game) and that it is one of the following: "fallout4", "fallout4vr", "falloutnv", "skyrim", or "skyrimvr".')
        voice_filename = model_filename_mapping.get(self.game, {}).get(voice, voice.lower().replace(' ', '').replace('.', ''))        
        voice_path = f"{self.model_path}{XVASynthAcronym}{voice_filename}"

        if self.config.linux_mode:
            voice_path = voice_path.replace("\\", "/")
        else:
            voice_path = voice_path.replace("/", "\\")
        
        if not os.path.exists(os.path.abspath(voice_path+'.json')) and self.game == "falloutnv":
            logging.error(f"Voice model does not exist in location '{os.path.abspath(voice_path+'.json')}'. Please ensure that the correct path has been set in config.json (xvasynth_folder) and that the model has been downloaded from {XVASynthModNexusLink} (Ctrl+F for '{XVASynthAcronym}{voice.lower().replace(' ', '')}').")
            logging.config("Checking for Fallout 3 voice model...")
            XVASynthAcronym="f3_"
            XVASynthModNexusLink = "https://www.nexusmods.com/fallout3/mods/24502?tab=files"
            voice_path = f"{self.xvasynth_path}/resources/app/models/fallout3/{XVASynthAcronym}{voice.lower().replace(' ', '')}"
            if self.config.linux_mode:
                voice_path = voice_path.replace("\\", "/")
            else:
                voice_path = voice_path.replace("/", "\\")
            
        if not os.path.exists(os.path.abspath(voice_path+'.json')):
            logging.error(f"Voice model does not exist in location '{os.path.abspath(voice_path+'.json')}'. Please ensure that the correct path has been set in config.json (xvasynth_folder) and that the model has been downloaded from {XVASynthModNexusLink} (Ctrl+F for '{XVASynthAcronym}{voice.lower().replace(' ', '')}').")
            raise base_tts.VoiceModelNotFound()

        with open(voice_path+'.json', 'r', encoding='utf-8') as f:
            voice_model_json = json.load(f)

        try:
            base_speaker_emb = voice_model_json['games'][0]['base_speaker_emb']
            base_speaker_emb = str(base_speaker_emb).replace('[','').replace(']','')
        except:
            base_speaker_emb = None

        self.base_speaker_emb = base_speaker_emb
        self.model_type = voice_model_json.get('modelType')
        # print(f"Model type: {self.model_type}")
        voice_path = voice_path.replace('\\', "/")
        model_change = {
            'outputs': None,
            'version': str(voice_model_json.get('version')) if self.model_type == 'FastPitch' else "3.0",
            'model': voice_path,
            'modelType': self.model_type,
            'base_lang': character_or_voice_model.tts_language_code if type(character_or_voice_model) != str else 'en',
            'pluginsContext': '{}',
        }
        if "emb_size" in voice_model_json:
            model_change['speakers'] = voice_model_json['emb_size']
            model_change['model_speakers'] = voice_model_json['emb_size']
            # if str(voice_model_json.get('version', "3.0")) == "1.4":
            # elif str(voice_model_json.get('version', "3.0")) == "1.3":
            # else:
            #     raise Exception(f"Unknown xVASynth model version {voice_model_json.get('version')}. Cannot determine how to set number of speakers for this model. Please ensure that your voice models are up to date with the latest version of xVASynth and that they include a version number in their json file.")
            
        logging.info(f'Loading voice model with data: {json.dumps(model_change, indent=4)}')
        requests.post(self.loadmodel_url, json=model_change)

        self.last_voice = voice
        logging.info('Voice model loaded.')
