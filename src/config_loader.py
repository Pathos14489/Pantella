print("Importing config_loader.py")
from src.logging import logging
import json
import os
import flask
import traceback
import base64
import src.tts as tts
import src.language_model as language_models
import src.tokenizer as tokenizers
from main import restart_manager

class LoglessFlask(flask.Flask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    @property
    def logger(self):
        return None

logging.info("Imported required libraries in config_loader.py")

interface_configs = {}
# Get all interface configs from src/interface_configs/ and add them to interface_configs
for file in os.listdir(os.path.join(os.path.dirname(__file__), "../interface_configs/")):
    if file.endswith(".json") and not file.startswith("__"):
        logging.config(f"Importing interface config {file}")
        game_id = file[:-5]
        interface_config_string = open(os.path.join(os.path.dirname(__file__), "../interface_configs/", file), encoding='utf-8').read()
        try:
            interface_configs[game_id] = json.loads(interface_config_string)
        except Exception as e:
            logging.error(f"Could not import interface config {game_id}. If you're on Windows, check that any paths you have in the config file are using double backslashes instead of single backslashes.")
            tb = traceback.format_exc()
            logging.error(f"Error loading interface config {game_id}: {interface_config_string}")
            logging.error(tb)
            raise e
        logging.config(f"Imported interface config {game_id}")
logging.info("Imported all interface configs, ready to use them!")

class ConfigLoader:
    def __init__(self, config_path='config.json'):
        self.conversation_manager = None
        self.config_path = config_path
        self.prompt_styles = {}
        self._raw_prompt_styles = {}
        self.behavior_styles = {}
        self._raw_behavior_styles = {}
        self.get_behavior_styles()
        self.load()
        self.interface_configs = interface_configs
        self.current_interface_config = interface_configs[self.game_id]
        # if either "game_path" or "mod_path" are empty or not set, open a prompt to ask the user to set the path for them, and then save the config file with the new paths
        save_interface = False
        if "game_path" in self.current_interface_config and (self.current_interface_config["game_path"] == "" or self.current_interface_config["game_path"] is None):
            logging.error(f"Game path not set for game id {self.game_id} in interface config file. Please set the game path for {self.game_id} to the directory where your game is installed.")
            if self.linux_mode:
                game_path = input(f"Please enter the path to your game directory for {self.game_id} (e.g. /home/user/.steam/steam/steamapps/common/Skyrim Special Edition/): ")
            else:
                game_path = input(f"Please enter the path to your game directory for {self.game_id} (e.g. C:\\Steam\\steamapps\\common\\Skyrim Special Edition\\): ")
            save_interface = True

        if "mod_path" in self.current_interface_config and (self.current_interface_config["mod_path"] == "" or self.current_interface_config["mod_path"] is None):
            logging.error(f"Mod path not set for game id {self.game_id} in interface config file. Please set the mod path for {self.game_id} to the directory where your game mods are located.")
            if self.linux_mode:
                mod_path = input(f"Please enter the path to your game mods folder for {self.game_id} (e.g. /home/user/MO2/mods/PantellaMod/): ")
            else:
                mod_path = input(f"Please enter the path to your game mods folder for {self.game_id} (e.g. C:\\MO2\\mods\\PantellaMod\\): ")
            save_interface = True
        
        if save_interface:
            self.current_interface_config["game_path"] = game_path.replace("\\", "/").replace("/","\\")
            self.current_interface_config["mod_path"] = mod_path.replace("\\", "/").replace("/","\\")
            with open(os.path.join(os.path.dirname(__file__), "../interface_configs", f"{self.game_id}.json"), "w", encoding='utf-8') as f:
                json.dump(self.current_interface_config, f, indent=4)
        logging.config(f"ConfigLoader initialized with config path {config_path}")
        logging.config(f"Current interface config: '{self.current_interface_config}' from game id '{self.game_id}'")
        self.conversation_manager_type = self.current_interface_config["conversation_manager_type"]
        self.interface_type = self.current_interface_config["interface_type"]
        self.behavior_manager = self.current_interface_config["behavior_manager"]
        logging.log_file = self.logging_file_path # Set the logging file path
        self.manager_types = {}
        self.get_prompt_styles()
        self.addons = {}
        self.load_addons()
        self.ready = True
        os.makedirs(os.path.join(os.path.dirname(__file__), "../configs/"), exist_ok=True)  # Ensure the configs directory exists

    @property
    def game_path(self):
        return self.current_interface_config["game_path"]
    
    @property
    def mod_path(self):
        return self.current_interface_config["mod_path"]

    def save(self):
        """Save the config to the config file"""
        try:
            export_obj = self.export()
        except Exception as e:
            logging.error(f"Could not save config file to {self.config_path}. Error: {e}")
            tb = traceback.format_exc()
            logging.error(tb)
            raise e
        try:
            with open(self.config_path, 'w') as f:
                json.dump(export_obj, f, indent=4)
            logging.info(f"Config file saved to {self.config_path}")
        except Exception as e:
            logging.error(f"Could not save config file to {self.config_path}. Error: {e}")
            tb = traceback.format_exc()
            logging.error(tb)
            raise e
        
    def save_json(self, json_data):
        """Save the config to the config file"""
        export_obj = self.export()
        for key in json_data:
            for sub_key in json_data[key]:
                if sub_key not in export_obj[key]:
                    logging.warn(f"Key '{key}' with subkey '{sub_key}' not found in config file. Adding it to the config file.")
                export_obj[key][sub_key] = json_data[key][sub_key]
                if type(export_obj[key][sub_key]) == list:
                    export_obj[key][sub_key] = [item for item in export_obj[key][sub_key] if item != "" and item is not None]  # Remove empty strings and None values from lists
        try:
            with open(self.config_path, 'w') as f:
                json.dump(export_obj, f, indent=4)
            logging.info(f"Config file saved to {self.config_path}")
        except Exception as e:
            logging.error(f"Could not save config file to {self.config_path}. Error: {e}")
            tb = traceback.format_exc()
            logging.error(tb)
            raise e

    def load(self):
        """Load the config from the config file and set the settings to the loader. If the config file does not exist, create it with the default settings. If a setting is missing from the config file, set it to the default setting."""
        logging.info(f"Loading config from {self.config_path}")
        save = False
        default = self.default()
        if os.path.exists(self.config_path):
            # If the config file does not exist, create it
            try:
                config = json.load(open(self.config_path))
            except:
                new_config = input(f"Error: Could not load config file from {self.config_path}. Do you want to create a new config file with default settings? (y/n): ")
                if new_config.lower() == "y":
                    config = self.default()
                    save = True
                    logging.info(f"Saving default config file to {self.config_path}")
                else:
                    logging.error(f"Could not load config file from {self.config_path}.")
                    input("Press enter to continue...")
                    raise ValueError(f"Could not load config file from {self.config_path}. Exiting...")

        else:
            logging.error(f"\"{self.config_path}\" does not exist! Creating default config file...")
            config = self.default()
            save = True
            logging.info(f"Saving default config file to {self.config_path}")
        
        for key in default: # Set the settings in the config file to the default settings if they are missing
            if key not in config:
                config[key] = default[key]
                save = True
                logging.info(f"Saving new key '{key}' to config file")
            for sub_key in default[key]:
                if sub_key not in config[key]:
                    config[key][sub_key] = default[key][sub_key]
                    save = True
                    logging.info(f"Saving new subkey '{key}':'{sub_key}' to config file")
                    
        for key in default: # Set the config settings to the loader
            for sub_key in default[key]:
                # print(f"Setting {sub_key} to {config[key][sub_key]}")
                if "_path" in sub_key or "_file" in sub_key:
                    setattr(self, sub_key, config[key][sub_key].replace("\\", "/").replace("/","\\"))
                else:
                    setattr(self, sub_key, config[key][sub_key])

        if self.game_id not in interface_configs:
            if self.game_id == "":
                logging.error(f"Game id not set in config file. Please set the game id in the config file to a valid game id (e.g. {list(interface_configs.keys())}).")
                self.game_id = input(f"Please enter the game id for your game (e.g. {list(interface_configs.keys())}): ")
                self.save()
                return self.load() # Reload the config after setting the game id
            else:
                logging.error(f"Game id {self.game_id} not found in interface_configs directory. Please add a interface config file for {self.game_id} or change the game_id in config.json to a valid game id.")
                logging.config(f"Valid game ids: {list(interface_configs.keys())}")
                input("Press enter to continue...")
                raise ValueError(f"Game id {self.game_id} not found in interface_configs directory. Please add a interface config file for {self.game_id} or change the game_id in config.json to a valid game id.")

        if save:
            self.save()
            
        if self.linux_mode:
            logging.config("Linux mode enabled - Fixing paths for linux...")
            # Fix paths for linux
            for key in default:
                for sub_key in default[key]:
                    if "_path" in sub_key or "_file" in sub_key or "_dir" in sub_key:
                        setattr(self, sub_key, config[key][sub_key].replace("\\", "/"))
            logging.config("Paths fixed for linux")
        
        self.set_behavior_style(self.behavior_style)

        if "./" in self.python_binary:
            # Make absolute path because it's a relative path and not a raw command or absolute path
            self.python_binary = os.path.abspath(self.python_binary)
        self.xtts_api_dir = os.path.abspath(self.xtts_api_dir) # Make absolute path for xTTS API
        self.addons_dir = os.path.abspath("./addons/")
        logging.config(f"Addons directory: {self.addons_dir}")

        logging.config(f"Unique settings:", self.unique())
        logging.config(f"Config loaded from {self.config_path}")

    def get_prompt_styles(self):
        """Get the prompt styles from the prompt_styles directory"""
        logging.config("Getting prompt styles")
        prompt_styles_dir = os.path.join(os.path.dirname(__file__), "../prompt_styles/")
        self.manager_types["prompt_styles"] = [prompt_style_slug.split('.')[0] for prompt_style_slug in os.listdir(prompt_styles_dir) if os.path.isdir(os.path.join(prompt_styles_dir, prompt_style_slug))]
        for file in os.listdir(prompt_styles_dir):
            if file.endswith('.json'):
                with open(f'{prompt_styles_dir}/{file}', encoding='utf-8') as f:
                    slug = file.split('.')[0]
                    self._raw_prompt_styles[slug] = json.load(f)
                    self.prompt_styles[slug] = self._raw_prompt_styles[slug]
        style_names = [f"{slug} ({self._raw_prompt_styles[slug]['name']})" for slug in self.prompt_styles]
        # self._prompt_style = self.prompt_styles["normal_en"]
        logging.config(f"Prompt styles loaded: "+str(style_names))

    def load_addons(self):
        """Load the addons from the addons directory"""
        logging.info("Loading addons...")
        self.addons = {}
        valid_addon_parts = [
            "behaviors",
            "characters",
            "voice_samples",
            "metadata.json",
            "prompt_style.json",
            "game_event_renderers",
        ]
        if os.path.exists(self.addons_dir):
            for addon_slug in os.listdir(self.addons_dir):
                addon_path = os.path.join(self.addons_dir, addon_slug)
                if os.path.isdir(addon_path):
                    if os.path.exists(os.path.join(addon_path, "metadata.json")):
                        with open(os.path.join(addon_path, "metadata.json")) as f:
                            metadata = json.load(f)
                        if metadata["enabled"] == False:
                            logging.warn(f"Addon {addon_slug} is disabled by it's own metadata. Skipping addon.")
                            continue
                        if addon_slug in self.disabled_addons:
                            logging.warn(f"Addon {addon_slug} is disabled by your config file. Skipping addon.")
                            continue
                        self.addons[addon_slug] = metadata
                        self.addons[addon_slug]["install_path"] = addon_path
                        self.addons[addon_slug]["slug"] = addon_slug
                        self.addons[addon_slug]["addon_parts"] = []
                        for addon_part in os.listdir(addon_path):
                            if addon_part not in valid_addon_parts:
                                logging.warn(f"Addon {addon_slug} has an invalid addon part: {addon_part}. Skipping invalid addon part...")
                                continue
                            if addon_part == "prompt_style.json":
                                self.addons[addon_slug]["prompt_style"] = json.load(open(os.path.join(addon_path, addon_part))) # Load the prompt style for the addon
                            self.addons[addon_slug]["addon_parts"].append(addon_part)
                        logging.config(f"Loaded addon {addon_slug} with metadata:", json.dumps(metadata, indent=4))
                    else:
                        logging.error(f"Addon {addon_slug} does not have a metadata.json file. Skipping addon.")
                else:
                    logging.warn(f"Addon {addon_slug} is not a directory. Skipping addon.")
        else:
            logging.error(f"Addons directory {self.addons_dir} does not exist. Please set a valid addons directory in the config file.")
            input("Press enter to continue...")
            raise ValueError(f"Addons directory {self.addons_dir} does not exist. Please set a valid addons directory in the config file.")
        logging.config("Loaded addons")

    def get_addon(self, addon_slug):
        """Get the addon by the addon slug"""
        if addon_slug in self.addons:
            return self.addons[addon_slug]
        else:
            logging.error(f"Addon {addon_slug} not found in addons directory.")
            return None

    def get_behavior_styles(self):
        """Get the behavior styles from the behavior_styles directory"""
        logging.config("Getting behavior styles")
        behavior_styles_dir = os.path.join(os.path.dirname(__file__), "../behavior_styles/")
        for file in os.listdir(behavior_styles_dir):
            if file.endswith('.json'):
                with open(f'{behavior_styles_dir}/{file}') as f:
                    slug = file.split('.')[0]
                    self._raw_behavior_styles[slug] = json.load(f)
                    self.behavior_styles[slug] = self._raw_behavior_styles[slug]["behavior_style"]
        style_names = [f"{slug} ({self._raw_behavior_styles[slug]['name']})" for slug in self.behavior_styles]
        logging.config(f"Behavior styles loaded: "+str(style_names))

    @property
    def prompts(self):
        return self.language["prompts"]
    
    @property
    def stop(self):
        return self._prompt_style["style"]["stop"]
    @property
    def BOS_token(self):
        return self._prompt_style["style"]["BOS_token"]
    @property
    def EOS_token(self):
        return self._prompt_style["style"]["EOS_token"]
    @property
    def message_signifier(self):
        return self._prompt_style["style"]["message_signifier"]
    @property
    def role_separator(self):
        return self._prompt_style["style"]["role_separator"]
    @property
    def message_separator(self):
        return self._prompt_style["style"]["message_separator"]
    @property
    def message_format(self):
        return self._prompt_style["style"]["message_format"]
    @property
    def language(self):
        if self._prompt_style is not None:
            return self._prompt_style["language"]
        else:
            return {
                "tts_language_code": "en",
                "tts_language_name": "English",
            }
    @property
    def racial_language(self):
        return self._prompt_style["racial_language"]
    
    def set_prompt_style(self, llm, tokenizer):
        """Set the prompt style - if llm has a recommended prompt style and config.prompt_style is not set to a specific style, set it to the recommended style"""
        if self.prompt_style is not None:
            if llm.prompt_style in self.prompt_styles and self.prompt_style == "default":
                self._prompt_style = self.prompt_styles[llm.prompt_style]
            elif self.prompt_style in self.prompt_styles:
                self._prompt_style = self.prompt_styles[self.prompt_style]
            else:
                logging.error(f"Prompt style {self.prompt_style} not found in prompt_styles directory. Using default prompt style.")
                self._prompt_style = self.prompt_styles["normal_en"]
        else:
            logging.error(f"Prompt style not set in config file. Using default prompt style.")
            self._prompt_style = self.prompt_styles["normal_en"]
        tokenizer.set_prompt_style(self._prompt_style) # Set the prompt style for the tokenizer
        # self.get_tokenizer_settings_from_prompt_style()
        logging.info("Getting tokenizer settings from prompt style")
        logging.config("Prompt Style:", json.dumps(self._prompt_style, indent=4))
        logging.info("Prompt formatting settings loaded")
    
    def set_behavior_style(self, behavior_style):
        """Set the behavior style - if behavior_style is not set to a specific style, set it to the default style"""
        if behavior_style is not None:
            if behavior_style in self.behavior_styles:
                self._behavior_style = self.behavior_styles[behavior_style]
            else:
                logging.error(f"Behavior style {behavior_style} not found in behavior_styles directory. Using default behavior style.")
                self._behavior_style = self.behavior_styles["normal"]
        else:
            logging.error(f"Behavior style not set in config file. Using default behavior style.")
            self._behavior_style = self.behavior_styles["normal"]
        return self._behavior_style

    def _unique(self):
        """Return a dictionary of settings that have been changed from the default settings"""
        default = self.default()
        unique = {}
        for key in default:
            for sub_key in default[key]:
                if getattr(self, sub_key) != default[key][sub_key]:
                    if key not in unique:
                        unique[key] = {}
                    unique[key][sub_key] = getattr(self, sub_key)
        return unique
    
    def unique(self):
        """Return a dictionary of settings that have been changed from the default settings"""
        return json.dumps(self._unique(), indent=4)

    def descriptions(self):
        """Return a dictionary of descriptions for each setting"""
        with open('./settings_descriptions.json') as f:
            return json.load(f)

    def default(self):
        return {
            "Game": {
                "game_id": "", # skyrim, skyrimvr, fallout4 or fallout4vr
                "conversation_manager_type": "auto",
                "interface_type": "auto",
                "behavior_manager": "auto",
                "memory_manager": "auto",
                "character_manager_type": "auto",
                "character_db_type": "auto"
            },
            "Addons": {
                "disabled_addons": [],
            },
            "summarizing_memory":{
                "summary_limit_pct": 0.8,
                "summarizing_memory_direction": "topdown", # topdown or bottomup
                "summarizing_memory_depth": 1,
            },
            "chromadb_memory":{
                "memory_update_interval": 1.0,
                "logical_memories": 5,
                "emotional_memories": 5,
                "torchmoji_max_length": 30,
                "empathy": 0.5,
                "chromadb_memory_messages_before": 4,
                "chromadb_memory_messages_after": 2,
                "emotional_decay_min": 0.005,
                "emotional_decay_max": 0.01,
                "emotion_composition": {
                    "amused": [
                        "joy",
                        "speak_no_evil",
                        "wink",
                    ],
                    "happy": [
                        "ok_hand",
                        "grin",
                        "v",
                        "sunglasses",
                        "yum",
                        "smile",
                        "stuck_out_tongue_winking_eye",
                        "relieved",
                        "thumbsup",
                        "sparkles",
                        "muscle",
                        "raised_hands",
                        "cry",
                        "musical_note",
                        "notes",
                        "clap"
                    ],
                    "sad": [
                        "unamused",
                        "tired_face",
                        "sob",
                        "cry",
                        "persevere",
                        "broken_heart",
                        "sleepy",
                        "pensive"
                    ],
                    "trusting": [
                        "relaxed",
                        "pray",
                    ],
                    "afraid": [
                        "weary",
                        "sweat_smile",
                        "skull",
                    ],
                    "angry": [
                        "rage",
                        "triumph",
                        "angry",
                        "facepunch",
                        "information_desk_person",
                        "disappointed",
                    ],
                    "regretful": [
                        "disappointed",
                        "speak_no_evil",
                        "pensive",
                    ],
                    "infatuated": [
                        "heart_eyes",
                        "blush",
                        "heart",
                        "flushed",
                        "two_hearts",
                        "kissing_heart",
                        "heartbeat",
                        "yellow_heart",
                        "purple_heart",
                        "sparkling_heart",
                        "blue_heart"
                    ],
                    "flirtaious": [
                        "wink",
                        "smirk",
                        "musical_note",
                        "notes",
                    ],
                    "confused": [
                        "confused",
                        "sweat",
                        "confounded",
                        "grimacing",
                    ],
                    "curious": [
                        "eyes",
                        "see_no_evil",
                    ],
                    "cheerful": [
                        "smiling_imp",
                        "gun",
                        "see_no_evil",
                        "musical_note",
                        "notes",
                        "wink",
                    ]
                },
                "chromadb_memory_depth": 1,
                "chromadb_memory_direction": "topdown", # topdown or bottomup
                "chromadb_query_size": 5,
                "chromadb_memory_editor_enabled": True,
            },
            "SpeechToText": {
                "stt_enabled": False,
                "stt_engine": "faster_whisper", # faster_whisper, openai_whisper
                "stt_language": "default",
                "speech_processor": "speech_recognition", # speech_recognition, silero_vad
                "audio_threshold": "auto",
                "pause_threshold": 0.5,
                "listen_timeout": 30.0,
            },
            "whisper": {
                "whisper_model": "base",
            },
            "faster_whisper": {
                "stt_translate": False,
                "whisper_process_device": "cpu",
                "whisper_cpu_threads": 4,
                "whisper_compute_type": "auto",
                "beam_size": 5,
                "vad_filter": True,
            },
            "openai_whisper": {
                "whisper_url": "http://127.0.0.1:8080/inference",
            },
            "CharacterDB": {
                "allow_name_matching": True,
                "allow_id_matching": True,
                "allow_exact_base_id_matching": True,
                "allow_greedy_base_id_matching": True,
                "override_voice_model_with_simple_predictions": True,
                "auto_save_generated_characters": True,
            },
            "LanguageModel": {
                "inference_engine": "default",
                "tokenizer_type": "default",
                "maximum_local_tokens": 4096,
                "max_response_sentences": 999,
                "wait_time_buffer": 1.0,
                "same_output_limit": 30,
                "conversation_limit_pct": 0.9,
                "min_conversation_length": 5,
                "reload_buffer": 20,
                # "reload_wait_time": 1,
            },
            "PromptStyle":{
                "prompt_style": "default",
                "behavior_style": "normal",
                "conversation_start_type": "force_npc_greeting_for_first_meeting_then_llm_choice",
                "strip_smalls": True, # Skip small voicelines
                "small_size": 3, # Character length that defines a small voiceline
                "assure_grammar": True,
                "assist_check": False,
                "break_on_time_announcements": True,
                "as_a_check": False,
                "meet_string_game_events": False,
                "message_reformatting": False,
                "game_update_pruning": True,
                "game_update_prune_count": 5,
                "conversation_start_role": "system", # "system" or "user" is recommended, "assistant" is not recommended because it would teach the assstant that it can respond using your identity, which is not recommended as it will waste generations failing to generate messages from you
                "start_as_stranger": True,
                "custom_possible_player_aliases": [], # adds additional names the player goes by to the list of names to check for in the conversation start role
            },
            "InferenceOptions": {
                "thought_type": "default",
                "character_type": "auto",
                "cot_enabled": False,
                "temperature": 0.8,
                "top_p": 1.0,
                "min_p": 0.05,
                "typical_p": 0.9,
                "top_k": 0,
                "repeat_penalty": 1.0,
                "tfs_z": 1.0,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "mirostat_mode": 0.0,
                "mirostat_eta": 0.1,
                "mirostat_tau": 5,
                "max_tokens": 512,
                "logit_bias":{}
            },
            "Vision": {
                "vision_enabled": False,
                "ocr_lang": "en",
                "ocr_use_angle_cls": True,
                "ocr_filter":[
                    "Skyrim Special Edition",
                    "Fallout 4",
                    "E",
                    "Talk",
                    "Steal",
                    "Take",
                    "Use",
                    "Read",
                    "Open",
                    "Close",
                    "Activate",
                    "Search",
                    "Pick",
                    "Unlock",
                    "Lock",
                    "Sleep",
                    "Wait",
                    "Sit",
                ],
                "append_system_image_near_end": True,
                "image_message_depth": -1,
                "image_message": "The image below is what {player_perspective_name}'s can see from their perspective:\n{image}\n{ocr}",
                "paddle_ocr": True,
                "ocr_resolution": 256,
                "resize_image": True,
                "image_resolution": 672,
            },
            "LLM_API_Settings":{
                "log_all_api_requests": False,
                "reverse_proxy": False,
            },
            "anthropic_api": {
                "anthropic_model": "claude-opus-4-20250514",
                "alternative_anthropic_api_base": "none",
                "anthropic_api_key_path": ".\\ANTHROPIC_SECRET_KEY.txt",
            },
            "openai_api": {
                "openai_model": "undi95/toppy-m-7b:free",
                "openai_character_generator_model": "", # Blank for use the same model as the main model. Otherwise, specify a different model here.
                "openai_completions_type": "text", # text or chat
                "alternative_openai_api_base": "https://openrouter.ai/api/v1/",
                "openai_api_key_path": ".\\GPT_SECRET_KEY.txt",
                "banned_samplers": [], # Examples: "min_p", "typical_p", "top_p", "top_k", "temperature", "frequency_penalty", "presence_penalty", "repeat_penalty", "tfs_z", "mirostat_mode", "mirostat_eta", "mirostat_tau", "max_tokens"
                "api_log_dir": ".\\api_logs",
            },
            "llama_cpp_python": {
                "model_path": ".\\model.gguf",
                "llava_clip_model_path": ".\\clip_model.gguf",
                "n_gpu_layers": 0,
                "n_threads": 4,
                "n_batch": 512,
                "tensor_split": [], # [0.5,0.5] for 2 gpus split evenly, [0.3,0.7] for 2 gpus split unevenly
                "main_gpu": 0,
                "split_mode": 0, # 0 = single gpu, 1 = split layers and kv across gpus, 2 = split rows across gpus
                "use_mmap": True,
                "use_mlock": False,
                "n_threads_batch": 1,
                "offload_kqv": True,
            },
            "transformers": {
                "transformers_model_slug": "mistralai/Mistral-7B-Instruct-v0.1",
                "trust_remote_code": False,
                "device_map": "cuda:0", # "cuda", "cuda:0", "cuda:1", "auto"
                "load_in_8bit": False
            },
            "Speech": {
                "tts_engine": [
                    "piper_binary"
                ],
                "end_conversation_wait_time": 1,
                "sentences_per_voiceline": 2,
                "narrator_voice": "MaleKhajiit",
                "narrator_volume": 0.5, # 50% volume
                "narrator_delay": 0.2, # 200ms delay
                "bypass_facefxwrapper": False,
            },
            "xTTS": {
                "xtts_device": "cuda",
                "xtts_preload_latents": True,
                "xtts_use_cached_latents": True,
                "xtts_temperature": 0.75,
                "xtts_top_k": 50,
                "xtts_top_p": 0.85,
                "xtts_length_penalty": 1.0,
                "xtts_repetition_penalty": 10.0,
                "xtts_speed": 1.0,
                "xtts_num_beams": 1,
            },
            "piperTTS": {
                "piper_binary_dir": ".\\piper\\",
                "piper_models_dir": ".\\data\\models\\piper\\",
                "piper_tts_banned_voice_models": [],
            },
            "xVASynth": {
                "xvasynth_path": "C:\\Games\\Steam\\steamapps\\common\\xVASynth",
                "xvasynth_process_device": "cpu",
                "xvasynth_default_pace": 1.0,
                "xvasynth_default_use_cleanup": False,
                "xvasynth_default_use_sr": False,
                "xvasynth_banned_voice_models": [],
                "xvasynth_base_url": "http://127.0.0.1:8008",
                "xvasynth_banned_voice_models": [],
            },
            "xTTS_api": {
                "xtts_api_dir": ".\\xtts-api-server-pantella\\",
                "xtts_api_base_url": "http://127.0.0.1:8020",
                "xtts_api_default_temperature": 0.75,
                "xtts_api_default_length_penalty": 1.0,
                "xtts_api_default_repetition_penalty": 3.0,
                "xtts_api_default_top_k": 40,
                "xtts_api_default_top_p": 0.80,
                "xtts_api_default_speed": 1.25,
                "xtts_api_enable_text_splitting": True,
                "xtts_api_stream_chunk_size": 200,
                "xtts_api_banned_voice_models": [],
                "default_xtts_api_model": "v2.0.2",
            },
            "ChatTTS": {
                "ensure_all_voice_samples_have_inference_settings": True,
                "chat_tts_default_infer_code_prompt": "[speed_3]",
                "chat_tts_default_infer_code_temperature": 0.3,
                "chat_tts_default_infer_code_repetition_penalty": 1.05,
                "chat_tts_default_refine_text_prompt": "",
                "chat_tts_default_refine_text_temperature": 0.7,
                "chat_tts_default_refine_text_top_p": 0.7,
                "chat_tts_default_refine_text_top_k": 20,
                "chat_tts_default_refine_text_repetition_penalty": 1.0,
                "chat_tts_banned_voice_models": [],
            },
            "ParlerTTS": {
                "parler_tts_model": "parler-tts/parler-tts-mini-v1",
                "parler_tts_device": "cpu",
                "parler_tts_compile": False,
                "parler_tts_compile_mode": "reduce-overhead", # reduce-overhead, default
                "parler_tts_max_length": 50,
                "parler_tts_default_temperature": 1.0,
                "parler_tts_banned_voice_models": [],
            },
            "StyleTTS2": {
                "style_tts_2_default_alpha": 0.3,
                "style_tts_2_default_beta": 0.7,
                "style_tts_2_default_diffusion_steps": 5,
                "style_tts_2_default_embedding_scale": 1.0,
                "style_tts_2_default_t": 0.7,
                "style_tts_2_banned_voice_models": [],
            },
            "F5_TTS": {
                "f5_tts_default_speed": 1.0,
                "f5_tts_default_cfg_strength": 2.0,
                "f5_tts_volume": 1.5,
                "f5_tts_device": "cuda",
                "f5_tts_banned_voice_models": [],
            },
            "E2_TTS": {
                "e2_tts_default_speed": 1.0,
                "e2_tts_default_cfg_strength": 2.0,
                "e2_tts_volume": 1.5,
                "e2_tts_device": "cuda",
                "e2_tts_banned_voice_models": [],
            },
            "Oute_TTS": {
                "oute_tts_default_temperature": 0.1,
                "oute_tts_default_repetition_penalty": 1.1,
                "oute_tts_max_length": 4096,
                "oute_tts_volume": 1.5,
                "oute_tts_banned_voice_models": [],
            },
            "GPT-SoVITS": {
                "gpt_sovits_is_half": True,
                "gpt_sovits_device": "cuda",
                "gpt_sovits_version": "v2",
                "gpt_sovits_cut_type": "none",
                "gpt_sovits_default_prompt_language": "en",
                "gpt_sovits_default_text_language": "en",
                "gpt_sovits_default_temperature": 1.0,
                "gpt_sovits_default_top_k": 20,
                "gpt_sovits_default_top_p": 1.0,
                "gpt_sovits_error_on_too_short_or_too_long_audio": True,
                "is_bigvgan_half": True,
                "gpt_sovits_banned_voice_models": [],
            },
            "chatterbox": {
                "chatterbox_device": "cuda",
                "chatterbox_default_temperature": 0.5,
                "chatterbox_default_exaggeration": 0.5,
                "chatterbox_default_cfgw": 0.8,
                "chatterbox_max_tokens": 1024,
                "chatterbox_watermark": False,
                "chatterbox_batch_size": 300,
                "chatterbox_batch_type": "paragraph", # paragraph, sentence, word
                "chatterbox_volume": 1.0,
                "chatterbox_banned_voice_models": [],
            },
            "chatterbox_api": {
                "chatterbox_api_base_url": "http://127.0.0.1:8024",
                "chatterbox_api_default_temperature": 0.5,
                "chatterbox_api_default_exaggeration": 0.5,
                "chatterbox_api_default_cfgw": 0.8,
                "chatterbox_api_max_tokens": 1024,
                "chatterbox_api_watermark": False,
                "chatterbox_api_batch_size": 300,
                "chatterbox_api_batch_type": "paragraph", # paragraph, sentence, word
                "chatterbox_api_volume": 1.0,
                "chatterbox_api_banned_voice_models": [],
            },
            "mira_tts": {
                "mira_tts_tts_banned_voice_models": [],
            },
            "Debugging": {
                "debug_mode": False,
                "share_debug_ui": False,
                "remove_mei_folders": False,
                "play_audio_from_script": False,
                "tts_boot_annoncements": True,
                "add_voicelines_to_all_voice_folders": False,
                "play_startup_announcement": True
            },
            "Errors": {
                "block_logs_from": [],
                "block_log_types": [],
                "error_on_empty_full_reply": False,
                "continue_on_voice_model_error": False,
                "continue_on_missing_character": False,
                "continue_on_start_type_error": False,
                "continue_on_llm_api_error": True,
                "continue_on_failure_to_send_audio_to_game_interface": False,
                "must_generate_a_sentence": False,
                "use_game_event_lines_as_is_if_cannot_parse": True,
                "bad_author_retries": 5,
                "retries": 3,
                "system_loop": 3,
            },
            "Config": {
                "linux_mode": False,
                "seed": -1,
                "python_binary": "../../python-3.10.11-embed/python.exe", # Default is for use with the launcher. Change to "python" or "python3" for use with a system python installation
                "character_database_file": ".\\characters\\", # can be a csv file path, a directory file path, or a list of csv file paths and directory file paths
                "conversation_data_directory": ".\\data\\conversations",
                "voice_model_ref_ids_file": ".\\skyrim_voice_model_ids.json",
                "logging_file_path": ".\\logging.log",
                "web_configurator": True, # Enable the web configurator
                "open_config_on_startup": True,
                "config_port": 8021,
                "memory_editor_port": 8022,
                "debug_ui_port": 8023,
            }
        }
    
    def export(self):
        return {
            "Game": {
                "game_id": self.game_id,
                "conversation_manager_type": self.conversation_manager_type,
                "interface_type": self.interface_type,
                "behavior_manager": self.behavior_manager,
                "memory_manager": self.memory_manager,
                "character_manager_type": self.character_manager_type,
                "character_db_type": self.character_db_type,
            },
            "Addons":{
                "disabled_addons": self.disabled_addons,
            },
            "summarizing_memory": {
                "summary_limit_pct": self.summary_limit_pct,
                "summarizing_memory_direction": self.summarizing_memory_direction,
                "summarizing_memory_depth": self.summarizing_memory_depth,
            },
            "chromadb_memory": {
                "memory_update_interval": self.memory_update_interval,
                "logical_memories": self.logical_memories,
                "emotional_memories": self.emotional_memories,
                "torchmoji_max_length": self.torchmoji_max_length,
                "empathy": self.empathy,
                "chromadb_memory_messages_before": self.chromadb_memory_messages_before,
                "chromadb_memory_messages_after": self.chromadb_memory_messages_after,
                "emotional_decay_min": self.emotional_decay_min,
                "emotional_decay_max": self.emotional_decay_max,
                "emotion_composition": self.emotion_composition,
                "chromadb_memory_depth": self.chromadb_memory_depth,
                "chromadb_memory_direction": self.chromadb_memory_direction,
                "chromadb_query_size": self.chromadb_query_size,
                "chromadb_memory_editor_enabled": self.chromadb_memory_editor_enabled,
            },
            "SpeechToText": {
                "stt_enabled": self.stt_enabled,
                "stt_engine": self.stt_engine,
                "stt_language": self.stt_language,
                "speech_processor": self.speech_processor,
                "audio_threshold": self.audio_threshold,
                "pause_threshold": self.pause_threshold,
                "listen_timeout": self.listen_timeout,
            },
            "whisper": {
                "whisper_model": self.whisper_model,
            },
            "faster_whisper": {
                "stt_translate": self.stt_translate,
                "whisper_process_device": self.whisper_process_device,
                "whisper_cpu_threads": self.whisper_cpu_threads,
                "whisper_compute_type": self.whisper_compute_type,
                "beam_size": self.beam_size,
                "vad_filter": self.vad_filter,
            },
            "openai_whisper": {
                "whisper_url": self.whisper_url,
            },
            "CharacterDB": {
                "allow_name_matching": self.allow_name_matching,
                "allow_id_matching": self.allow_id_matching,
                "allow_exact_base_id_matching": self.allow_exact_base_id_matching,
                "allow_greedy_base_id_matching": self.allow_greedy_base_id_matching,
                "override_voice_model_with_simple_predictions": self.override_voice_model_with_simple_predictions,
                "auto_save_generated_characters": self.auto_save_generated_characters,
            },
            "LanguageModel": {
                "inference_engine": self.inference_engine,
                "tokenizer_type": self.tokenizer_type,
                "maximum_local_tokens": self.maximum_local_tokens,
                "max_response_sentences": self.max_response_sentences,
                "wait_time_buffer": self.wait_time_buffer,
                "same_output_limit": self.same_output_limit,
                "conversation_limit_pct": self.conversation_limit_pct,
                "min_conversation_length": self.min_conversation_length,
                "reload_buffer": self.reload_buffer,
                # "reload_wait_time": self.reload_wait_time,
            },
            "PromptStyle":{
                "prompt_style": self.prompt_style,
                "behavior_style": self.behavior_style,
                "conversation_start_type": self.conversation_start_type,
                "strip_smalls": self.strip_smalls,
                "small_size": self.small_size,
                "assure_grammar": self.assure_grammar,
                "assist_check": self.assist_check,
                "as_a_check": self.as_a_check,
                "break_on_time_announcements": self.break_on_time_announcements,
                "meet_string_game_events": self.meet_string_game_events,
                "message_reformatting": self.message_reformatting,
                "game_update_pruning": self.game_update_pruning,
                "game_update_prune_count": self.game_update_prune_count,
                "conversation_start_role": self.conversation_start_role,
                "start_as_stranger": self.start_as_stranger,
                "custom_possible_player_aliases": self.custom_possible_player_aliases,
            },
            "InferenceOptions": {
                "thought_type": self.thought_type,
                "character_type": self.character_type,
                "cot_enabled": self.cot_enabled,
                "temperature": self.temperature,
                "thought_type": self.thought_type,
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
                "max_tokens": self.max_tokens,
                "logit_bias": self.logit_bias,
            },
            "Vision": {
                "vision_enabled": self.vision_enabled,
                "ocr_lang": self.ocr_lang,
                "ocr_use_angle_cls": self.ocr_use_angle_cls,
                "ocr_filter": self.ocr_filter,
                "append_system_image_near_end": self.append_system_image_near_end,
                "image_message_depth": self.image_message_depth,
                "image_message": self.image_message,
                "paddle_ocr": self.paddle_ocr,
                "ocr_resolution": self.ocr_resolution,
                "image_resolution": self.image_resolution,
                "resize_image": self.resize_image,
            },
            "LLM_API_Settings": {
                "log_all_api_requests": self.log_all_api_requests,
                "reverse_proxy": self.reverse_proxy,
            },
            "anthropic_api": {
                "anthropic_model": self.anthropic_model,
                "alternative_anthropic_api_base": self.alternative_anthropic_api_base,
                "anthropic_api_key_path": self.anthropic_api_key_path,
            },
            "openai_api": {
                "openai_model": self.openai_model,
                "openai_character_generator_model": self.openai_character_generator_model,
                "openai_completions_type": self.openai_completions_type,
                "alternative_openai_api_base": self.alternative_openai_api_base,
                "openai_api_key_path": self.openai_api_key_path,
                "banned_samplers": self.banned_samplers,
                "api_log_dir": self.api_log_dir,
            },
            "llama_cpp_python": {
                "model_path": self.model_path,
                "llava_clip_model_path": self.llava_clip_model_path,
                "n_gpu_layers": self.n_gpu_layers,
                "n_threads": self.n_threads,
                "n_batch": self.n_batch,
                "tensor_split": self.tensor_split,
                "main_gpu": self.main_gpu,
                "split_mode": self.split_mode,
                "use_mmap": self.use_mmap,
                "use_mlock": self.use_mlock,
                "n_threads_batch": self.n_threads_batch,
                "offload_kqv": self.offload_kqv,
            },
            "transformers": {
                "transformers_model_slug": self.transformers_model_slug,
                "trust_remote_code": self.trust_remote_code,
                "device_map": self.device_map,
                "load_in_8bit": self.load_in_8bit,
            },
            "Speech": {
                "tts_engine": self.tts_engine,
                "end_conversation_wait_time": self.end_conversation_wait_time,
                "sentences_per_voiceline": self.sentences_per_voiceline,
                "narrator_voice": self.narrator_voice,
                "narrator_volume": self.narrator_volume,
                "narrator_delay": self.narrator_delay,
                "bypass_facefxwrapper": self.bypass_facefxwrapper,
            },
            "xTTS": {
                "xtts_device": self.xtts_device,
                "xtts_preload_latents": self.xtts_preload_latents,
                "xtts_use_cached_latents": self.xtts_use_cached_latents,
                "xtts_temperature": self.xtts_temperature,
                "xtts_top_k": self.xtts_top_k,
                "xtts_top_p": self.xtts_top_p,
                "xtts_length_penalty": self.xtts_length_penalty,
                "xtts_repetition_penalty": self.xtts_repetition_penalty,
                "xtts_speed": self.xtts_speed,
                "xtts_num_beams": self.xtts_num_beams,
            },
            "piperTTS": {
                "piper_binary_dir": self.piper_binary_dir,
                "piper_models_dir": self.piper_models_dir,
                "piper_tts_banned_voice_models": self.piper_tts_banned_voice_models,
            },
            "xVASynth": {
                "xvasynth_path": self.xvasynth_path,
                "xvasynth_process_device": self.xvasynth_process_device,
                "xvasynth_default_pace": self.xvasynth_default_pace,
                "xvasynth_default_use_cleanup": self.xvasynth_default_use_cleanup,
                "xvasynth_default_use_sr": self.xvasynth_default_use_sr,
                "xvasynth_banned_voice_models": self.xvasynth_banned_voice_models,
                "xvasynth_base_url": self.xvasynth_base_url,
                "xvasynth_banned_voice_models": self.xvasynth_banned_voice_models,
            },
            "xTTS_api": {
                "xtts_api_dir": self.xtts_api_dir,
                "xtts_api_base_url": self.xtts_api_base_url,
                "xtts_api_default_temperature": self.xtts_api_default_temperature,
                "xtts_api_default_length_penalty": self.xtts_api_default_length_penalty,
                "xtts_api_default_repetition_penalty": self.xtts_api_default_repetition_penalty,
                "xtts_api_default_top_k": self.xtts_api_default_top_k,
                "xtts_api_default_top_p": self.xtts_api_default_top_p,
                "xtts_api_default_speed": self.xtts_api_default_speed,
                "xtts_api_enable_text_splitting": self.xtts_api_enable_text_splitting,
                "xtts_api_stream_chunk_size": self.xtts_api_stream_chunk_size,
                "xtts_api_banned_voice_models": self.xtts_api_banned_voice_models,
                "default_xtts_api_model": self.default_xtts_api_model,
            },
            "ChatTTS": {
                "ensure_all_voice_samples_have_inference_settings": self.ensure_all_voice_samples_have_inference_settings,
                "chat_tts_default_infer_code_prompt": self.chat_tts_default_infer_code_prompt,
                "chat_tts_default_infer_code_temperature": self.chat_tts_default_infer_code_temperature,
                "chat_tts_default_infer_code_repetition_penalty": self.chat_tts_default_infer_code_repetition_penalty,
                "chat_tts_default_refine_text_prompt": self.chat_tts_default_refine_text_prompt,
                "chat_tts_default_refine_text_temperature": self.chat_tts_default_refine_text_temperature,
                "chat_tts_default_refine_text_top_p": self.chat_tts_default_refine_text_top_p,
                "chat_tts_default_refine_text_top_k": self.chat_tts_default_refine_text_top_k,
                "chat_tts_default_refine_text_repetition_penalty": self.chat_tts_default_refine_text_repetition_penalty,
                "chat_tts_banned_voice_models": self.chat_tts_banned_voice_models,
            },
            "ParlerTTS": {
                "parler_tts_model": self.parler_tts_model,
                "parler_tts_device": self.parler_tts_device,
                "parler_tts_compile": self.parler_tts_compile,
                "parler_tts_compile_mode": self.parler_tts_compile_mode,
                "parler_tts_max_length": self.parler_tts_max_length,
                "parler_tts_default_temperature": self.parler_tts_default_temperature,
                "parler_tts_banned_voice_models": self.parler_tts_banned_voice_models,
            },
            "StyleTTS2": {
                "style_tts_2_default_alpha": self.style_tts_2_default_alpha,
                "style_tts_2_default_beta": self.style_tts_2_default_beta,
                "style_tts_2_default_diffusion_steps": self.style_tts_2_default_diffusion_steps,
                "style_tts_2_default_embedding_scale": self.style_tts_2_default_embedding_scale,
                "style_tts_2_default_t": self.style_tts_2_default_t,
                "style_tts_2_banned_voice_models": self.style_tts_2_banned_voice_models,
            },
            "F5_TTS": {
                "f5_tts_default_speed": self.f5_tts_default_speed,
                "f5_tts_default_cfg_strength": self.f5_tts_default_cfg_strength,
                "f5_tts_volume": self.f5_tts_volume,
                "f5_tts_device": self.f5_tts_device,
                "f5_tts_banned_voice_models": self.f5_tts_banned_voice_models,
            },
            "E2_TTS": {
                "e2_tts_default_speed": self.e2_tts_default_speed,
                "e2_tts_default_cfg_strength": self.e2_tts_default_cfg_strength,
                "e2_tts_volume": self.e2_tts_volume,
                "e2_tts_device": self.e2_tts_device,
                "e2_tts_banned_voice_models": self.e2_tts_banned_voice_models,
            },
            "Oute_TTS": {
                "oute_tts_default_temperature": self.oute_tts_default_temperature,
                "oute_tts_default_repetition_penalty": self.oute_tts_default_repetition_penalty,
                "oute_tts_max_length": self.oute_tts_max_length,
                "oute_tts_volume": self.oute_tts_volume,
                "oute_tts_banned_voice_models": self.oute_tts_banned_voice_models,
            },
            "GPT-SoVITS": {
                "gpt_sovits_is_half": self.gpt_sovits_is_half,
                "gpt_sovits_device": self.gpt_sovits_device,
                "gpt_sovits_version": self.gpt_sovits_version,
                "gpt_sovits_cut_type": self.gpt_sovits_cut_type,
                "gpt_sovits_default_prompt_language": self.gpt_sovits_default_prompt_language,
                "gpt_sovits_default_text_language": self.gpt_sovits_default_text_language,
                "gpt_sovits_default_temperature": self.gpt_sovits_default_temperature,
                "gpt_sovits_default_top_k": self.gpt_sovits_default_top_k,
                "gpt_sovits_default_top_p": self.gpt_sovits_default_top_p,
                "gpt_sovits_error_on_too_short_or_too_long_audio": self.gpt_sovits_error_on_too_short_or_too_long_audio,
                "is_bigvgan_half": self.is_bigvgan_half,
                "gpt_sovits_banned_voice_models": self.gpt_sovits_banned_voice_models,
            },
            "chatterbox": {
                "chatterbox_device": self.chatterbox_device,
                "chatterbox_default_temperature": self.chatterbox_default_temperature,
                "chatterbox_default_exaggeration": self.chatterbox_default_exaggeration,
                "chatterbox_default_cfgw": self.chatterbox_default_cfgw,
                "chatterbox_max_tokens": self.chatterbox_max_tokens,
                "chatterbox_watermark": self.chatterbox_watermark,
                "chatterbox_batch_size": self.chatterbox_batch_size,
                "chatterbox_batch_type": self.chatterbox_batch_type,
                "chatterbox_volume": self.chatterbox_volume,
                "chatterbox_banned_voice_models": self.chatterbox_banned_voice_models,
            },
            "chatterbox_api": {
                "chatterbox_api_base_url": self.chatterbox_api_base_url,
                "chatterbox_api_default_temperature": self.chatterbox_api_default_temperature,
                "chatterbox_api_default_exaggeration": self.chatterbox_api_default_exaggeration,
                "chatterbox_api_default_cfgw": self.chatterbox_api_default_cfgw,
                "chatterbox_api_max_tokens": self.chatterbox_api_max_tokens,
                "chatterbox_api_watermark": self.chatterbox_api_watermark,
                "chatterbox_api_batch_size": self.chatterbox_api_batch_size,
                "chatterbox_api_batch_type": self.chatterbox_api_batch_type,
                "chatterbox_api_volume": self.chatterbox_api_volume,
                "chatterbox_api_banned_voice_models": self.chatterbox_api_banned_voice_models,
            },
            "mira_tts": {
                "mira_tts_tts_banned_voice_models": self.mira_tts_tts_banned_voice_models,
            },
            "Debugging": {
                "debug_mode": self.debug_mode,
                "share_debug_ui": self.share_debug_ui,
                "remove_mei_folders": self.remove_mei_folders,
                "play_audio_from_script": self.play_audio_from_script,
                "tts_boot_annoncements": self.tts_boot_annoncements,
                "add_voicelines_to_all_voice_folders": self.add_voicelines_to_all_voice_folders,
                "play_startup_announcement": self.play_startup_announcement,
            },
            "Errors": {
                "block_logs_from": self.block_logs_from,
                "block_log_types": self.block_log_types,
                "error_on_empty_full_reply": self.error_on_empty_full_reply,
                "continue_on_voice_model_error": self.continue_on_voice_model_error,
                "continue_on_missing_character": self.continue_on_missing_character,
                "continue_on_start_type_error": self.continue_on_start_type_error,
                "continue_on_llm_api_error": self.continue_on_llm_api_error,
                "continue_on_failure_to_send_audio_to_game_interface": self.continue_on_failure_to_send_audio_to_game_interface,
                "must_generate_a_sentence": self.must_generate_a_sentence,
                "use_game_event_lines_as_is_if_cannot_parse": self.use_game_event_lines_as_is_if_cannot_parse,
                "bad_author_retries": self.bad_author_retries,
                "retries": self.retries,
                "system_loop": self.system_loop,
            },
            "Config": {
                "linux_mode": self.linux_mode,
                "seed": self.seed,
                "python_binary": self.python_binary,
                "character_database_file": self.character_database_file,
                "conversation_data_directory": self.conversation_data_directory,
                "voice_model_ref_ids_file": self.voice_model_ref_ids_file,
                "logging_file_path": self.logging_file_path,
                "web_configurator": self.web_configurator,
                "open_config_on_startup": self.open_config_on_startup,
                "config_port": self.config_port,
                "memory_editor_port": self.memory_editor_port,
                "debug_ui_port": self.debug_ui_port,
            }
        }
    
    def default_types(self):
        typesobj = {}
        default = self.default()
        for key in default:
            typesobj[key] = {}
            for sub_key in default[key]:
                # typesobj[key][sub_key] = str(type(default[key][sub_key]))
                text = str(type(default[key][sub_key]))
                text = text.split("'")[1]
                typesobj[key][sub_key] = text
        # print("Default types:", typesobj)
        return typesobj
    
    def mulitple_choice(self):
        return {
            "Game": {
                "game_id": ["skyrim", "skyrimvr", "falloutnv", "fallout4", "fallout4vr"],
                "conversation_manager_type": ["auto"]+[conversation_manager_type for conversation_manager_type in self.manager_types["conversation_manager"]],
                "interface_type": ["auto"]+[interface_type for interface_type in self.manager_types["game_interface"]],
                "behavior_manager": ["auto"]+[behavior_manager for behavior_manager in self.manager_types["behavior_manager"]],
                "memory_manager": ["auto"]+[memory_manager_slug.split(".")[0]  for memory_manager_slug in os.listdir(os.path.join(os.path.dirname(__file__), "memory_managers/")) if memory_manager_slug.endswith(".py") and not memory_manager_slug.startswith("__")],
                "character_manager_type": ["auto"]+[character_manager_type for character_manager_type in self.manager_types["character_manager"]],
                "character_db_type": ["auto"]+[character_db_type for character_db_type in self.manager_types["character_dbs"]],
            },
            "summarizing_memory": {
                "summarizing_memory_direction": ["topdown","bottomup"],
            },
            "chromadb_memory": {
                "chromadb_memory_direction": ["topdown","bottomup"],
            },
            "SpeechToText": {
                "stt_engine": [stt_engine.split(".")[0] for stt_engine in os.listdir(os.path.join(os.path.dirname(__file__), "stt_types/")) if stt_engine.endswith(".py") and not stt_engine.startswith("__")],
                "stt_language": ["default","af","am","ar","as","az","ba","be","bg","bn","bo","br","bs","ca","cs","cy","da","de","el","en","es","et","eu","fa","fi","fo","fr","gl","gu","ha","haw","he","hi","hr","ht","hu","hy","id","is","it","ja","jw","ka","kk","km","kn","ko","la","lb","ln","lo","lt","lv","mg","mi","mk","ml","mn","mr","ms","mt","my","ne","nl","nn","no","oc","pa","pl","ps","pt","ro","ru","sa","sd","si","sk","sl","sn","so","sq","sr","su","sv","sw","ta","te","tg","th","tk","tl","tr","tt","uk","ur","uz","vi","yi","yo","zh","yue"]
            },
            "whisper": {
                "whisper_model": ["tiny", "tiny.en", "base", "base.en", "small", "small.en", "distil-small.en", "medium", "medium.en", "distil-medium.en", "large-v1", "large-v2", "large-v3", "large", "distil-large-v2", "distil-large-v3"],
            },
            "faster_whisper": {
                "whisper_process_device": ["auto","cpu", "cuda"],
                "whisper_compute_type": ["auto", "int8", "int8_float32", "int8_float16", "int8_bfloat16", "int16", "float16", "bfloat16", "float32"],
            },
            "LanguageModel": {
                "inference_engine": [inference_engine for inference_engine in self.manager_types["language_model"]],
                "tokenizer_type": [tokenizer_type for tokenizer_type in self.manager_types["tokenizer"]],
            },
            "PromptStyle": {
                "prompt_style": [behavior_style.split(".")[0] for behavior_style in os.listdir(os.path.join(os.path.dirname(__file__), "../prompt_styles"))],
                "behavior_style": [behavior_style.split(".")[0] for behavior_style in os.listdir(os.path.join(os.path.dirname(__file__), "../behavior_styles"))],
                "conversation_start_type": [
                    "always_llm_choice",
                    "always_force_npc_greeting",
                    "always_player_greeting",
                    "implicit_predetermined_player_greeting",
                    "predetermined_npc_greeting",
                    "predetermined_npc_greeting_for_first_meeting_then_llm_choice",
                    "force_npc_greeting_for_first_meeting_then_llm_choice"
                ],
                "conversation_start_role": [
                    "user",
                    "system",
                    "assistant",
                ]
            },
            "InferenceOptions": {
                "thought_type": [thought_type for thought_type in self.manager_types["thought_process"]],
                "character_type": ["auto"]+[character_type for character_type in self.manager_types["character_manager"]],
            },
            "Vision": {
                "ocr_lang": list(set(['en', 'af', 'az', 'bs', 'cs', 'cy', 'da', 'de', 'es', 'et', 'fr', 'ga', 'hr', 'hu', 'id', 'is', 'it', 'ku', 'la', 'lt', 'lv', 'mi', 'ms', 'mt', 'nl', 'no', 'oc', 'pi', 'pl', 'pt', 'ro', 'rs_latin', 'sk', 'sl', 'sq', 'sv', 'sw', 'tl', 'tr', 'uz', 'vi', 'french', 'german'] + ['ar', 'fa', 'ug', 'ur'] + ['ru', 'rs_cyrillic', 'be', 'bg', 'uk', 'mn', 'abq', 'ady', 'kbd', 'ava', 'dar', 'inh', 'che', 'lbe', 'lez', 'tab'] + ['hi', 'mr', 'ne', 'bh', 'mai', 'ang', 'bho', 'mah', 'sck', 'new', 'gom', 'sa', 'bgc']))
            },
            "openai_api":{
                "openai_completions_type": ["text","chat"]
            }
        }

    def host_config_server(self, conversation_manager):
        self.conversation_manager = conversation_manager
        self.config_server_app = LoglessFlask(__name__)

        @self.config_server_app.route('/config', methods=['GET'])
        def get_config():
            # export = self.export()
            # print(export)
            config = json.load(open(self.config_path))
            return flask.jsonify(config)
        
        @self.config_server_app.route('/config', methods=['POST'])
        def post_config():
            default_types = self.default_types()
            data = flask.request.json
            for key in data:
                for sub_key in data[key]:
                    if type(getattr(self,sub_key)) is not type(data[key][sub_key]):
                        if type(getattr(self,sub_key)) is list:
                            setattr(self, sub_key, str(data[key][sub_key]).split(","))
                        else:
                            if default_types[key][sub_key] == "bool":
                                setattr(self, sub_key, bool(data[key][sub_key]))
                            elif default_types[key][sub_key] == "int":
                                setattr(self, sub_key, int(data[key][sub_key]))
                            elif default_types[key][sub_key] == "float":
                                setattr(self, sub_key, float(data[key][sub_key]))
                            elif default_types[key][sub_key] == "dict":
                                setattr(self, sub_key, json.loads(data[key][sub_key]))
                            elif default_types[key][sub_key] == "list":
                                new_list = data[key][sub_key]
                                if type(data[key][sub_key]) is str:
                                    new_list = str(data[key][sub_key]).split(",")
                                new_list = [item.strip() for item in new_list if item.strip() != ""]
                                if len(new_list) == 0:
                                    new_list = []
                                elif len(new_list) == 1 and new_list[0] == "":
                                    new_list = []
                                setattr(self, sub_key, new_list)
                            else:
                                setattr(self, sub_key, str(data[key][sub_key]))
            # self.save()
            self.save_json(data)
            self.conversation_manager.restart = True
            if not self.conversation_manager.in_conversation:
                logging.info("Config updated and conversation manager not in a conversation. Restart the conversation manager to apply the new settings. - WILL BE FIXED IN FUTURE RELEASE")
            # return flask.jsonify(self.export())
            config = json.load(open(self.config_path))
            return flask.jsonify(config)
        
        @self.config_server_app.route('/defaults', methods=['GET'])
        def get_default():
            print(self.default())
            print(self.default_types())
            print(self.descriptions())
            return flask.jsonify({
                "defaultConfig": self.default(),
                "types": self.default_types(),
                "descriptions": self.descriptions()
            })
        
        @self.config_server_app.route('/voice-samples', methods=['GET'])
        def get_voice_samples():
            if self.linux_mode:
                voice_samples_relative_path = "../data/voice_samples"
            else:
                voice_samples_relative_path = "..\\data\\voice_samples"
            if self.linux_mode:
                tts_settings_relative_path = "../data/tts_settings"
            else:
                tts_settings_relative_path = "..\\data\\tts_settings"
            voice_samples_dirs_dir = os.path.join(os.path.dirname(__file__), voice_samples_relative_path)
            voice_samples = []
            for language_dir in os.listdir(voice_samples_dirs_dir):
                voice_sample_path = os.path.join(voice_samples_dirs_dir, language_dir)
                if os.path.isdir(voice_sample_path):
                    for voice_sample_file in os.listdir(voice_sample_path):
                        if voice_sample_file.endswith(".wav"):
                            voice_sample_full_path = os.path.join(voice_sample_path, voice_sample_file)
                            voice_sample_obj = {
                                "voice_model": voice_sample_file.split(".")[0],
                                "file_name": voice_sample_file,
                                "language": language_dir,
                                "tts_settings": {},
                            }
                            with open(voice_sample_full_path, 'rb') as f: # Read the wave file and encode it to base64
                                voice_sample_obj["data"] = base64.b64encode(f.read()).decode('utf-8')
                            # Read all tts_settings JSON files to get the inference settings for the voice sample for each TTS engine
                            for tts_engine_dir in os.listdir(os.path.join(os.path.dirname(__file__), tts_settings_relative_path)):
                                tts_settings_path = os.path.join(os.path.dirname(__file__), tts_settings_relative_path, tts_engine_dir, language_dir, f"{voice_sample_file.split('.')[0]}.json")
                                tts_settings_path = os.path.abspath(tts_settings_path)
                                if os.path.exists(tts_settings_path):
                                    with open(tts_settings_path, 'r') as tts_f:
                                        tts_settings = json.load(tts_f)
                                        voice_sample_obj["tts_settings"][tts_engine_dir] = tts_settings
                            voice_samples.append(voice_sample_obj)
            return flask.jsonify(voice_samples)
        
        @self.config_server_app.route('/voice-models', methods=['GET'])
        def get_voice_models():
            required_voice_models = self.conversation_manager.character_database.all_voice_formatted_models
            available_voice_models = self.conversation_manager.synthesizer.voices()
            voice_models = []
            for voice_model in required_voice_models:
                voice_model_obj = {
                    "voice_model": voice_model,
                    "available": voice_model in available_voice_models
                }
                voice_models.append(voice_model_obj)
            return flask.jsonify(voice_models)
        
        @self.config_server_app.route('/tts-engines', methods=['GET'])
        def get_tts_engines():
            tts_engines = {}
            # engine_slugs = self.tts_engine
            for tts_engine_slug in tts.tts_Types:
                if tts_engine_slug != "default" and tts_engine_slug != "multi_tts":
                    if len(tts.tts_Types[tts_engine_slug].default_settings) > 0:
                        class_metadata = {
                            "description": tts.tts_Types[tts_engine_slug].Synthesizer.__doc__,
                            "class_name": tts.tts_Types[tts_engine_slug].Synthesizer.__name__,
                            "methods": [],
                        }
                        for method_name in dir(tts.tts_Types[tts_engine_slug].Synthesizer):
                            if not method_name.startswith("__") and callable(getattr(tts.tts_Types[tts_engine_slug].Synthesizer, method_name)):
                                method = getattr(tts.tts_Types[tts_engine_slug].Synthesizer, method_name)
                                method_metadata = {
                                    "name": method_name,
                                    "doc": method.__doc__,
                                    "parameters": list(method.__code__.co_varnames[:method.__code__.co_argcount]),
                                    "return_type": str(method.__annotations__.get('return', 'None')),
                                }
                                class_metadata["methods"].append(method_metadata)
                        tts_engines[tts_engine_slug] = {
                            "name": tts_engine_slug,
                            "default_settings": tts.tts_Types[tts_engine_slug].default_settings,
                            "settings_description": tts.tts_Types[tts_engine_slug].settings_description,
                            "options": tts.tts_Types[tts_engine_slug].options,
                            "loaded": tts.tts_Types[tts_engine_slug].loaded,
                            "imported": tts.tts_Types[tts_engine_slug].imported,
                            "description": tts.tts_Types[tts_engine_slug].description,
                            "class_metadata": class_metadata,
                        }
            return flask.jsonify(tts_engines)

        @self.config_server_app.route('/inference-engines', methods=['GET'])
        def get_inference_engines():
            inference_engines = {}
            for inference_engine_slug in language_models.LLM_Types:
                if inference_engine_slug != "base_LLM" and inference_engine_slug != "default":
                    if len(language_models.LLM_Types[inference_engine_slug].default_settings) > 0:
                        # derive class metadata from the language_models.LLM_Types[inference_engine_slug].LLM class - Must be JSON serializable
                        class_metadata = {
                            "description": language_models.LLM_Types[inference_engine_slug].LLM.__doc__,
                            "class_name": language_models.LLM_Types[inference_engine_slug].LLM.__name__,
                            "methods": [],
                        }
                        for method_name in dir(language_models.LLM_Types[inference_engine_slug].LLM):
                            if not method_name.startswith("__") and callable(getattr(language_models.LLM_Types[inference_engine_slug].LLM, method_name)):
                                method = getattr(language_models.LLM_Types[inference_engine_slug].LLM, method_name)
                                method_metadata = {
                                    "name": method_name,
                                    "doc": method.__doc__,
                                    "parameters": list(method.__code__.co_varnames[:method.__code__.co_argcount]),
                                    "return_type": str(method.__annotations__.get('return', 'None')),
                                }
                                class_metadata["methods"].append(method_metadata)
                        logging.info("Class metadata for", inference_engine_slug, ":", class_metadata)
                        inference_engines[inference_engine_slug] = {
                            "inference_engine_name": inference_engine_slug,
                            "tokenizer_slug": language_models.LLM_Types[inference_engine_slug].tokenizer_slug,
                            "default_settings": language_models.LLM_Types[inference_engine_slug].default_settings,
                            "settings_description": language_models.LLM_Types[inference_engine_slug].settings_description,
                            "options": language_models.LLM_Types[inference_engine_slug].options,
                            "loaded": language_models.LLM_Types[inference_engine_slug].loaded,
                            "imported": language_models.LLM_Types[inference_engine_slug].imported,
                            "description": language_models.LLM_Types[inference_engine_slug].description,
                            "class_metadata": class_metadata,
                        }
            # tokenizers_list = []
            # for tokenizer_type in tokenizers.Tokenizer_Types:
            #     if tokenizer_type != "default":
            #         tokenizers_list.append(tokenizer_type)
            return flask.jsonify({
                "default": language_models.default,
                "loaded_tokenizer_slug": language_models.loaded_tokenizer_slug,
                # "available_tokenizers": tokenizers_list,
                "inference_engines": inference_engines,
            })
        
        @self.config_server_app.route('/characters', methods=['GET'])
        def get_characters():
            return flask.jsonify(self.conversation_manager.character_database.characters)

        @self.config_server_app.route('/multiple-choice', methods=['GET'])
        def get_multiple_choice():
            return flask.jsonify(self.mulitple_choice())
        @self.config_server_app.route('/banned-modules', methods=['GET'])
        def get_banned_modules():
            with open(os.path.join(os.path.dirname(__file__), "../src/banned_modules"), 'r') as f:
                return f.read()
        @self.config_server_app.route('/banned-modules', methods=['POST'])
        def post_banned_modules():
            data = flask.request.json
            banned_modules_string = "\n".join(data["banned_modules"])
            with open(os.path.join(os.path.dirname(__file__), "../src/banned_modules"), 'w') as f:
                f.write(banned_modules_string)
            return flask.jsonify({"status": "success", "message": "Banned modules updated."})
        @self.config_server_app.route('/prompt-style', methods=['GET'])
        def get_prompt_style(prompt_style_slug):
            prompt_style_slug = flask.request.args.get('prompt_style_slug', default=None, type=str)
            if prompt_style_slug is None:
                return flask.jsonify({"error": "No prompt style slug provided."}), 400
            prompt_style_path = os.path.join(os.path.dirname(__file__), "../prompt_styles", f"{prompt_style_slug}.json")
            if not os.path.exists(prompt_style_path):
                return flask.jsonify({"error": "Prompt style not found."}), 404
            with open(prompt_style_path, 'r') as f:
                return f.read()
        @self.config_server_app.route('/prompt-style', methods=['POST'])
        def post_prompt_style():
            data = flask.request.json
            prompt_style_slug = data.get("prompt_style_slug")
            if not prompt_style_slug:
                return flask.jsonify({"error": "No prompt style slug provided."}), 400
            prompt_style_path = os.path.join(os.path.dirname(__file__), "../prompt_styles", f"{prompt_style_slug}.json")
            if not os.path.exists(prompt_style_path):
                return flask.jsonify({"error": "Prompt style not found."}), 404
            with open(prompt_style_path, 'w') as f:
                json.dump(data, f, indent=4)
            return flask.jsonify({"status": "success", "message": "Prompt style updated."})
        @self.config_server_app.route('/behavior-style', methods=['GET'])
        def get_behavior_style(behavior_style_slug):
            behavior_style_slug = flask.request.args.get('behavior_style_slug', default=None, type=str)
            if behavior_style_slug is None:
                return flask.jsonify({"error": "No behavior style slug provided."}), 400
            behavior_style_path = os.path.join(os.path.dirname(__file__), "../behavior_styles", f"{behavior_style_slug}.json")
            if not os.path.exists(behavior_style_path):
                return flask.jsonify({"error": "Behavior style not found."}), 404
            with open(behavior_style_path, 'r') as f:
                return f.read()
        @self.config_server_app.route('/behavior-style', methods=['POST'])
        def post_behavior_style():
            data = flask.request.json
            behavior_style_slug = data.get("behavior_style_slug")
            if not behavior_style_slug:
                return flask.jsonify({"error": "No behavior style slug provided."}), 400
            behavior_style_path = os.path.join(os.path.dirname(__file__), "../behavior_styles", f"{behavior_style_slug}.json")
            if not os.path.exists(behavior_style_path):
                return flask.jsonify({"error": "Behavior style not found."}), 404
            with open(behavior_style_path, 'w') as f:
                json.dump(data, f, indent=4)
            return flask.jsonify({"status": "success", "message": "Behavior style updated."})
        @self.config_server_app.route('/add-voice-samples', methods=['POST'])
        def add_voice_samples():
            data = flask.request.json
            voice_sample_base64 = data.get("voice_sample_base64")
            voice_sample_name = data.get("voice_sample_name")
            voice_sample_path = os.path.join(os.path.dirname(__file__), "../voice_samples", f"{voice_sample_name}.wav")
            if not voice_sample_base64 or not voice_sample_name:
                return flask.jsonify({"error": "No voice sample base64 or name provided."}), 400
            try:
                with open(voice_sample_path, 'wb') as f:
                    f.write(base64.b64decode(voice_sample_base64))
                return flask.jsonify({"status": "success", "message": "Voice sample added."})
            except Exception as e:
                logging.error(f"Error adding voice sample: {e}")
                return flask.jsonify({"error": "Failed to add voice sample."}), 500
        @self.config_server_app.route('/restart', methods=['POST'])
        def restart():
            logging.info("Restarting the config server...")
            try:
                self.conversation_manager = restart_manager(self, self.conversation_manager)
                return flask.jsonify({"status": "success", "message": "Config server is restarting."})
            except Exception as e:
                logging.error(f"Error restarting the config server: {e}")
                return flask.jsonify({"error": "Failed to restart the config server.", "details": str(e)}), 500
        @self.config_server_app.route('/', methods=['GET'])
        def index(): # Return the index.html file
            return flask.send_file(os.path.join(os.path.dirname(__file__), '../webconfigurator/index.html'))
        @self.config_server_app.route('/log', methods=['GET'])
        def log(): # Return the index.html file
            try:
                last_500_lines = []
                with open(os.path.join(os.path.dirname(__file__), "../logging.log"), 'r') as f:
                    lines = f.readlines()
                    last_500_lines = lines[-500:]
                last_500_lines = "\n".join(last_500_lines)
                while "\n\n" in last_500_lines:
                    last_500_lines = last_500_lines.replace("\n\n", "\n")
                return last_500_lines
            except Exception as e:
                logging.error(f"Error reading log file: {e}")
                return flask.jsonify({"error": "Failed to read log file.", "details": str(e)}), 500
        @self.config_server_app.route('/jquery-3.7.1.min.js', methods=['GET'])
        def jquery():
            return flask.send_file(os.path.join(os.path.dirname(__file__), '../webconfigurator/jquery-3.7.1.min.js'))
        @self.config_server_app.route('/logo.png', methods=['GET'])
        def get_logo():
            return flask.send_file(os.path.join(os.path.dirname(__file__), '../img/pantella_logo_github.png'))
        logging.info(f"Running config server on port http://localhost:{self.config_port}/")
        self.config_server_app.run(port=self.config_port, threaded=True)
        logging.info(f"Config server running on port http://localhost:{self.config_port}/")
