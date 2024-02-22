import logging
import json
import os
import sys
import flask
import asyncio

class ConfigLoader:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.prompt_styles = {}
        self.load()
        self.get_prompt_styles()
        self.ready = True

        def check_missing_mantella_file(set_path):
            if not os.path.exists(set_path+'/_mantella__skyrim_folder.txt'):
                logging.warn(f'''
Warning: Could not find _mantella__skyrim_folder.txt in {set_path}. 
If you have not yet casted the Mantella spell in-game you can safely ignore this message. 
If you have casted the Mantella spell please check that your 
MantellaSoftware/config.json "skyrim_folder" has been set correctly 
(instructions on how to set this up are in the config file itself).
If you are still having issues, a list of solutions can be found here: 
https://github.com/art-from-the-machine/Mantella#issues-qa
''')
             
        # don't trust; verify; test subfolders
        if not os.path.exists(f"{self.game_path}"):
            self.ready = False
            logging.error(f"Game path does not exist: {self.game_path}")
        else:
            check_missing_mantella_file(self.game_path)

        if not os.path.exists(f"{self.xvasynth_path}\\resources\\"):
            self.ready = False
            logging.error(f"xVASynth path does not exist: {self.xvasynth_path}")
        if not os.path.exists(self.mod_voice_dir):
            self.ready = False
            logging.error(f"Mantella mod path does not exist: {self.mod_path}")

    @property
    def mod_voice_dir(self):
        return self.mod_path + "\\Sound\\Voice\\Mantella.esp"


    def save(self):
        try:
            exportable = self.export()
            with open(self.config_path, 'w') as f:
                json.dump(exportable, f, indent=4)
            logging.info(f"Config file saved to {self.config_path}")
        except Exception as e:
            logging.error(f"Could not save config file to {self.config_path}. Error: {e}")

    def load(self):
        print(f"Loading config from {self.config_path}")
        save = False
        default = self.default()
        if os.path.exists(self.config_path):
            # If the config file does not exist, create it
            config = json.load(open(self.config_path))
        else:
            logging.error(f"\"{self.config_path}\" does not exist! Creating default config file...")
            config = self.default()
            save = True

        if not save: # Check if settings are missing from the config file and add them if they are
            for key in default:
                if key not in config:
                    config[key] = default[key]
                    save = True
        
        for key in default: # Set the settings in the config file to the default settings if they are missing
            if key not in config:
                config[key] = default[key]
                save = True
            for sub_key in default[key]:
                if sub_key not in config[key]:
                    config[key][sub_key] = default[key][sub_key]
                    save = True
                    
        for key in default: # Set the config settings to the loader
            for sub_key in default[key]:
                print(f"Setting {sub_key} to {config[key][sub_key]}")
                setattr(self, sub_key, config[key][sub_key])
        logging.basicConfig(filename=self.logging_file_path, format='%(asctime)s %(levelname)s| %(message)s', level=logging.INFO)

        if save:
            self.save()

    def get_prompt_styles(self):
        prompt_styles_dir = './prompt_styles'
        for file in os.listdir(prompt_styles_dir):
            if file.endswith('.json'):
                with open(f'{prompt_styles_dir}/{file}') as f:
                    slug = file.split('.')[0]
                    self.prompt_styles[slug] = json.load(f)["style"]

    @property
    def prompts(self):
        return self.prompt_styles[self.prompt_style]
    
    def set_prompt_style(self, llm):
        """Set the prompt style - if llm has a recommended prompt style and config.prompt_style is not set to a specific style, set it to the recommended style"""
        if self.prompt_style is not None:
            if llm.prompt_style in self.prompt_styles and self.prompt_style == "default":
                self._prompt_style = self.prompt_styles[llm.prompt_style]
            elif self.prompt_style in self.prompt_styles:
                self._prompt_style = self.prompt_styles[self.prompt_style]
            else:
                logging.error(f"Prompt style {self.prompt_style} not found in prompt_styles directory. Using default prompt style.")
                self._prompt_style = self.prompt_styles["normal"]
        else:
            logging.error(f"Prompt style not set in config file. Using default prompt style.")
            self._prompt_style = self.prompt_styles["normal"]
        return self._prompt_style


    def default(self):
        return {
            "Game": {
                "game_id": "skyrim" # skyrim or fallout4
            },
            "Paths": {
                "game_path": "C:\\Games\\Steam\\steamapps\\common\\Skyrim Special Edition",
                "mod_path": "C:\\Modding\\MO2\\mods\\Mantella",
                "character_database_file": "./data/020224_skyrim_characters_hex_ids.csv",
                "voice_model_ref_ids_file": "./skyrim_voice_model_ids.json",
                "xvasynth_path": "C:\\Games\\Steam\\steamapps\\common\\xVASynth",
                "xtts_server_folder": "C:\\Users\\User\\Desktop\\xtts-api-server",
                "logging_file_path": "./logging.log",
                "language_support_file_path": "./data/language_support.csv"
            },   
            "Language": {
                "language": "en",
                "end_conversation_keyword": "Goodbye",
                "goodbye_npc_response": "Safe travels",
                "collecting_thoughts_npc_response": "I need to think for a moment."
            },
            "Microphone": {
                "whisper_model": "base",
                "stt_language": "default",
                "stt_translate": False,
                "whisper_process_device": "cpu",
                "whisper_type": "faster_whisper",
                "whisper_url": "http://127.0.0.1:8080/inference",
                "audio_threshold": "auto",
                "pause_threshold": 0.5,
                "listen_timeout": 30
            },
            "LanguageModel": {
                "inference_engine": "default",
                "tokenizer_type": "default",
                "prompt_style": "default",
                "maximum_local_tokens": 4096,
                "max_response_sentences": 999,
                "wait_time_buffer": 0.5,
                "stop": ["<im_end>","\n<im_end>"],
                "BOS_token": "<im_start>",
                "EOS_token": "<im_end>",
                "message_signifier": "\n",
                "message_seperator": "\n",
                "message_format": "[BOS_token][name][message_signifier][content][EOS_token][message_seperator]",
                "system_name": "system",
                "user_name": "user",
                "assistant_name": "assistant",
                "assist_check": True,
                "strip_smalls": True,
                "small_size": 3,
                "same_output_limit": 30,
                "conversation_limit_pct": 0.8,
                "reload_buffer": 8,
                "reload_wait_time": 1,
            },
            "InferenceOptions": {
                "temperature": 0.7,
                "top_p": 1,
                "min_p": 0.05,
                "typical_p": 1, # "typical_p": "0.5", # "typical_p": 0.5,
                "top_k": 0,
                "repeat_penalty": 1.0,
                "tfs_z": 1.0,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "mirostat_mode": 0,
                "mirostat_eta": 5,
                "mirostat_tau": 0.1,
                "max_tokens": 512,
            },
            "openai_api": {
                "llm": "gpt-3.5-turbo-1106",
                "alternative_openai_api_base": "none",
                "secret_key_file_path": "./GPT_SECRET_KEY.txt"
            },
            "llama_cpp_python": {
                "model_path": "./model.gguf",
                "n_gpu_layers": 0,
                "n_threads": 4,
                "n_batch": 512,
                "tensor_split": [1.0],
                "main_gpu": 0,
                "split_mode": 0, # 0 = single gpu, 1 = split layers and kv across gpus, 2 = split rows across gpus
                "use_mmap": True,
                "use_mlock": False,
                "n_threads_batch": 1,
                "offload_kqv": True,
            },
            "transformers": {
                "transformers_model_slug": "mistralai/Mistral-7B-Instruct-v0.1",
                "trust_remote_code": True,
                "device_map": "cuda:0", # "cuda", "cuda:0", "cuda:1", "auto"
                "load_in_4bit": True,
                "load_in_8bit": False
            },
            "Speech": {
                "tts_engine": "xvasynth",
                "end_conversation_wait_time": 1,
                "sentences_per_voiceline": 3
            },
            "xVASynth": {
                "xvasynth_process_device": "cpu",
                "pace": 1.0,
                "use_cleanup": False,
                "use_sr": False,
                "xvasynth_base_url": "http://127.0.0.1:8008"
            },
            "xTTS": {
                "xtts_base_url": "http://127.0.0.1:8020",
                "xtts_data": {
                    "temperature": 0.75,
                    "length_penalty": 1.0,
                    "repetition_penalty": 3.0,
                    "top_k": 40,
                    "top_p": 0.80,
                    "speed": 1.2,
                    "enable_text_splitting": True,
                    "stream_chunk_size": 200
                },
                "default_xtts_model": "v2.0.2"
            },
            "Cleanup": {
                "remove_mei_folders": False
            },
            "Debugging": {
                "debug_mode": False,
                "play_audio_from_script": False,
                "debug_character_name": "Hulda",
                "debug_use_mic": False,
                "default_player_response": "Can you tell me something about yourself?",
                "debug_exit_on_first_exchange": False,
                "add_voicelines_to_all_voice_folders": False
            },
            "Config": {
                "port": 8021
            }
        }

    def descriptions(self):
        """Return a dictionary of descriptions for each setting"""
        with open('./settings_descriptions.json') as f:
            return json.load(f)


    def export(self):
        return {
            "Game": {
                "game_id": self.game_id
            },
            "Paths": {
                "game_path": self.game_path,
                "mod_path": self.mod_path,
                "character_database_file": self.character_database_file,
                "voice_model_ref_ids_file": self.voice_model_ref_ids_file,
                "xvasynth_path": self.xvasynth_path,
                "xtts_server_folder": self.xtts_server_folder,
                "logging_file_path": self.logging_file_path,
                "language_support_file_path": self.language_support_file_path
            },
            "Language": {
                "language": self.language,
                "end_conversation_keyword": self.end_conversation_keyword,
                "goodbye_npc_response": self.goodbye_npc_response,
                "collecting_thoughts_npc_response": self.collecting_thoughts_npc_response
            },
            "Microphone": {
                "whisper_model": self.whisper_model,
                "stt_language": self.stt_language,
                "stt_translate": self.stt_translate,
                "whisper_process_device": self.whisper_process_device,
                "whisper_type": self.whisper_type,
                "whisper_url": self.whisper_url,
                "audio_threshold": self.audio_threshold,
                "pause_threshold": self.pause_threshold,
                "listen_timeout": self.listen_timeout
            },
            "LanguageModel": {
                "inference_engine": self.inference_engine,
                "tokenizer_type": self.tokenizer_type,
                "maximum_local_tokens": self.maximum_local_tokens,
                "max_response_sentences": self.max_response_sentences,
                "wait_time_buffer": self.wait_time_buffer,
                "stop": self.stop,
                "BOS_token": self.BOS_token,
                "EOS_token": self.EOS_token,
                "message_signifier": self.message_signifier,
                "message_seperator": self.message_seperator,
                "message_format": self.message_format,
                "system_name": self.system_name,
                "user_name": self.user_name,
                "assistant_name": self.assistant_name,
                "assist_check": self.assist_check,
                "strip_smalls": self.strip_smalls,
                "small_size": self.small_size,
                "same_output_limit": self.same_output_limit,
                "conversation_limit_pct": self.conversation_limit_pct,
                "reload_buffer": self.reload_buffer,
                "reload_wait_time": self.reload_wait_time
            },
            "InferenceOptions": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "min_p": self.min_p,
                "typical_p": self.typical_p,
                "top_k": self.top_k,
                "repeat_penalty": self.repeat_penalty,
                "tfs_z": self.tfs_z,
                "frequency_penalty": self.frequency_penalty,
                "presence_penalty": self.presence_penalty,
                "mirostat_mode": self.mirostat_mode,
                "mirostat_eta": self.mirostat_eta,
                "mirostat_tau": self.mirostat_tau,
                "max_tokens": self.max_tokens
            },
            "openai_api": {
                "llm": self.llm,
                "alternative_openai_api_base": self.alternative_openai_api_base,
                "secret_key_file_path": self.secret_key_file_path
            },
            "llama_cpp_python": {
                "model_path": self.model_path,
                "n_gpu_layers": self.n_gpu_layers,
                "n_threads": self.n_threads,
                "n_batch": self.n_batch,
                "tensor_split": self.tensor_split,
                "main_gpu": self.main_gpu,
                "split_mode": self.split_mode,
                "use_mmap": self.use_mmap,
                "use_mlock": self.use_mlock,
                "n_threads_batch": self.n_threads_batch,
                "offload_kqv": self.offload_kqv
            },
            "transformers": {
                "transformers_model_slug": self.transformers_model_slug,
                "trust_remote_code": self.trust_remote_code,
                "device_map": self.device_map,
                "load_in_4bit": self.load_in_4bit,
                "load_in_8bit": self.load_in_8bit
            },
            "Speech": {
                "tts_engine": self.tts_engine,
                "end_conversation_wait_time": self.end_conversation_wait_time,
                "sentences_per_voiceline": self.sentences_per_voiceline
            },
            "xVASynth": {
                "xvasynth_process_device": self.xvasynth_process_device,
                "pace": self.pace,
                "use_cleanup":self.use_cleanup,
                "use_sr": self.use_sr,
                "xvasynth_base_url": self.xvasynth_base_url
            },
            "xTTS": {
                "xtts_base_url": self.xtts_base_url,
                "xtts_data": self.xtts_data,
                "default_xtts_model": self.default_xtts_model
            },
            "Cleanup": {
                "remove_mei_folders": self.remove_mei_folders
            },
            "Debugging": {
                "debug_mode": self.debug_mode,
                "play_audio_from_script": self.play_audio_from_script,
                "debug_character_name": self.debug_character_name,
                "debug_use_mic": self.debug_use_mic,
                "default_player_response": self.default_player_response,
                "debug_exit_on_first_exchange": self.debug_exit_on_first_exchange,
                "add_voicelines_to_all_voice_folders": self.add_voicelines_to_all_voice_folders
            },
            "Config": {
                "port": self.port
            }
        }
    
    def default_types(self):
        typesobj = {}
        default = self.default()
        for key in default:
            typesobj[key] = {}
            for sub_key in default[key]:
                text = str(type(default[key][sub_key]))
                text = text.split("'")[1]
                typesobj[key][sub_key] = text
        return typesobj
    
    def host_config_server(self):
        app = flask.Flask(__name__)
        @app.route('/config', methods=['GET'])
        def get_config():
            return flask.jsonify(self.export())
        @app.route('/config', methods=['POST'])
        def post_config():
            data = flask.request.json
            for key in data:
                for sub_key in data[key]:
                    setattr(self, sub_key, data[key][sub_key])
            self.save()
            self.conversation_manager.restart = True
            if not self.conversation_manager.in_conversation:
                logging.info("Config updated and conversation manager not in a conversation. Restart the conversation manager to apply the new settings. - WILL BE FIXED IN FUTURE RELEASE")
            return flask.jsonify(self.export())
        @app.route('/defaults', methods=['GET'])
        def get_default():
            return flask.jsonify({
                "defaultConfig": self.default(),
                "types": self.default_types(),
                "descriptions": self.descriptions()
            })
        @app.route('/', methods=['GET'])
        def index(): # Return the index.html file
            return flask.send_file('../webconfigurator/index.html')
        @app.route('/jquery-3.7.1.min.js', methods=['GET'])
        def jquery():
            return flask.send_file('../webconfigurator/jquery-3.7.1.min.js')
        app.run(port=self.port, threaded=True)
        logging.info(f"Config server running on port http://localhost:{self.port}/")