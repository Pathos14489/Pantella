from openai import OpenAI
import logging
import pandas as pd
import tiktoken
import src.config_loader as config_loader
import src.tts as tts
import src.utils as utils
import json
import time
import os
import requests
# from aiohttp import ClientSession


class CharacterDB():
    def __init__(self, config, xvasynth): # character_df_directory is the path to a character directory where each character is a seperate json file
        self.config = config
        self.xvasynth = xvasynth # xvasynth is the xvasynth synthesizer object
        self.character_df_path = config.character_df_file
        self.characters = []
        self.named_index = {}
        self.baseid_int_index = {}
        self.valid = []
        self.invalid = []
        self.db_type = None
        # make sure voice_model_ref_ids_file exists
        if not os.path.exists(config.voice_model_ref_ids_file):
            logging.error(f"Could not find voice_model_ref_ids_file at {config.voice_model_ref_ids_file}. Please download the correct file for your game, or correct the filepath in your config.ini and try again.")
            raise FileNotFoundError
        if config.voice_model_ref_ids_file != "" and os.path.exists(config.voice_model_ref_ids_file):
            with open(config.voice_model_ref_ids_file, 'r') as f:
                self.voice_model_ids = json.load(f)
        else:
            self.voice_model_ids = {}

    def loaded(self):
        print(f"{len(self.male_voice_models)} Male voices - {len(self.female_voice_models)} Female voices")
        print("All Required Voice Models:",self.all_voice_models)
        print("Total Required Voice Models:",len(self.all_voice_models))
        print("voice_model_ids:",self.voice_model_ids)

    def load_characters_json(self):
        print(f"Loading character database from {self.character_df_path}...")
        self.characters = []
        self.named_index = {}
        self.baseid_int_index = {}
        for file in os.listdir(self.character_df_path):
            if file.endswith(".json"):
                character = json.load(open(os.path.join(self.character_df_path, file)))
                self.characters.append(character)
                self.named_index[character['name']] = self.characters[-1]
                self.baseid_int_index[character['baseid_int']] = self.characters[-1]
        self.db_type = 'json'
        print(f"Loaded {len(self.characters)} characters from JSON {self.character_df_path}")
        self.loaded()
    
    def load_characters_csv(self):
        print(f"Loading character database from JSON files in {self.character_df_path}...")
        self.characters = []
        self.named_index = {}
        self.baseid_int_index = {}
        encoding = utils.get_file_encoding(self.character_df_path)
        character_df = pd.read_csv(self.character_df_path, engine='python', encoding=encoding)
        character_df = character_df.loc[character_df['voice_model'].notna()]
        for _, row in character_df.iterrows():
            character = row.to_dict()
            self.characters.append(character)
            self.named_index[character['name']] = self.characters[-1]
            self.baseid_int_index[character['baseid_int']] = self.characters[-1]
        self.db_type = 'csv'
        print(f"Loaded {len(self.characters)} characters from csv {self.character_df_path}")
        self.loaded()

    def patch_character_info(self,info): # Patches information about a character into the character database and if db_type is json, saves the changes to the json file
        self.characters.append(info)
        self.named_index[info['name']] = self.characters[-1]
        self.baseid_int_index[info['baseid_int']] = self.characters[-1] 
        if self.db_type == 'json':
            if not os.path.exists(self.character_df_path): # If the directory doesn't exist, create it
                os.makedirs(self.character_df_path) 
            json_file_path = os.path.join(self.character_df_path, info['name']+'.json')
            # If the character already exists, confirm that the user wants to overwrite it
            if os.path.exists(json_file_path):
                overwrite = input(f"Character '{info['name']}' already exists in the database. Overwrite? (y/n): ")
                if overwrite.lower() != 'y':
                    return
            json.dump(info, open(json_file_path, 'w'), indent=4)

    def get_character_by_name(self, name):
        if name in self.named_index:
            return self.named_index[name]
        else:
            logging.warning(f"Could not find character '{name}' in character database using name lookup.")
            return None
        
    def get_character_by_voice_folder(self, voice_folder): # Look through non-generic characters for a character with the given voice folder
        for character in self.characters:
            if character['voice_model'].lower() == voice_folder.lower(): # If the voice model matches, return the character
                return character
        return None # If no character is found, return None
    
    def get_voice_folder_by_voice_model(self, voice_model):
        # print(f"voice_model_ids: {voice_model}/{voice_model.replace(' ', '')}")
        folder = None
        for voice_folder in self.voice_folders:
            if voice_model == voice_folder:
                folder = self.voice_folders[voice_folder]
            if voice_model.replace(' ', '') == voice_folder:
                folder = self.voice_folders[voice_folder]
        # print(f"folder:",folder)
        return folder
    
    def verify_characters(self):
        xvasynth_available_voices = self.xvasynth.voices()
        self.valid = []
        self.invalid = []
        for voice in self.all_voice_models:
            voice_folder = self.get_voice_folder_by_voice_model(voice)
            if voice_folder in xvasynth_available_voices:
                self.valid.append(voice_folder)
            elif voice in self.voice_folders:
                self.valid.append(voice)
            else:
                print(f"invalid voice: {voice} & {voice_folder}")
                self.invalid.append(voice)
                self.invalid.append(voice_folder)
        unused_voices = []
        for voice in xvasynth_available_voices:
            if voice not in self.valid:
                unused_voices.append(voice)
                print(f"unused voice: {voice}")
        print(f"Total unused voices: {len(unused_voices)}")
        if len(self.invalid) > 0:
            logging.warning(f"Invalid voices found in character database: {self.invalid}. Please check that the voices are installed and try again.")
            for character in self.characters:
                if character['voice_model'] in self.invalid:
                    if character['voice_model'] != "":
                        logging.warning(f"Character '{character['name']}' uses invalid voice model '{character['voice_model']}'")
        logging.info(f"Valid voices found in character database: {len(self.valid)}/{len(self.all_voice_models)}")
        
    @property
    def male_voice_models(self):
        valid = {}
        for character in self.characters:
            if character["gender"] == "Male" and "Female" not in character["voice_model"]:
                if character['voice_model'] not in valid and character['voice_model'] != character['name']:
                    valid[character['voice_model']] = [character['name']]
                elif character['voice_model'] != character['name']:
                    valid[character['voice_model']].append(character['name'])
        filtered = []
        for model in valid:
            if len(valid[model]) > 1:
                filtered.append(model)
        models = {}
        for character in self.characters:
            race_string = character['race']+"Race"
            if character["voice_model"] in filtered and character["voice_model"] != "":
                if race_string not in models:
                    models[race_string] = [character['voice_model']]
                else:
                    if character["voice_model"] not in models[race_string]:
                        models[race_string].append(character['voice_model'])
        return models
    
    @property
    def female_voice_models(self):
        valid = {}
        for character in self.characters:
            if character["gender"] == "Female" and "Male" not in character["voice_model"]:
                if character['voice_model'] not in valid and character['voice_model'] != character['name']:
                    valid[character['voice_model']] = [character['name']]
                elif character['voice_model'] != character['name']:
                    valid[character['voice_model']].append(character['name'])
        filtered = []
        for model in valid:
            if len(valid[model]) > 1:
                filtered.append(model)
        models = {}
        for character in self.characters:
            race_string = character['race']+"Race"
            if character["voice_model"] in filtered and character["voice_model"] != "":
                if race_string not in models:
                    models[race_string] = [character['voice_model']]
                else:
                    if character["voice_model"] not in models[race_string]:
                        models[race_string].append(character['voice_model'])
        return models
    
    @property
    def all_voice_models(self):
        models = []
        for character in self.characters:
            if character["voice_model"] != "":
                if character["voice_model"] not in models:
                    models.append(character["voice_model"])
        return models
        
    @property
    def voice_folders(self): # Returns a dictionary of voice models and their corresponding voice folders
        folders = {} 
        for character in self.characters:
            if character['voice_model'] != "":
                if character['voice_model'] not in folders:
                    if character['skyrim_voice_folder'] != "":
                        folders[character['voice_model']] = [character['skyrim_voice_folder']]
                    else:
                        folders[character['voice_model']] = [character['voice_model']]
                else:
                    if character["skyrim_voice_folder"] not in folders[character['voice_model']]:
                        if character['skyrim_voice_folder'] != "":
                            folders[character['voice_model']].append(character['skyrim_voice_folder'])
                        else:
                            folders[character['voice_model']].append(character['voice_model'])
        new_folders = {}
        for folder in folders:
            if len(folders[folder]) > 1:
                new_folders[folder] = folders[folder]
            else:
                new_folders[folder] = folders[folder][0]
        folders = new_folders
        return folders
    
        
    
            
        

class Tokenizer(): # Tokenizes(only availble for counting the tokens in a string presently for local_models), and parses and formats messages for use with the language model
    def __init__(self,config, client):
        self.encoding = None
        self.config = config
        self.client = client
        if not self.config.is_local: # If we're using OpenAI, we can use the tiktoken library to get the number of tokens used by the prompt
            self.encoding = tiktoken.encoding_for_model(config.llm)
            
        self.BOS_token = config.BOS_token
        self.EOS_token = config.EOS_token
        self.message_signifier = config.message_signifier
        self.message_seperator = config.message_seperator
        self.message_format = config.message_format

    def named_parse(self, msg, name): # Parses a string into a message format with the name of the speaker
        parsed_msg = self.message_format
        parsed_msg = parsed_msg.replace("[BOS_token]",self.BOS_token)
        parsed_msg = parsed_msg.replace("[name]",name)
        parsed_msg = parsed_msg.replace("[message_signifier]",self.message_signifier)
        parsed_msg = parsed_msg.replace("[content]",msg)
        parsed_msg = parsed_msg.replace("[EOS_token]",self.EOS_token)
        parsed_msg = parsed_msg.replace("[message_seperator]",self.message_seperator)
        return parsed_msg

    def start_message(self, name): # Returns the start of a message with the name of the speaker
        parsed_msg = self.message_format
        parsed_msg = parsed_msg.split("[content]")[0]
        parsed_msg = parsed_msg.replace("[BOS_token]",self.BOS_token)
        parsed_msg = parsed_msg.replace("[name]",name)
        parsed_msg = parsed_msg.replace("[message_signifier]",self.message_signifier)
        parsed_msg = parsed_msg.replace("[EOS_token]",self.EOS_token)
        parsed_msg = parsed_msg.replace("[message_seperator]",self.message_seperator)
        return parsed_msg

    def end_message(self, name=""): # Returns the end of a message with the name of the speaker (Incase the message format chosen requires the name be on the end for some reason, but it's optional to include the name in the end message)
        parsed_msg = self.message_format
        parsed_msg = parsed_msg.split("[content]")[1]
        parsed_msg = parsed_msg.replace("[BOS_token]",self.BOS_token)
        parsed_msg = parsed_msg.replace("[name]",name)
        parsed_msg = parsed_msg.replace("[message_signifier]",self.message_signifier)
        parsed_msg = parsed_msg.replace("[EOS_token]",self.EOS_token)
        parsed_msg = parsed_msg.replace("[message_seperator]",self.message_seperator)
        return parsed_msg

    def get_string_from_messages(self, messages): # Returns a formatted string from a list of messages
        context = ""
        for message in messages:
            context += self.named_parse(message["content"],message["role"])
        return context

    def num_tokens_from_messages(self, messages): # Returns the number of tokens used by a list of messages
        """Returns the number of tokens used by a list of messages"""
        context = self.get_string_from_messages(messages)
        context += self.start_message(self.config.assistant_name) # Simulate the assistant replying to add a little more to the token count to be safe (this is a bit of a hack, but it should work 99% of the time I think) TODO: Determine if needed
        return self.get_token_count(context)
        
    def get_token_count(self, string):
        if self.config.is_local: # If we're using the api, we can just ask it how many tokens it used by looking at the prompt_tokens usage via an embedding call
            embedding = self.client.embeddings.create(
                model=self.config.llm,
                input=string
            )
            num_tokens = int(embedding.usage.prompt_tokens)
        else: # If we're using OpenAI, we can use the tiktoken library to get the number of tokens used by the prompt
            tokens = self.encoding.encode(string)
            num_tokens = len(tokens)
        return num_tokens

class LLM():
    def __init__(self, config, client, tokenizer, token_limit, language_info):
        self.config = config
        self.client = client
        self.tokenizer = tokenizer
        self.token_limit = token_limit
        self.language_info = language_info
    
    @utils.time_it
    def chatgpt_api(self, input_text, messages):
        print(f"ChatGPT API: {input_text}")
        print(f"Messages: {messages}")
        if input_text:
            messages.append(
                {"role": "user", "content": input_text},
            )
            logging.info('Getting LLM response...')
            chat_completion = self.create(messages)
        
        reply = chat_completion.choices[0].message.content
        messages.append(
            {"role": "assistant", "content": chat_completion.choices[0].message.content},
        )
        logging.info(f"LLM Response: {reply}")

        return reply, messages
    
    def create(self, messages):
        print(f"cMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                if self.config.is_local: # If local, don't do the weird header thing. Doesn't break anything, but it's weird.
                    prompt = self.tokenizer.get_string_from_messages(messages)
                    completion = self.client.completions.create(
                        model=self.config.llm, prompt=prompt, max_tokens=self.config.max_tokens
                    )
                else:
                    completion = self.client.chat.completions.create(
                        model=self.config.llm, messages=messages, headers={"HTTP-Referer": 'https://github.com/art-from-the-machine/Mantella', "X-Title": 'mantella'}, stop=self.config.stop,temperature=self.config.temperature,top_p=self.config.top_p,frequency_penalty=self.config.frequency_penalty, max_tokens=self.config.max_tokens
                    )
            except Exception as e:
                logging.warning('Could not connect to LLM API, retrying in 5 seconds...')
                logging.warning(e)
                print(e)
                if retries == 1:
                    logging.error('Could not connect to LLM API after 5 retries, exiting...')
                    input('Press enter to continue...')
                    exit()
                time.sleep(5)
                retries -= 1
                continue
            break
        return completion
    
    def acreate(self, messages):
        # print(f"acMessages: {messages}")
        # if self.alternative_openai_api_base == 'none': # if using the default API base, use the default aiohttp session - I don't think this is needed anymore, but I'm keeping it here just in case
        #     openai.aiosession.set(ClientSession()) # https://github.com/openai/openai-python#async-api
        # if self.config.is_local: # If local, don't do the weird header thing. Doesn't break anything, but it's weird.
        #     generator = self.client.chat.completions.create(model=self.config.llm, messages=messages,stream=True,stop=self.config.stop,temperature=self.config.temperature,top_p=self.config.top_p,frequency_penalty=self.config.frequency_penalty, max_tokens=self.config.max_tokens)
        # else: # honestly no idea why the header is needed, but I guess I'll leave it for OpenAI support incase that's something they require?
        #     generator = self.client.chat.completions.create(model=self.config.llm, messages=messages, headers={"HTTP-Referer": 'https://github.com/art-from-the-machine/Mantella', "X-Title": 'mantella'},stream=True,stop=self.stop,temperature=self.temperature,top_p=self.top_p,frequency_penalty=self.frequency_penalty, max_tokens=self.max_tokens)
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                prompt = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message("") # Start empty message from no one to let the LLM generate the speaker by split \n
                print(f"avPrompt: {prompt}")
                return self.client.completions.create(
                    model=self.config.llm, prompt=prompt, max_tokens=self.config.max_tokens, stream=True # , stop=self.stop, temperature=self.temperature, top_p=self.top_p, frequency_penalty=self.frequency_penalty, stream=True
                )
            except Exception as e:
                logging.warning('Could not connect to LLM API, retrying in 5 seconds...')
                logging.warning(e)
                print(e)
                if retries == 1:
                    logging.error('Could not connect to LLM API after 5 retries, exiting...')
                    input('Press enter to continue...')
                    exit()
                time.sleep(5)
                retries -= 1
                continue
            break
        # if self.alternative_openai_api_base == 'none':
        #     await openai.aiosession.get().close()



def initialise(config_file, logging_file, secret_key_file, language_file):
    def setup_openai_secret_key(file_name):
        with open(file_name, 'r') as f:
            api_key = f.readline().strip()
        return api_key

    def setup_logging(file_name):
        logging.basicConfig(filename=file_name, format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        logging.getLogger('').addHandler(console)

    def get_language_info(file_name):
        language_df = pd.read_csv(file_name)
        try:
            language_info = language_df.loc[language_df['alpha2']==config.language].to_dict('records')[0]
            return language_info
        except:
            logging.error(f"Could not load language '{config.language}'. Please set a valid language in config.ini\n")

    def get_token_limit(config):
        if config.is_local:
            logging.info(f"Using local language model. Token limit set to {config.maximum_local_tokens} (this number can be changed via the `maximum_local_tokens` setting in config.ini)")
            try:
                token_limit = int(config.maximum_local_tokens)
            except ValueError:
                logging.error(f"Invalid maximum_local_tokens value: {config.maximum_local_tokens}. It should be a valid integer. Please update your configuration.")
                token_limit = 4096  # Default to 4096 in case of an error.
        else:
            llm = config.llm
            if '/' in llm:
                llm = llm.split('/')[-1]

            if llm == 'gpt-3.5-turbo':
                token_limit = 4096
            elif llm == 'gpt-3.5-turbo-16k':
                token_limit = 16384
            elif llm == 'gpt-4':
                token_limit = 8192
            elif llm == 'gpt-4-32k':
                token_limit = 32768
            elif llm == 'claude-2':
                token_limit = 100_000
            elif llm == 'claude-instant-v1':
                token_limit = 100_000
            elif llm == 'palm-2-chat-bison':
                token_limit = 8000
            elif llm == 'palm-2-codechat-bison':
                token_limit = 8000
            elif llm == 'llama-2-7b-chat':
                token_limit = 4096
            elif llm == 'llama-2-13b-chat':
                token_limit = 4096
            elif llm == 'llama-2-70b-chat':
                token_limit = 4096
            elif llm == 'codellama-34b-instruct':
                token_limit = 16000
            elif llm == 'nous-hermes-llama2-13b':
                token_limit = 4096
            elif llm == 'weaver':
                token_limit = 8000
            elif llm == 'mythomax-L2-13b':
                token_limit = 8192
            elif llm == 'airoboros-l2-70b-2.1':
                token_limit = 4096
            elif llm == 'gpt-3.5-turbo-1106':
                token_limit = 16_385
            elif llm == 'gpt-4-1106-preview':
                token_limit = 128_000
            else:
                logging.info(f"Could not find number of available tokens for {llm}. Defaulting to token count of {config.maximum_local_tokens} (this number can be changed via the `maximum_local_tokens` setting in config.ini)")

        if token_limit <= 4096:
            logging.info(f"{llm} has a low token count of {token_limit}. For better NPC memories, try changing to a model with a higher token count")
        return token_limit

    setup_logging(logging_file)
    config = config_loader.ConfigLoader(config_file)
    
    
    is_local = True
    if (config.alternative_openai_api_base == 'none'): # or (config.alternative_openai_api_base.startswith('https://openrouter.ai/api/v1')) -- this is a temporary fix for the openrouter api, as while it isn't local, it shouldnn't use the local tokenizer, so we're going to lie here TODO: Fix this. Should do more granularity than local or not, should just have a flag for when using openai or other models.
        is_local = False
    
    api_key = setup_openai_secret_key(secret_key_file)
    client = OpenAI(api_key=api_key)

    if config.alternative_openai_api_base != 'none':
        client.base_url  = config.alternative_openai_api_base
        logging.info(f"Using OpenAI API base: {client.base_url}")

    if is_local:
        logging.info(f"Running Mantella with local language model")
    else:
       logging.info(f"Running Mantella with '{config.llm}'. The language model chosen can be changed via config.ini")

    xvasynth = tts.Synthesizer(config)

    # clean up old instances of exe runtime files
    utils.cleanup_mei(config.remove_mei_folders)
    character_df = CharacterDB(config,xvasynth)
    try:
        if config.character_df_file.endswith('.csv'):
            character_df.load_characters_csv()
        else:
            character_df.load_characters_json()
        character_df.verify_characters()
    except:
        logging.error(f"Could not load character database from {config.character_df_file}. Please check the path and try again. Path should be a directory containing json files or a csv file containing character information.")
        raise
    language_info = get_language_info(language_file)
    
    config.is_local = is_local

    tokenizer = Tokenizer(config,client)
    token_limit = get_token_limit(config)
    
    llm = LLM(config, client, tokenizer, token_limit, language_info)



    return config, character_df, language_info, llm, tokenizer, token_limit, xvasynth