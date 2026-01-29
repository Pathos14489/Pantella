from src.logging import logging
logging.info("Importing base_tts.py")
import src.utils as utils
import subprocess
import os
from pathlib import Path
import soundfile as sf
import time
import numpy as np
import json
from src.config_loader import ConfigLoader
try:
    logging.info("Trying to import winsound")
    import winsound
    loaded_winsound = True
    logging.info("Loaded winsound")
except:
    loaded_winsound = False
    logging.error("Could not load winsound")
try:
    logging.info("Trying to import pygame")
    import pygame
    pygame.init()
    loaded_pygame = True
    logging.info("Loaded pygame")
except:
    loaded_pygame = False
    logging.error("Could not load pygame")
logging.info("Imported required libraries in base_tts.py")

class VoiceModelNotFound(Exception):
    pass

tts_slug = "base_Synthesizer"
default_settings = {
    "transcription": "",
}
settings_description = {
    "transcription": "Transcription of the voiceline, used for some TTS types that require transcriptions of the voiceline to be sampled for generation. This is not used by all TTS types, so it may be empty if your preferred TTS doesn't require it.",
}
options = {}
settings = {}
loaded = False
description = "Base synthesizer class for all TTS types. This class should not be used directly, but rather as a base class for other TTS types. It provides the basic functionality for TTS types, such as synthesizing text, changing voice, and getting available voices. It also provides methods for handling voice model settings and speaker wavs folders."
class base_Synthesizer:
    def __init__(self, conversation_manager):
        global tts_slug, default_settings, loaded
        self.tts_slug = tts_slug
        self._default_settings = default_settings
        self.conversation_manager = conversation_manager
        self.config: ConfigLoader = self.conversation_manager.config
        # determines whether the voiceline should play internally
        self.debug_mode = self.config.debug_mode
        self.play_audio_from_script = self.config.play_audio_from_script
        # currrent game running
        self.game = self.config.game_id
        # output wav / lip files path
        if self.config.linux_mode:
            self.output_path = utils.resolve_path()+'/data'
        else:
            self.output_path = utils.resolve_path()+'\\data'
        # last active voice model
        self.crashable = self.config.continue_on_voice_model_error
        self._voices = None
        self.last_voice = ''
        loaded = True

    @property
    def tts_engines(self):
        """Return the list of TTS engines available for this TTS type"""
        return [self.tts_slug]

    @property
    def speaker_wavs_folders(self):
        if "language" in self.config.__dict__: # If the language is specified in the config, only use the speaker wavs folder for that language
            if self.config.linux_mode:
                speaker_wavs_folders = [
                    os.path.abspath(f"./data/voice_samples/{self.config.game_id}/{self.language['tts_language_code']}/"),
                    os.path.abspath(f"./data/voice_samples/")
                ]
            else:
                speaker_wavs_folders = [
                    os.path.abspath(f".\\data\\voice_samples\\{self.config.game_id}\\{self.language['tts_language_code']}\\"),
                    os.path.abspath(f".\\data\\voice_samples\\"),
                ]
        else: # Otherwise, use all the speaker wavs folders
            speaker_wavs_folders = []
            if self.config.linux_mode:
                for language_code in os.listdir(f"./data/voice_samples/{self.config.game_id}/"):
                    if not os.path.isdir(f"./data/voice_samples/{self.config.game_id}/{language_code}/"):
                        continue
                    speaker_wavs_folders.append(os.path.abspath(f"./data/voice_samples/{self.config.game_id}/{language_code}/"))
            else:
                for language_code in os.listdir(f".\\data\\voice_samples\\{self.config.game_id}\\"):
                    if not os.path.isdir(f".\\data\\voice_samples\\{self.config.game_id}\\{language_code}\\"):
                        continue
                    speaker_wavs_folders.append(os.path.abspath(f".\\data\\voice_samples\\{self.config.game_id}\\{language_code}\\"))
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
    def language(self):
        if "_prompt_style" in self.config.__dict__:
            return self.config.language # TODO: Make sure this works with prompt_styles
        return {
            "tts_language_code": "en",
        } # TODO: Fix this to get the language from the config
    
    def convert_to_16bit(self, input_file, output_file=None, override_sample_rate=None):
        if output_file is None:
            output_file = input_file
        # Read the audio file
        data, samplerate = sf.read(input_file)
        if override_sample_rate is not None:
            samplerate = override_sample_rate

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
        """"Return a list of available voices"""
        voices = []
        for speaker_wavs_folder in self.speaker_wavs_folders:
            for speaker_wav_file in os.listdir(speaker_wavs_folder):
                speaker = speaker_wav_file.split(".")[0]
                if speaker_wav_file.endswith(".wav") and speaker not in voices:
                    voices.append(speaker)
        return voices
    
    def get_speaker_wav_path(self, voice_model):
        """Get the path to the wav filepath to a voice sample for the specified voice model if it exists"""
        for speaker_wavs_folder in self.speaker_wavs_folders:
            # if os.path.exists(os.path.join(speaker_wavs_folder, f"{voice_model}")) and os.path.isdir(os.path.join(speaker_wavs_folder, f"{voice_model}")): # check if a folder exists at the path for the specified voice model's wavs
            #     list_of_files = os.listdir(speaker_wavs_folder)
            #     list_of_files = [os.path.join(speaker_wavs_folder, file+ ".wav") for file in list_of_files if os.path.isfile(os.path.join(speaker_wavs_folder, file+ ".wav"))]
            #     return random.choice(list_of_files)
            # el
            if os.path.exists(os.path.join(speaker_wavs_folder, f"{voice_model}.wav")):
                speaker_wav_path = os.path.join(speaker_wavs_folder, f"{voice_model}.wav")
                return speaker_wav_path
        return None
    
    def get_valid_voice_model(self, character_or_voice_model, crashable=None, multi_tts=True, log=True):
        """Get the valid voice model for the character from the available voices - Order of preference: voice_model, voice_model without spaces, lowercase voice_model, uppercase voice_model, lowercase voice_model without spaces, uppercase voice_model without spaces"""
        if crashable is None:
            crashable = self.crashable
        # log = True
        voice_model_folder = None
        if type(character_or_voice_model) == str:
            voice_model = character_or_voice_model
        else:
            voice_model = character_or_voice_model.voice_model
            if "voice_model_folder" in character_or_voice_model.__dict__ and character_or_voice_model.voice_model_folder != None:
                voice_model_folder = character_or_voice_model.voice_model_folder
        options = [voice_model] # add the voice model from the character object
        options.append(voice_model.replace(' ', '')) # add the voice model without spaces
        options.append(voice_model.lower()) # add the lowercase version of the voice model
        options.append(voice_model.upper()) # add the uppercase version of the voice model
        options.append(voice_model.lower().replace(' ', '')) # add the lowercase version of the voice model without spaces
        options.append(voice_model.upper().replace(' ', '')) # add the uppercase version of the voice model without spaces
        if voice_model_folder != None:
            options.append(voice_model_folder) # add the voice model folder from the character object

        available_voices = self.voices()
        if log:
            logging.info("Trying to detect voice model using the following aliases: ", options)
            logging.config("Available voices: ", available_voices)
        lower_voices = {}
        for voice in available_voices:
            lower_voices[voice.lower()] = voice
        spaceless_voices = {}
        for voice in available_voices:
            spaceless_voices[voice.replace(' ', '').lower()] = voice
        spaceless_lower_voices = {}
        for voice in available_voices:
            spaceless_lower_voices[voice.replace(' ', '').lower()] = voice
        for option in options:
            if option in available_voices:
                if log:
                    logging.info(f'Voice model "{option}" found!')
                return option # return the first valid voice model found
            if option.lower() in lower_voices:
                if log:
                    logging.info(f'Voice model "{option}" not found, but "{lower_voices[option.lower()]}" found!')
                return lower_voices[option.lower()] # return the first valid voice model found
            if option.replace(' ', '') in spaceless_voices:
                if log:
                    logging.info(f'Voice model "{option}" not found, but "{spaceless_voices[option.replace(" ", "").lower()]}" found!')
                return spaceless_voices[option.replace(' ', '').lower()] # return the first valid voice model found
            if option.lower().replace(' ', '') in spaceless_lower_voices:
                if log:
                    logging.info(f'Voice model "{option}" not found, but "{spaceless_lower_voices[option.lower().replace(" ", "")]}" found!')
                return spaceless_lower_voices[option.lower().replace(' ', '')]
        # return None # if no valid voice model is found
        if log:
            logging.error(f'Voice model "{voice_model}" not available in {self.tts_slug}! Please add it to the voices list.')
        if crashable:
            if self.continue_on_voice_model_error and voice_model == None:
                input("Press enter to continue...")
                raise VoiceModelNotFound(f'Voice model {voice_model} not available! Please add it to the voices list.')

    @utils.time_it
    def change_voice(self, character, settings=None):
        """Change the voice of the tts to the voice model specified in the character object."""
        logging.info(f'Warning: You haven\'t implemented the change_voice() method in your new TTS type. This method should change the voice of the TTS to the voice model specified in the character object if the TTS requires this as a seperate step from just asking for output. This is likely not an issue if your TTS does not require this step, but if it does, you should implement this method.')
        # logging.info(f'Changing voice to: {character.voice_model}')
        # logging.info('Voice model not loaded, please fix your code.')
        # input("Press enter to continue...")
        # raise NotImplementedError("change_voice() method not implemented in your tts type.")
        # return None

    @property
    def default_voice_model_settings(self):
        """Return the default settings for the voice model"""
        return self._default_settings
    
    def voice_model_settings_path(self, voice_model):
        """Change the voice model settings path to the voice model's voice model settings path"""
        if self.config.linux_mode:
            voice_model_settings_path = os.path.abspath(f"./data/tts_settings/{self.tts_slug}/{self.language['tts_language_code']}/{voice_model}.json")
        else:
            voice_model_settings_path = os.path.abspath(f".\\data\\tts_settings\\{self.tts_slug}\\{self.language['tts_language_code']}\\{voice_model}.json")
        return voice_model_settings_path

    def character_settings_path(self, character):
        """Change the voice model settings path to the character's voice model settings path"""
        if self.config.linux_mode:
            voice_model_settings_path = os.path.abspath(f"./data/tts_settings/voices/{character.name}/{self.language['tts_language_code']}/{self.tts_slug}.json")
        else:
            voice_model_settings_path = os.path.abspath(f".\\data\\tts_settings\\voices\\{character.name}\\{self.language['tts_language_code']}\\{self.tts_slug}.json")
        os.makedirs(os.path.dirname(voice_model_settings_path), exist_ok=True) # make sure the directory exists
        return voice_model_settings_path

    def default_settings_path(self, voice_model):
        if self.config.linux_mode:
            voice_model_settings_path = os.path.abspath(f"./data/tts_settings/default/{self.language['tts_language_code']}/{voice_model}.json")
        else:
            voice_model_settings_path = os.path.abspath(f".\\data\\tts_settings\\default\\{self.language['tts_language_code']}\\{voice_model}.json")
        return voice_model_settings_path

    def voice_model_settings(self, character_or_voice_model):
        """Return the settings for the specified voice model"""
        settings = self.default_voice_model_settings.copy()
        if type(character_or_voice_model) == str:
            voice_model = character_or_voice_model
        else:
            voice_model = self.get_valid_voice_model(character_or_voice_model)

        default_settings_path = self.default_settings_path(voice_model) # Get the default settings path for the voice model (universal for all TTS types)
        os.makedirs(os.path.dirname(default_settings_path), exist_ok=True) # make sure the directory exists
        if os.path.exists(default_settings_path):
            logging.info(f'Loading default settings for voice model: {voice_model} from {default_settings_path}')
            with open(default_settings_path, "r") as f:
                default_Settings = json.load(f)
                settings.update(default_Settings) # update with specific TTS default settings
        else:
            with open(default_settings_path, "w") as f:
                json.dump(settings, f, indent=4)

        voice_model_settings_path = self.voice_model_settings_path(voice_model) # Get the voice model settings path for the specific TTS type
        os.makedirs(os.path.dirname(voice_model_settings_path), exist_ok=True) # make sure the directory exists
        if os.path.exists(voice_model_settings_path):
            logging.info(f'Loading settings for voice model: {voice_model} from {voice_model_settings_path}')
            with open(voice_model_settings_path, "r") as f:
                tts_default_settings = json.load(f)
                settings.update(tts_default_settings) # update with specific voice model settings
        else:
            with open(voice_model_settings_path, "w") as f:
                json.dump(settings, f, indent=4)
            tts_default_settings = self.default_voice_model_settings

        if type(character_or_voice_model) != str: # If a character object is passed, load character specific settings
            character_settings_path = self.character_settings_path(character_or_voice_model)
            os.makedirs(os.path.dirname(character_settings_path), exist_ok=True) # make sure the directory exists
            if os.path.exists(character_settings_path):
                logging.info(f'Loading settings for character: {character_or_voice_model.name} from {character_settings_path}')
                with open(character_settings_path, "r") as f:
                    character_settings = json.load(f)
                    settings.update(character_settings) # update with specific character settings
            else:
                with open(character_settings_path, "w") as f:
                    json.dump(settings, f, indent=4)
                    
        settings['tts_language_code'] = self.get_language_code_from_character(character_or_voice_model)
        return settings
    
    @utils.time_it
    def _synthesize(self, voiceline, voice_model, voiceline_location, settings, aggro=0):
        """Synthesize the text passed as a parameter with the voice model specified in the character object."""
        logging.info(f'Warning: Using synthesizer() method of base_tts.py, this means you haven\'t implemented the synthesizer() method in your new tts type. This method should synthesize the text passed as a parameter with the voice model specified in the character object.')
        logging.out(f'Synthesizing text: {voiceline}')
        logging.config(f'Using voice model: {voice_model}')
        logging.config('Voiceline Location:', voiceline_location)
        logging.warn('Wav file not saved, please fix your code.')
        logging.warn('Lip file not saved, please fix your code.')
        logging.error('Voice model not loaded, please fix your code.')
        input("Press enter to continue...")
        raise NotImplementedError("synthesize() method not implemented in your tts type.")
    
    def get_language_code_from_character(self, character_or_voice_model):
        """Get the language code from the character object"""
        if type(character_or_voice_model) == str:
            language_code = self.language['tts_language_code']
        else:
            language_code = character_or_voice_model.tts_language_code
        return language_code
    
    @utils.time_it
    def synthesize(self, voiceline, character, aggro=0):
        """Synthesize the audio for the character specified using TTS"""
        logging.out(f'{self.tts_slug} - Starting voiceline synthesis: {voiceline}')
        if type(character) == str:
            voice_model = character
        else:
            voice_model = character.voice_model
        settings = self.voice_model_settings(character)
        self.change_voice(character, settings)
        if voiceline.strip() == '': # If the voiceline is empty, don't synthesize anything
            logging.info('No voiceline to synthesize.')
            return ''
        final_voiceline_file_name = 'voiceline'
        # make voice model folder if it doesn't already exist
        if self.config.linux_mode:
            if not os.path.exists(f"{self.output_path}/voicelines/{voice_model}"):
                os.makedirs(f"{self.output_path}/voicelines/{voice_model}")
            final_voiceline_file = f"{self.output_path}/voicelines/{voice_model}/{final_voiceline_file_name}.wav"
        else:
            if not os.path.exists(f"{self.output_path}\\voicelines\\{voice_model}"):
                os.makedirs(f"{self.output_path}\\voicelines\\{voice_model}")
            final_voiceline_file =  f"{self.output_path}\\voicelines\\{voice_model}\\{final_voiceline_file_name}.wav"

        try:
            if os.path.exists(final_voiceline_file):
                os.remove(final_voiceline_file)
            if os.path.exists(final_voiceline_file.replace(".wav", ".lip")):
                os.remove(final_voiceline_file.replace(".wav", ".lip"))
        except:
            logging.warning("Failed to remove spoken voicelines")

        # Synthesize voicelines using chat_tts to create the new voiceline
        self._synthesize(voiceline, voice_model, final_voiceline_file, settings, aggro)
        if not os.path.exists(final_voiceline_file):
            logging.error(f'{self.tts_slug} failed to generate voiceline at: {Path(final_voiceline_file)}')
            raise FileNotFoundError()

        self.lip_gen(voiceline, final_voiceline_file)
        self.debug(final_voiceline_file)

        return final_voiceline_file
         
    def run_command(self, command):
        """Run a command in the command prompt"""
        if self.config.linux_mode:
            sp = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

            stdout, stderr = sp.communicate()
            stderr = stderr.decode("utf-8")
        else:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            sp = subprocess.Popen(command, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            stdout, stderr = sp.communicate()
            stderr = stderr.decode("utf-8")

    def check_face_fx_wrapper(self):
        """Check if FaceFXWrapper is installed and FonixData.cdf exists in the same directory as the script."""
        current_dir = os.getcwd() # get current directory
        if self.config.linux_mode:
            cdf_path = f'{current_dir}/FaceFXWrapper/FonixData.cdf'
            face_wrapper_executable = f'{current_dir}/FaceFXWrapper/FaceFXWrapper.exe'
        else:
            cdf_path = f'{current_dir}\\FaceFXWrapper\\FonixData.cdf'
            face_wrapper_executable = f'{current_dir}\\FaceFXWrapper\\FaceFXWrapper.exe'
        installed = False

        logging.info(f'Checking if FonixData.cdf exists at: {cdf_path}')
        if os.path.isfile(cdf_path):
            logging.info(f'Found FonixData.cdf at: {cdf_path}')
            installed = True
        else:
            logging.error(f'Could not find FonixData.cdf in "{Path(cdf_path).parent}" required by FaceFXWrapper.')
        
        logging.info(f'Checking if FaceFXWrapper.exe exists at: {face_wrapper_executable}')
        if os.path.isfile(face_wrapper_executable):
            logging.info(f'Found FaceFXWrapper.exe at: {face_wrapper_executable}')
            installed = True
        else:
            logging.error(f'Could not find FaceFXWrapper.exe in "{Path(face_wrapper_executable).parent}" with which to create a Lip Sync file, download it from: https://github.com/Haurrus/FaceFXWrapper/releases')
            
        return installed

    def lip_gen(self, voiceline, final_voiceline_file):
        """Generate a lip file using FaceFXWrapper and FonixData.cdf"""
        current_dir = utils.resolve_path() # get current directory
        if self.config.linux_mode:
            cdf_path = f'{current_dir}/FaceFXWrapper/FonixData.cdf'
            face_wrapper_executable = f'{current_dir}/FaceFXWrapper/FaceFXWrapper.exe'
        else:
            cdf_path = f'{current_dir}\\FaceFXWrapper\\FonixData.cdf'
            face_wrapper_executable = f'{current_dir}\\FaceFXWrapper\\FaceFXWrapper.exe'
        logging.info(f'Generating lip file for voiceline: {voiceline} to: {final_voiceline_file.replace(".wav", ".lip")}')

        face_wrapper_game = self.game.lower()
        if face_wrapper_game == 'fallout4vr' or face_wrapper_game == 'fallout4':
            face_wrapper_game = 'Fallout4'
        if face_wrapper_game == 'skyrimvr' or face_wrapper_game == 'skyrim' or face_wrapper_game == 'falloutnv':
            face_wrapper_game = 'Skyrim'
        logging.info(f'FaceFXWrapper Detected Game: {face_wrapper_game}')

        if self.check_face_fx_wrapper() and not self.config.bypass_facefxwrapper:
            try:
                if self.config.linux_mode:
                    command = f'wine "{face_wrapper_executable}" "{face_wrapper_game}" "USEnglish" "{cdf_path}" "{final_voiceline_file}" "{final_voiceline_file.replace(".wav", "_r.wav")}" "{final_voiceline_file.replace(".wav", ".lip")}" "{voiceline}"'
                else:
                    command = f'{face_wrapper_executable} "{face_wrapper_game}" "USEnglish" "{cdf_path}" "{final_voiceline_file}" "{final_voiceline_file.replace(".wav", "_r.wav")}" "{final_voiceline_file.replace(".wav", ".lip")}" "{voiceline}"'

                logging.info(f'Running command: {command}')
                self.run_command(command)
                # remove file created by FaceFXWrapper
                if os.path.exists(final_voiceline_file.replace(".wav", "_r.wav")):
                    os.remove(final_voiceline_file.replace(".wav", "_r.wav"))
            except Exception as e:
                logging.error(f'FaceFXWrapper failed to generate lip file at: {final_voiceline_file} - Falling back to default/last lip file:', e)
        else:
            logging.error(f'FaceFXWrapper not installed or bypassed: Falling back to default lip file in the Pantella mod folder')

        if not os.path.exists(final_voiceline_file.replace(".wav", ".lip")):
            logging.error(f'FaceFXWrapper failed to generate lip file at: {Path(final_voiceline_file).with_suffix(".lip")}')

    def debug(self, final_voiceline_file):
        """Play the voiceline from the script if debug_mode is enabled."""
        if self.debug_mode and self.play_audio_from_script and loaded_winsound:
            self.play_voiceline(final_voiceline_file)

    def play_voiceline(self, final_voiceline_file, volume=0.5):
        """Play the voiceline from the script if debug_mode is enabled."""
        # winsound.PlaySound(final_voiceline_file, winsound.SND_FILENAME)
        if loaded_pygame:
            pygame.mixer.init()
            pygame.mixer.music.load(final_voiceline_file)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play()
            # release the audio device after the voiceline has finished playing
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.quit()
        elif loaded_winsound:
            logging.warn(f"Playing voiceline with winsound, no volume control available!")
            winsound.PlaySound(final_voiceline_file, winsound.SND_FILENAME)
        else:
            logging.error("Could not play voiceline, no audio library loaded.")

    def _say(self, voiceline, voice_model="Female Sultry", volume=0.5):
        logging.info(f'{self.tts_slug} - _Saying voiceline: {voiceline} with voice model: {voice_model}')
        settings = self.voice_model_settings(voice_model)
        logging.config(f'{self.tts_slug} - Using settings: {settings}')
        self.change_voice(voice_model, settings)
        voiceline_location = f"{self.output_path}\\voicelines\\{voice_model}\\direct.wav"
        if self.config.linux_mode:
            voiceline_location = f"{self.output_path}/voicelines/{voice_model}/direct.wav"
        logging.config(f'{self.tts_slug} - Voiceline location: {voiceline_location}')
        if not os.path.exists(voiceline_location):
            os.makedirs(os.path.dirname(voiceline_location), exist_ok=True)
        self._synthesize(voiceline, voice_model, voiceline_location, settings)
        self.play_voiceline(voiceline_location, volume)
        return voiceline_location