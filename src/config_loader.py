import configparser
import logging
import json
import os
import sys

class ConfigLoader:
    def __init__(self, file_name='config.ini'):
        config = configparser.ConfigParser()
        config.read(file_name, encoding='utf-8')

        def invalid_path(set_path, tested_path):
            logging.error(f"\"{tested_path}\" does not exist!\n\nThe path set in config.ini: \"{set_path}\"")
            input('\nPress any key to exit...')
            sys.exit(0)

        def check_missing_mantella_file(set_path):
            if not os.path.exists(set_path+'/_mantella__skyrim_folder.txt'):
                logging.warn(f'''
Warning: Could not find _mantella__skyrim_folder.txt in {set_path}. 
If you have not yet casted the Mantella spell in-game you can safely ignore this message. 
If you have casted the Mantella spell please check that your 
MantellaSoftware/config.ini "skyrim_folder" has been set correctly 
(instructions on how to set this up are in the config file itself).
If you are still having issues, a list of solutions can be found here: 
https://github.com/art-from-the-machine/Mantella#issues-qa
''')

        def run_config_editor():
            try:
                import src.config_editor as configeditor

                logging.info('Launching config editor...')
                configeditor.start()
                logging.info(f'Config editor closed. Re-reading {file_name} file...')

                config.read(file_name)
            except Exception as e:
                logging.error('Unable to run config editor!')
                raise e

        try:
            # [Startup]
            # run config editor if config.ini has the parameter
            self.open_config_editor = bool(int(config['Startup']['open_config_editor']))
            if self.open_config_editor:
                run_config_editor()

            # [Game]
            self.game_id = str(config['Game']['game_id']).lower() # skyrim, fallout4

            # [Paths]
            self.game_path = config['Paths']['skyrim_folder']
            self.xvasynth_path = config['Paths']['xvasynth_folder']
            self.mod_path = config['Paths']['mod_folder']
            self.character_database_file = config['Paths']['character_database_file']
            self.voice_model_ref_ids_file = config['Paths']['voice_model_ref_ids_file']
            self.logging_file_path = config['Paths']['logging_file_path']
            self.language_support_file_path = config['Paths']['language_support_file_path']

            # [Language]
            self.language = config['Language']['language']
            self.end_conversation_keyword = config['Language']['end_conversation_keyword']
            self.goodbye_npc_response = config['Language']['goodbye_npc_response']
            self.collecting_thoughts_npc_response = config['Language']['collecting_thoughts_npc_response']

            # [Microphone]
            self.mic_enabled = config['Microphone']['microphone_enabled']
            self.whisper_model = config['Microphone']['model_size']
            self.stt_language = config['Microphone']['stt_language']
            if (self.stt_language == 'default'):
                self.stt_language = self.language
            self.stt_translate = bool(int(config['Microphone']['stt_translate']))
            self.whisper_process_device = config['Microphone']['process_device']
            self.whisper_type = config['Microphone']['whisper_type']
            self.whisper_url = config['Microphone']['whisper_url']
            self.audio_threshold = config['Microphone']['audio_threshold']
            self.pause_threshold = float(config['Microphone']['pause_threshold'])
            self.listen_timeout = int(config['Microphone']['listen_timeout'])

            # [Hotkey]
            # self.hotkey = config['Hotkey']['hotkey']
            # self.textbox_timer = config['Hotkey']['textbox_timer']

            # [LanguageModel]
            self.inference_engine = config['LanguageModel']['inference_engine']
            self.tokenizer_type = config['LanguageModel']['tokenizer_type']
            self.maximum_local_tokens = int(config['LanguageModel']['maximum_local_tokens'])
            self.max_response_sentences = int(config['LanguageModel']['max_response_sentences'])
            self.wait_time_buffer = float(config['LanguageModel']['wait_time_buffer'])
            stop_value = config['LanguageModel']['stop']
            if ',' in stop_value:
                # If there are commas in the stop value, split the string by commas and store the values in a list
                self.stop = stop_value.split(',')
            else:
                # If there are no commas, put the single value into a list
                self.stop = [stop_value]
            
            self.temperature = float(config['LanguageModel']['temperature'])
            self.top_p = float(config['LanguageModel']['top_p'])
            self.min_p = float(config['LanguageModel']['min_p'])
            self.top_k = int(config['LanguageModel']['top_k'])
            self.repeat_penalty = float(config['LanguageModel']['repeat_penalty'])
            self.max_tokens = int(config['LanguageModel']['max_tokens'])

            self.BOS_token = str(config['LanguageModel']['BOS_token'])
            self.EOS_token = str(config['LanguageModel']['EOS_token'])
            self.message_signifier = str(config['LanguageModel']['message_signifier'])
            if "//" in self.message_signifier or "\\" in self.message_signifier:
                self.message_signifier = self.message_signifier.replace("//n", "\n")
                self.message_signifier = self.message_signifier.replace("\\n", "\n")
            self.message_seperator = str(config['LanguageModel']['message_seperator'])
            if "//" in self.message_seperator or "\\" in self.message_seperator:
                self.message_seperator = self.message_seperator.replace("//n", "\n")
                self.message_seperator = self.message_seperator.replace("\\n", "\n")
            self.message_format = str(config['LanguageModel']['message_format'])
            
            self.system_name = str(config['LanguageModel']['system_name'])
            self.user_name = str(config['LanguageModel']['user_name'])
            self.assistant_name = str(config['LanguageModel']['assistant_name'])

            self.assist_check = bool(int(config['LanguageModel']['assist_check']))
            self.strip_smalls = bool(int(config['LanguageModel']['strip_smalls']))
            self.small_size = int(config['LanguageModel']['small_size'])
            self.same_output_limit = int(config['LanguageModel']['same_output_limit'])
            
            self.conversation_limit_pct = float(config['LanguageModel']['conversation_limit_pct'])
            self.reload_buffer = int(config['LanguageModel']['reload_buffer'])
            self.reload_wait_time = float(config['LanguageModel']['reload_wait_time'])
            
            self.experimental_features = bool(int(config['LanguageModel']['experimental_features']))

            # [openai_api]
            self.llm = config['openai_api']['model']
            self.alternative_openai_api_base = config['openai_api']['alternative_openai_api_base']
            self.secret_key_file_path = config['openai_api']['secret_key_file_path']

            # [llama_cpp_python]
            self.model_path = config['llama_cpp_python']['model_path']
            self.n_gpu_layers = int(config['llama_cpp_python']['n_gpu_layers'])
            self.n_threads = int(config['llama_cpp_python']['n_threads'])
            self.n_batch = int(config['llama_cpp_python']['n_batch'])
            self.tensor_split = [float(i.strip()) for i in config['llama_cpp_python']['tensor_split'].split(',')]
            self.main_gpu = int(config['llama_cpp_python']['main_gpu'])

            # [Speech]
            self.tts_engine = str(config['Speech']['tts_engine'])
            self.end_conversation_wait_time = float(config['Speech']['end_conversation_wait_time'])
            self.sentences_per_voiceline = int(config['Speech']['sentences_per_voiceline']) 

            # [xVASynth]
            self.xvasynth_process_device = str(config['xVASynth']['tts_process_device']) # cpu, cuda
            self.pace = float(config['xVASynth']['pace'])
            self.use_cleanup = int(config['xVASynth']['use_cleanup']) == 1
            self.use_sr = int(config['xVASynth']['use_sr']) == 1
            self.xvasynth_base_url = config['xVASynth']['xvasynth_base_url']

            # [xTTS]
            self.xtts_base_url = config['xTTS']['xtts_base_url']
            self.xtts_data = json.loads(config['xTTS']['xtts_data'].replace('\n', '')) # We can do JSON in the config.ini?? Dude... this would have save so much time and space. TODO: Hot dog, I like it! :D Do this for all the stuff this would benefit.

            # [Cleanup]
            self.remove_mei_folders = config['Cleanup']['remove_mei_folders']

            # [Debugging]
            self.debug_mode = config['Debugging']['debugging']
            self.play_audio_from_script = config['Debugging']['play_audio_from_script']
            self.debug_character_name = config['Debugging']['debugging_npc']
            self.debug_use_mic = config['Debugging']['use_mic']
            self.default_player_response = config['Debugging']['default_player_response']
            self.debug_exit_on_first_exchange = config['Debugging']['exit_on_first_exchange']
            self.add_voicelines_to_all_voice_folders = config['Debugging']['add_voicelines_to_all_voice_folders']

            # [Prompt]
            self.single_npc_prompt = str(config['Prompt']['single_npc_prompt']).replace("//n", "\n").replace("/r", "")
            self.multi_npc_prompt = str(config['Prompt']['multi_npc_prompt']).replace("//n", "\n").replace("/r", "")

            # Other
            self.is_local = False
            pass
        except Exception as e:
            logging.error('Parameter missing/invalid in config.ini file!')
            raise e

        # don't trust; verify; test subfolders
        if not os.path.exists(f"{self.game_path}"):
            invalid_path(self.game_path, f"{self.game_path}")
        else:
            check_missing_mantella_file(self.game_path)

        if not os.path.exists(f"{self.xvasynth_path}\\resources\\"):
            invalid_path(self.xvasynth_path, f"{self.xvasynth_path}\\resources\\")
        if not os.path.exists(f"{self.mod_path}\\Sound\\Voice\\Mantella.esp"):
            invalid_path(self.mod_path, f"{self.mod_path}\\Sound\\Voice\\Mantella.esp")

        self.mod_path += "\\Sound\\Voice\\Mantella.esp"
