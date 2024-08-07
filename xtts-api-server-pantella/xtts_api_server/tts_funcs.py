# tts.py

import torch
import torchaudio
from TTS.api import TTS

from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from pathlib import Path

from xtts_api_server.modeldownloader import download_model,check_tts_version

from loguru import logger
from datetime import datetime
import os
import time 
import re
import json
import socket
import io
import wave
import numpy as np

# Class to check tts settings
class InvalidSettingsError(Exception):
    pass

# List of supported language codes
supported_languages = {
    "ar":"Arabic",
    "pt":"Brazilian Portuguese",
    "zh-cn":"Chinese",
    "cs":"Czech",
    "nl":"Dutch",
    "en":"English",
    "fr":"French",
    "de":"German",
    "it":"Italian",
    "pl":"Polish",
    "ru":"Russian",
    "es":"Spanish",
    "tr":"Turkish",
    "ja":"Japanese",
    "ko":"Korean",
    "hu":"Hungarian",
    "hi":"Hindi"
}

default_tts_settings = {
    "temperature" : 0.75,
    "length_penalty" : 1.0,
    "repetition_penalty": 5.0,
    "top_k" : 50,
    "top_p" : 0.85,
    "speed" : 1,
    "enable_text_splitting": True
}

official_model_list = ["v2.0.0","v2.0.1","v2.0.2","v2.0.3","main"]
official_model_list_v2 = ["2.0.0","2.0.1","2.0.2","2.0.3"]

reversed_supported_languages = {name: code for code, name in supported_languages.items()}

class TTSWrapper:
    def __init__(self,output_folder = "./output", speaker_folder="./speakers",latent_speaker_folders = "./latent_speakers",model_folder="./xtts_folder",lowvram = False,model_source = "local",model_version = "2.0.2",device = "cuda",deepspeed = False,enable_cache_results = True):
        self.cuda = device # If the user has chosen what to use, we rewrite the value to the value we want to use
        self.device = 'cpu' if lowvram else (self.cuda if torch.cuda.is_available() else "cpu")
        self.lowvram = lowvram  # Store whether we want to run in low VRAM mode.

        self.latents_cache = {} 

        self.model_source = model_source
        self.model_version = model_version
        self.tts_settings = default_tts_settings
        self.stream_chunk_size = 100

        self.deepspeed = deepspeed
        
        speaker_folder = speaker_folder.split(',')
        if type(speaker_folder) is not list:
            self.speaker_folder = [speaker_folder]
        else:
            self.speaker_folder = speaker_folder
        self.output_folder = output_folder
        self.model_folder = model_folder
        latent_speaker_folders = latent_speaker_folders.split(',')
        if type(latent_speaker_folders) is not list:
            self.latent_speaker_folders = [latent_speaker_folders]
        else:
            self.latent_speaker_folders = latent_speaker_folders

        self.create_directories()
        check_tts_version()

        self.enable_cache_results = enable_cache_results
        self.cache_file_path = os.path.join(output_folder, "cache.json")

        self.is_official_model = True
        
        self.current_model = None
        
        if self.enable_cache_results:
            # Reset the contents of the cache file at each initialization.
            with open(self.cache_file_path, 'w') as cache_file:
                json.dump({}, cache_file)
    # HELP FUNC
    def isModelOfficial(self,model_version):
        if model_version in official_model_list:
            self.is_official_model = True
            return True
        return False

    def check_model_version_old_format(self,model_version):
        if model_version in official_model_list_v2:
            return "v"+model_version
        return model_version

    def get_models_list(self):
        # Fetch all entries in the directory given by self.model_folder
        entries = os.listdir(self.model_folder)
        
        # Filter out and return only directories, converted to lowercase without spaces
        return [name.lower().replace(' ', '') for name in entries if os.path.isdir(os.path.join(self.model_folder, name))]
        

    def get_wav_header(self, channels:int=1, sample_rate:int=24000, width:int=2) -> bytes:
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as out:
            out.setnchannels(channels)
            out.setsampwidth(width)
            out.setframerate(sample_rate)
            out.writeframes(b"")
        wav_buf.seek(0)
        return wav_buf.read()

    # CACHE FUNCS
    def check_cache(self, text_params):
        if not self.enable_cache_results:
            return None

        try:
            with open(self.cache_file_path) as cache_file:
                cache_data = json.load(cache_file)

            for entry in cache_data.values():
                if all(entry[key] == value for key, value in text_params.items()):
                    return entry['file_name']

            return None

        except FileNotFoundError:
            return None

    def update_cache(self, text_params, file_name):
        if not self.enable_cache_results:
            return None
        try:
            # Check if the file exists and its contents before downloading.
            if os.path.exists(self.cache_file_path) and os.path.getsize(self.cache_file_path) > 0:
                with open(self.cache_file_path, 'r') as cache_file:
                    cache_data = json.load(cache_file)
            else:
                cache_data = {}  # Initialization of an empty dictionary if the file does not exist or is empty.

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            cache_data[timestamp] = {**text_params, 'file_name': file_name}

            with open(self.cache_file_path, 'w') as cache_file:
                json.dump(cache_data, cache_file)

            logger.info("Cache updated successfully.")
        except IOError as e:
            print("I/O error occurred while updating the cache: ", str(e))
        except json.JSONDecodeError as e:
            print("JSON decode error occurred while updating the cache: ", str(e))
            
    # LOAD FUNCS
    def load_model(self,load=True):
        if self.model_source == "api":
            self.model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

        if self.model_source == "apiManual":
            this_dir = Path(self.model_folder)

            if self.isModelOfficial(self.model_version):
              download_model(this_dir,self.model_version)

            config_path = this_dir / f'{self.model_version}' / 'config.json'
            checkpoint_dir = this_dir / f'{self.model_version}'

            self.model = TTS(model_path=checkpoint_dir,config_path=config_path).to(self.device)

        if self.model_source != "api" and self.model_source != "apiManual":
           is_official_model = False
 
           self.load_local_model(load = is_official_model)
           self.load_all_latents()
           if self.lowvram == False:
             # Due to the fact that we create latents on the cpu and load them from the cuda we get an error
             logger.info("Pre-create latents for all current speakers")
             self.create_latents_for_all() 
          
        logger.info("Model successfully loaded ")
    
    def load_local_model(self,load=True):
        this_model_dir = Path(self.model_folder)

        if self.isModelOfficial(self.model_version):
            download_model(this_model_dir,self.model_version)
            this_model_dir = this_model_dir

        config = XttsConfig()
        config_path = this_model_dir /  f'{self.model_version}' / 'config.json'
        checkpoint_dir = this_model_dir / f'{self.model_version}'

        config.load_json(str(config_path))
        
        self.model = Xtts.init_from_config(config)
        self.model.load_checkpoint(config,use_deepspeed=self.deepspeed, checkpoint_dir=str(checkpoint_dir))
        self.model.to(self.device)

    def switch_model(self,model_name):

        self.current_model = model_name
        model_list = self.get_models_list()
        # Check to see if the same name is selected
        if(model_name == self.model_version):
            raise InvalidSettingsError("The model with this name is already loaded in memory")
            return
        
        # Check if the model is in the list at all
        if(model_name not in model_list):
            raise InvalidSettingsError(f"A model with `{model_name}` name is not in the models folder, the current available models: {model_list}")
            return

        # Clear gpu cache from old model
        self.model = ""
        torch.cuda.empty_cache()
        logger.info("Model successfully unloaded from memory")
        
        # Start load model
        logger.info(f"Start loading {model_name} model")
        self.model_version = model_name
        if self.model_source == "local":
          self.load_local_model()
        else:
          self.load_model()
          
        logger.info(f"Model successfully loaded")

    # LOWVRAM FUNCS
    def switch_model_device(self):
        # We check for lowram and the existence of cuda
        if self.lowvram and torch.cuda.is_available() and self.cuda != "cpu":
            with torch.no_grad():
                if self.device == self.cuda:
                    self.device = "cpu"
                else:
                    self.device = self.cuda

                self.model.to(self.device)

            if self.device == 'cpu':
                # Clearing the cache to free up VRAM
                torch.cuda.empty_cache()

    # SPEAKER FUNCS
    def get_or_create_latents(self, speaker_name, speaker_wav, language_code):
        speaker_name = speaker_name.lower()
        speaker_key = f"{speaker_name}_{language_code}"
        if speaker_key not in self.latents_cache:
            logger.info(f"Creating latents for {speaker_name} in {language_code}: {speaker_wav}")
            gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(speaker_wav)
            # Move latents to the current device
            gpt_cond_latent = gpt_cond_latent.to(self.device)
            speaker_embedding = speaker_embedding.to(self.device)
            self.latents_cache[speaker_key] = (gpt_cond_latent, speaker_embedding)
            self.save_latents_to_json(speaker_name, language_code)
        else:
            # Ensure cached latents are on the current device
            gpt_cond_latent, speaker_embedding = self.latents_cache[speaker_key]
            gpt_cond_latent = gpt_cond_latent.to(self.device)
            speaker_embedding = speaker_embedding.to(self.device)
        return gpt_cond_latent, speaker_embedding

    def create_latents_for_all(self):
        # Iterate over each language subdirectory in the speaker folder
        total_new_latents = 0
        total_existing_latents = 0
        for speaker_folder in self.speaker_folder:
            for language_code in os.listdir(speaker_folder):
                language_path = os.path.join(speaker_folder, language_code)
                if os.path.isdir(language_path):
                    speakers_list = self._get_speakers(language_path)
                    
                    new_latents_count = 0
                    existing_latents_count = 0

                    for speaker in speakers_list:
                        # Check if the latent JSON already exists
                        latent_exists = False
                        for latent_folder in self.latent_speaker_folders:
                            latent_json_path = os.path.join(latent_folder, language_code, f"{speaker['speaker_name']}.json")
                            if os.path.exists(latent_json_path):
                                latent_exists = True
                                break
                        if latent_exists:
                            # Increment existing latents counter if the file exists
                            existing_latents_count += 1
                        else:
                            # Otherwise, create the latent and increment new latents counter
                            self.get_or_create_latents(speaker['speaker_name'], speaker['speaker_wav'], language_code)
                            new_latents_count += 1
                    
                    total_new_latents += new_latents_count
                    total_existing_latents += existing_latents_count

                    # Report based on whether new latent JSON files were created
                    if new_latents_count > 0:
                        logger.info(f"Latents created for all {new_latents_count} new speakers in {language_code}.")
                    if existing_latents_count > 0:
                        logger.info(f"Latent JSON already existing for {existing_latents_count} speakers in {language_code}.")

        # Optionally, provide a summary of actions taken across all languages
        logger.info(f"Total new latents created across all languages: {total_new_latents}")
        logger.info(f"Total existing latents found across all languages: {total_existing_latents}")

    def save_latents_to_json(self, speaker_name, language_code):
        # Generate the combined key as used in get_or_create_latents
        speaker_key = f"{speaker_name}_{language_code}"
        
        # Ensure accessing the correct key in latents_cache
        if speaker_key in self.latents_cache:
            # Create a subdirectory for the language if it doesn't exist in the first latent_speaker_folder
            language_folder = os.path.join(self.latent_speaker_folders[0], language_code)
            if not os.path.exists(language_folder):
                os.makedirs(language_folder)
            
            # Define the file path within the language-specific folder
            file_path = os.path.join(language_folder, f"{speaker_name}.json")
            
            # Access the latents using the combined speaker_key
            data_to_save = {
                "gpt_cond_latent": self.latents_cache[speaker_key][0].tolist(),
                "speaker_embedding": self.latents_cache[speaker_key][1].tolist()
            }
            with open(file_path, 'w') as json_file:
                json.dump(data_to_save, json_file)
            logger.info(f"Latents for {speaker_name} in {language_code} saved to {file_path}")
        else:
            logger.error(f"Latents for {speaker_key} not found in cache.")
      
    def load_latents_from_json(self, file_path):
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
        # Use the class's device setting for tensor allocation
        gpt_cond_latent = torch.tensor(data['gpt_cond_latent'], device=self.device)
        speaker_embedding = torch.tensor(data['speaker_embedding'], device=self.device)
        return gpt_cond_latent, speaker_embedding
    
    def load_all_latents(self):
        # Total count for logging purposes
        total_latents_loaded = 0

        # Iterate over all language subdirectories in the latent speaker folder
        for latent_speaker_folder in self.latent_speaker_folders:
            for language_code in os.listdir(latent_speaker_folder):
                language_path = os.path.join(latent_speaker_folder, language_code)
                if os.path.isdir(language_path):
                    # Initialize counter for the current language
                    current_language_latents_count = 0

                    # Load all json files within this language subfolder
                    for file_name in os.listdir(language_path):
                        if file_name.endswith('.json'):
                            speaker_name = file_name[:-5]  # Remove '.json' to get the speaker name
                            speaker_key = f"{speaker_name}_{language_code}"
                            file_path = os.path.join(language_path, file_name)
                            gpt_cond_latent, speaker_embedding = self.load_latents_from_json(file_path)
                            self.latents_cache[speaker_key] = (gpt_cond_latent, speaker_embedding)
                            current_language_latents_count += 1

                    # Log the count of loaded latents for the current language
                    logger.info(f"Loaded latents for {current_language_latents_count} speakers in '{language_code}' subfolder.")
                    total_latents_loaded += current_language_latents_count

        # Optionally, log the total count of latents loaded across all languages
        logger.info(f"Total latents loaded across all languages: {total_latents_loaded}")

    # DIRICTORIES FUNCS
    def create_directories(self):
        # Base directories to be checked for existence
        base_directories = [self.output_folder, self.model_folder]

        # Creating base directories if they do not exist
        for directory in base_directories:
            absolute_path = os.path.abspath(os.path.normpath(directory))
            if not os.path.exists(absolute_path):
                os.makedirs(absolute_path)
                logger.info(f"Folder in the path {absolute_path} has been created")

        # Creating language subdirectories within speaker_folder and the first latent_speaker_folder
        for language_code in supported_languages.keys():
            for folder in self.speaker_folder + self.latent_speaker_folders:
                language_path = os.path.join(folder, language_code)
                if not os.path.exists(language_path):
                    os.makedirs(language_path)
                    logger.info(f"Language subfolder '{language_code}' in path {language_path} has been created")

    def set_speaker_folder(self, folder):
        if os.path.exists(folder) and os.path.isdir(folder):
            self.speaker_folder = folder
            self.create_directories()
            logger.info(f"Speaker folder is set to {folder}")
        else:
            raise ValueError("Provided path is not a valid directory")

    def set_out_folder(self, folder):
        if os.path.exists(folder) and os.path.isdir(folder):
            self.output_folder = folder
            self.create_directories()
            logger.info(f"Output folder is set to {folder}")
        else:
            raise ValueError("Provided path is not a valid directory")

    def set_tts_settings(self, temperature, speed, length_penalty,
                         repetition_penalty, top_p, top_k, enable_text_splitting, stream_chunk_size):
        # Validate each parameter and raise an exception if any checks fail.
        
        # Check temperature
        if not (0.01 <= temperature <= 1):
            raise InvalidSettingsError("Temperature must be between 0.01 and 1.")
        
        # Check speed
        if not (0.2 <= speed <= 2):
            raise InvalidSettingsError("Speed must be between 0.2 and 2.")
        
        # Check length_penalty (no explicit range specified)
        if not isinstance(length_penalty, float):
            raise InvalidSettingsError("Length penalty must be a floating point number.")
        
        # Check repetition_penalty
        if not (0.1 <= repetition_penalty <= 10.0):
            raise InvalidSettingsError("Repetition penalty must be between 0.1 and 10.0.")
        
        # Check top_p
        if not (0.01 <= top_p <= 1):
            raise InvalidSettingsError("Top_p must be between 0.01 and 1 and must be a float.")
        
        # Check top_k
        if not (1 <= top_k <= 100):
            raise InvalidSettingsError("Top_k must be an integer between 1 and 100.")

        # Check stream_chunk_size
        if not (20 <= stream_chunk_size <= 400):
            raise InvalidSettingsError("Stream chunk size must be an integer between 20 and 400.")
        
        # Check enable_text_splitting
        if not isinstance(enable_text_splitting, bool):
            raise InvalidSettingsError("Enable text splitting must be either True or False.")
        
        # All validations passed - proceed to apply settings.
        self.tts_settings = {
            "temperature": temperature,
            "speed": speed,
            "length_penalty": length_penalty,
            "repetition_penalty": repetition_penalty,
            "top_p": top_p,
            "top_k": top_k,
            "enable_text_splitting": enable_text_splitting,
        }

        self.stream_chunk_size = stream_chunk_size

        print("Successfully updated TTS settings.")

    # GET FUNCS
    def get_wav_files(self, directory):
        """ Finds all the wav files in a directory. """
        wav_files = [f for f in os.listdir(directory) if f.endswith('.wav')]
        return wav_files


    def get_wav_files(self, path):
        """Return a list of wav files in the given directory."""
        return [f for f in os.listdir(path) if f.endswith('.wav')]

    def _get_speakers_from_dir(self, path, existing_speakers=None):
        """Helper function to retrieve speaker information from directories, excluding duplicates."""
        if existing_speakers is None:
            existing_speakers = []
        speakers = []
        for f in os.listdir(path):
            full_path = os.path.join(path, f)
            if os.path.isdir(full_path) and f not in existing_speakers:
                subdir_files = self.get_wav_files(full_path)
                if subdir_files:
                    speaker_wav = [os.path.join(path, f, s) for s in subdir_files]
                    preview = os.path.join(f, subdir_files[0])
                    speakers.append({
                        'speaker_name': f,
                        'speaker_wav': speaker_wav,
                        'preview': preview
                    })
        return speakers

    def _get_speakers_from_json(self, path):
        """Helper function to retrieve speaker names from JSON files."""
        speakers = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.json'):
                    speaker_name = os.path.splitext(file)[0]
                    speaker_wav = os.path.join(root, file)
                    preview = file
                    speakers.append({
                        'speaker_name': speaker_name,
                        'speaker_wav': speaker_wav,
                        'preview': preview
                    })
        return speakers

    def get_speakers(self):
        """Gets available speakers, ensuring uniqueness across both folders."""
        speaker_info = {}
        for latent_speaker_folder in self.latent_speaker_folders:
            for lang_code in os.listdir(self.speaker_folder):
                full_path = os.path.join(self.speaker_folder, lang_code)
                if os.path.isdir(full_path):
                    speaker_path = os.path.join(self.speaker_folder, lang_code)
                    latent_speaker_path = os.path.join(latent_speaker_folder, lang_code)

                    latent_speaker_names = [s['speaker_name'] for s in self._get_speakers_from_json(latent_speaker_path)]
                    speaker_names = [s['speaker_name'] for s in self._get_speakers_from_dir(speaker_path, existing_speakers=latent_speaker_names)]

                    # Combine and ensure unique speaker names
                    combined_speakers = list(set(latent_speaker_names + speaker_names))

                    speaker_info[lang_code] = {
                        'speakers': combined_speakers
                    }
        return speaker_info

    def _get_speakers(self, path=None):
        """
        Gets info on all the speakers from the given path or the default speaker folder.

        Returns a list of {speaker_name, speaker_wav, preview} dicts.
        """
        if path is None:
            path = self.speaker_folder

        speakers = []
        for f in os.listdir(path):
            full_path = os.path.join(path, f)
            if os.path.isdir(full_path):
                # Multi-sample voice
                subdir_files = self.get_wav_files(full_path)
                if len(subdir_files) == 0:
                    # No WAV files in directory
                    continue

                speaker_name = f
                speaker_wav = [os.path.join(path, f, s) for s in subdir_files]
                # Use the first file found as the preview
                preview = os.path.join(f, subdir_files[0])
                speakers.append({
                        'speaker_name': speaker_name,
                        'speaker_wav': speaker_wav,
                        'preview': preview
                        })

            elif f.endswith('.wav'):
                speaker_name = os.path.splitext(f)[0]
                speaker_wav = full_path
                preview = f
                speakers.append({
                        'speaker_name': speaker_name,
                        'speaker_wav': speaker_wav,
                        'preview': preview
                        })
        return speakers

    def get_local_ip(self):
      try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0] 
      except Exception as e:
        print(f"Failed to obtain a local IP: {e}")
        return None
      return IP

    # Special format for SillyTavern
    def get_speakers_special(self):
        BASE_URL = os.getenv('BASE_URL', '127.0.0.1:8020')
        BASE_HOST = os.getenv('BASE_HOST', '127.0.0.1')
        BASE_PORT = os.getenv('BASE_PORT', '8020')
        TUNNEL_URL = os.getenv('TUNNEL_URL', '')

        is_local_host = BASE_HOST == '127.0.0.1' or BASE_HOST == "localhost"

        if TUNNEL_URL == "" and not is_local_host:
            TUNNEL_URL = f"http://{self.get_local_ip()}:{BASE_PORT}"
        speakers_special = []

        speakers = self._get_speakers()

        for speaker in speakers:
            if TUNNEL_URL == "":
                preview_url = f"{BASE_URL}/sample/{speaker['preview']}"
            else:
                preview_url = f"{TUNNEL_URL}/sample/{speaker['preview']}"

            speaker_special = {
                    'name': speaker['speaker_name'],
                    'voice_id': speaker['speaker_name'],
                    'preview_url': preview_url
            }
            speakers_special.append(speaker_special)

        return speakers_special


    def list_languages(self):
        return reversed_supported_languages

    # GENERATION FUNCS
    def clean_text(self,text):
        # Remove asterisks and line breaks
        text = re.sub(r'[\*\r\n]', '', text)
        # Replace double quotes with single quotes and correct punctuation around quotes
        text = re.sub(r'"\s?(.*?)\s?"', r"'\1'", text)
        return text

    async def stream_generation(self,text,speaker_name,speaker_wav,language,accent,output_file):
        # Log time
        generate_start_time = time.time()  # Record the start time of loading the model

        gpt_cond_latent, speaker_embedding = self.get_or_create_latents(speaker_name, speaker_wav, language)
        file_chunks = []

        chunks = self.model.inference_stream(
            text,
            accent,
            speaker_embedding=speaker_embedding,
            gpt_cond_latent=gpt_cond_latent,
            **self.tts_settings, # Expands the object with the settings and applies them for generation
            stream_chunk_size=self.stream_chunk_size,
        )
        
        for chunk in chunks:
            if isinstance(chunk, list):
                chunk = torch.cat(chunk, dim=0)
            file_chunks.append(chunk)
            chunk = chunk.cpu().numpy()
            chunk = chunk[None, : int(chunk.shape[0])]
            chunk = np.clip(chunk, -1, 1)
            chunk = (chunk * 32767).astype(np.int16)
            yield chunk.tobytes()

        if len(file_chunks) > 0:
            wav = torch.cat(file_chunks, dim=0)
            torchaudio.save(output_file, wav.cpu().squeeze().unsqueeze(0), 24000)
        else:
            logger.warning("No audio generated.")

        generate_end_time = time.time()  # Record the time to generate TTS
        generate_elapsed_time = generate_end_time - generate_start_time

        logger.info(f"Processing time: {generate_elapsed_time:.2f} seconds.")

    def local_generation(self,text,speaker_name,speaker_wav,language,accent,output_file):
        # Log time
        generate_start_time = time.time()  # Record the start time of loading the model

        gpt_cond_latent, speaker_embedding = self.get_or_create_latents(speaker_name, speaker_wav, language)

        out = self.model.inference(
            text,
            accent,
            gpt_cond_latent=gpt_cond_latent,
            speaker_embedding=speaker_embedding,
            **self.tts_settings, # Expands the object with the settings and applies them for generation
        )

        torchaudio.save(output_file, torch.tensor(out["wav"]).unsqueeze(0), 24000)

        generate_end_time = time.time()  # Record the time to generate TTS
        generate_elapsed_time = generate_end_time - generate_start_time

        logger.info(f"Processing time: {generate_elapsed_time:.2f} seconds.")

    def api_generation(self,text,speaker_wav,language,accent,output_file):
        self.model.tts_to_file(
                text=text,
                speaker_wav=speaker_wav,
                language=accent,
                file_path=output_file,
        )

    def get_speaker_wav(self, speaker_name_or_path, language_code):
        """Gets the speaker_wav(s) for a given speaker name considering the language."""
        for speaker_folder in self.speaker_folder:
            base_path = os.path.join(speaker_folder, language_code)  # Adjust the path to include the language code

            if speaker_name_or_path.endswith('.wav'):
                # If it's a file name
                speaker_wav = os.path.join(base_path, speaker_name_or_path)  # Adjust to look inside the language-specific folder
            else:
                # If it's a speaker name
                full_path = os.path.join(base_path, speaker_name_or_path)
                wav_files = [os.path.join(full_path, f) for f in os.listdir(full_path) if f.endswith('.wav')]
                if not wav_files:
                    raise ValueError(f"Speaker {speaker_name_or_path} not found in language folder '{language_code}'.")
                speaker_wav = wav_files if len(wav_files) > 1 else wav_files[0]
            if os.path.exists(speaker_wav):
                break
        return speaker_wav

    # MAIN FUNC
    def process_tts_to_file(self, text, speaker_name_or_path, language, accent=None, file_name_or_path="out.wav", stream=False):
        if file_name_or_path == '' or file_name_or_path is None:
            file_name_or_path = "out.wav"
        try:
            # Normalize speaker name and ensure language code is in lower case for consistency
            speaker_name = speaker_name_or_path.lower()
            language_code = language.lower()

            accent = language if accent is None else accent
            
            speaker_json_path = None
            # Adjusted path for JSON file in the latent speaker folder to include language
            for latent_speaker_folder in self.latent_speaker_folders:
                proposed_path = os.path.join(latent_speaker_folder, language_code, f"{speaker_name}.json")
                logger.info(f"Checking for speaker JSON at {proposed_path}")
                if os.path.exists(proposed_path):
                    speaker_json_path = proposed_path
                    break
            if speaker_json_path is None:
                raise ValueError(f"Speaker JSON file not found for {speaker_name} for language '{language_code}'.")
            else:
                logger.info(f"Speaker JSON found at {speaker_json_path}")

            # Check if the speaker's JSON exists in the latent speaker folder within the specific language subdirectory
            if os.path.exists(speaker_json_path):
                # Load latent directly without needing a .wav file
                speaker_wav = "out.wav"
                logger.info(f"Using latents from JSON for {speaker_name} in {language_code}")
            else:
                speaker_path_models_folder = Path(self.model_folder) / speaker_name_or_path
                for speaker_folder in self.speaker_folder:
                    # Check speaker_name_or_path in models_folder and speakers_folder
                    speaker_path_speakers_folder = Path(speaker_folder) / language_code / speaker_name
                    speaker_path_speakers_file = speaker_path_speakers_folder.with_suffix('.wav')
                
                    # Check if the .wav file exists or if the directory exists for the speaker
                    if speaker_path_speakers_folder.is_dir() or speaker_path_speakers_file.exists():
                        speaker_wav = self.get_speaker_wav(speaker_name_or_path, language)
                    elif speaker_path_models_folder.is_dir():
                        reference_wav = speaker_path_models_folder / "reference.wav"
                        if reference_wav.exists():
                            speaker_wav = str(reference_wav)
                        else:
                            logger.info(f"No 'reference.wav' found in {speaker_path_models_folder}")
                    else:
                        raise ValueError(f"Speaker path '{speaker_name_or_path}' not found in speakers or models folder.")
                    break
            # Determine output path based on whether a full path or a file name was provided
            if os.path.isabs(file_name_or_path):
                # An absolute path was provided by user; use as is.
                output_file = file_name_or_path
            else:
                # Only a filename was provided; prepend with output folder.
                output_file = os.path.join(self.output_folder, file_name_or_path)


            # Check if 'text' is a valid path to a '.txt' file.
            if os.path.isfile(text) and text.lower().endswith('.txt'):
                with open(text, 'r', encoding='utf-8') as f:
                    text = f.read()

            # Generate unic name for cached result
            if self.enable_cache_results:
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                file_name_or_path = timestamp + "_cache_" + file_name_or_path
                output_file = os.path.join(self.output_folder, file_name_or_path)

            # Replace double quotes with single, asterisks, carriage returns, and line feeds
            clear_text = self.clean_text(text)

            # Generate a dictionary of the parameters to use for caching.
            text_params = {
              'text': clear_text,
              'speaker_name_or_path': speaker_name_or_path,
              'language': language,
              'accent': accent,
              'file_name_or_path': file_name_or_path
            }

            # Check if results are already cached.
            cached_result = self.check_cache(text_params)

            if cached_result is not None:
                logger.info("Using cached result.")
                return cached_result  # Return the path to the cached result.

            self.switch_model_device() # Load to CUDA if lowram ON

            # Define generation if model via api or locally
            if self.model_source == "local":
                if stream:
                    async def stream_fn():
                        async for chunk in self.stream_generation(clear_text,speaker_name_or_path,speaker_wav,language,accent,output_file):
                            yield chunk
                        self.switch_model_device()
                        # After generation completes successfully...
                        self.update_cache(text_params,output_file)
                    return stream_fn()
                else:
                    self.local_generation(clear_text,speaker_name_or_path,speaker_wav,language,accent,output_file)
            else:
                self.api_generation(clear_text,speaker_wav,language,accent,output_file)
            
            self.switch_model_device() # Unload to CPU if lowram ON

            # After generation completes successfully...
            self.update_cache(text_params,output_file)
            return output_file

        except Exception as e:
            raise e  # Propagate exceptions for endpoint handling.

