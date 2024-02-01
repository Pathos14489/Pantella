import logging
import json
import os
import sys
import flask
import asyncio

class ConfigLoader:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.load()
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
        with open(self.config_path, 'w') as f:
            json.dump(self.export(), f, indent=4)

    def load(self):
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
            for sub_key in default[key]:
                if sub_key not in config[key]:
                    config[key][sub_key] = default[key][sub_key]
                    save = True
                    
        for key in default: # Set the config settings to the loader
            for sub_key in default[key]:
                setattr(self, sub_key, config[key][sub_key])
        
        if save:
            self.save()

    def default(self):
        return {
            "Game": {
                "game_id": "skyrim"
            },
            "Paths": {
                "game_path": "C:\\Games\\Steam\\steamapps\\common\\Skyrim Special Edition",
                "mod_path": "C:\\Modding\\MO2\\mods\\Mantella",
                "character_database_file": "./data/skyrim_characters.csv",
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
                "mic_enabled": True,
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
                "maximum_local_tokens": 4096,
                "max_response_sentences": 999,
                "wait_time_buffer": 0.5,
                "stop": ["<im_end>","\n<im_end>"],
                "temperature": 0.7,
                "top_p": 1,
                "min_p": 0.05,
                "top_k": 0,
                "repeat_penalty": 1.0,
                "max_tokens": 512,
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
                "main_gpu": 0
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
                }
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
            "Prompt": {
                "single_npc_prompt": "{name} is a {race} {gendered_age} that lives in Skyrim. {name} can only speak {language}.\n\n{bio}\n\nSometimes in-game events will be sent as system messages with the text between * symbols. No one else can use these. Only System can use asterixes for providing context. Here is an example:\n\n*{player_name} picked up a pair of gloves*\n\nHere is another:\n\n*{name} dropped a Steel Sword*\n\n{name} is having a conversation with {player_name} in {location}.\n\nIt is {time12} {time_group}.\n\nThe following are Behaviors that {name} can use in addition to responding to {player_name}:\n{behavior_summary}\nThe following is a summary of the conversation that {name} and {perspective_player_description} have had so far:\n{conversation_summary}\nThe following is a conversation that will be spoken aloud between {name} and {perspective_player_description}. {name} will not respond with numbered lists, code, etc. only natural responses to the conversation.",
                "multi_npc_prompt": "{bios} \n\n{conversation_summaries}\n\nSometimes in-game events will be sent as system messages with the text between * symbols. No one else can use these. Only System can use asterixes for providing context. Here is an example:\n\n*{player_name} picked up a pair of gloves*\n\nHere is another:\n\n*{player_name} dropped a Steel Sword*\n\n{names_w_player} are having a conversation in {location} in {language}.\nIt is {time12} {time_group}."
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
                "mic_enabled": self.mic_enabled,
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
                "temperature": self.temperature,
                "top_p": self.top_p,
                "min_p": self.min_p,
                "top_k": self.top_k,
                "repeat_penalty": self.repeat_penalty,
                "max_tokens": self.max_tokens,
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
                "main_gpu": self.main_gpu
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
                "xtts_data": self.xtts_data
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
            "Prompt": {
                "single_npc_prompt": self.single_npc_prompt,
                "multi_npc_prompt": self.multi_npc_prompt
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