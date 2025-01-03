print("Importing openai_api.py")
from src.logging import logging, time
import src.utils as utils
from src.llms.base_llm import base_LLM, TestCoT, get_schema_description
import random
import traceback
import os
import json
logging.info("Imported required libraries in openai_api.py")

try:
    from openai import OpenAI
    loaded = True
    logging.info("Imported openai in openai_api.py")
except Exception as e:
    loaded = False
    logging.warn(f"Failed to load openai, so openai_api cannot be used! Please check that you have installed it correctly. Unless you're not using openai, in which case you can ignore this warning.")

inference_engine_name = "openai"

class LLM(base_LLM):
    def __init__(self, conversation_manager, vision_enabled=False):
        global inference_engine_name
        super().__init__(conversation_manager, vision_enabled=vision_enabled)
        self.inference_engine_name = inference_engine_name
        self.tokenizer_slug = "tiktoken" # Fastest tokenizer for OpenAI models, change if you want to use a different tokenizer (use 'embedding' for compatibility with any model using the openai API)
        
        llm = self.config.openai_model
        # Is LLM Local?
        self.is_local = True
        if self.config.alternative_openai_api_base == 'none' or self.config.alternative_openai_api_base == "https://openrouter.ai/api/v1" or self.config.alternative_openai_api_base == "http://openrouter.ai/api/v1" or self.config.alternative_openai_api_base == "https://api.openai.com" or self.config.alternative_openai_api_base == "https://api.totalgpt.ai/v1":
            self.is_local = False
        if self.is_local:
            logging.info(f"Could not find number of available tokens for {llm} for tiktoken. Defaulting to token count of {str(self.config.maximum_local_tokens)} (this number can be changed via the `maximum_local_tokens` setting in config.json).")
            logging.info("WARNING: Tiktoken is being run using the default tokenizer, which is not always correct. If you're using a local model, try using the embedding tokenizer instead if it's supported by your API emulation method. It's slower and might be incompatible with some configurations, but more accurate.")
            token_limit = self.config.maximum_local_tokens # Default to 4096 tokens for local models
        else:
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
                logging.warn(f"Could not find number of available tokens for {llm} for tiktoken. Defaulting to token count of 4096.")
                token_limit = 4096
            self.config.maximum_local_tokens = token_limit # Set the maximum number of tokens for local models to the number of tokens available for the model chosen    

        with open(self.config.openai_api_key_path, 'r') as f:
            api_key = f.readline().strip()
        self.api_key = api_key

        if loaded:
            self.client = OpenAI(api_key=api_key, base_url=self.config.alternative_openai_api_base)
        else:
            logging.error(f"Error loading openai. Please check that you have installed it correctly.")
            input("Press Enter to exit.")
            raise ValueError(f"Error loading openai. Please check that you have installed it correctly.")

        if self.config.alternative_openai_api_base != 'none':
            self.client.base_url  = self.config.alternative_openai_api_base
            logging.info(f"Using OpenAI-style API base: {self.client.base_url}")

        if self.is_local:
            logging.info(f"Running Pantella with local language model via openai python package")
        else:
            logging.info(f"Running Pantella with '{self.config.openai_model}'. The language model chosen can be changed via config.json")


        generation_model = self.config.openai_model
        if self.config.openai_character_generator_model is not None and self.config.openai_character_generator_model.strip() != "":
            generation_model = self.config.openai_character_generator_model

        dedicated_character_generation_model_selected = generation_model != self.config.openai_model # If the character generator model is different from the main model, we need to check if it's supported for completions

        if not self.vision_enabled:
            if self.openai_completions_type == "text":
                try:
                    if self.config.reverse_proxy:
                        self.client.completions.create(prompt="This is a test of the", model=self.config.openai_model, max_tokens=10, extra_body={"proxy_password":api_key})
                    else:
                        self.client.completions.create(prompt="This is a test of the", model=self.config.openai_model, max_tokens=10)
                    self.completions_supported = True
                    logging.success(f"OpenAI API at '{self.config.alternative_openai_api_base}' supports completions!")
                except Exception as e:
                    self.completions_supported = False
                    logging.error(f"Current API does not support text completions! Are you using OpenAI's API? They will not work with all features of Pantella, please use OpenRouter or another API that supports raw non-chat completions.")
                    logging.error(e)
                    # input("Press Enter to exit.")
            else:
                self.completions_supported = False
            try:
                if self.cot_enabled:
                    if self.openai_completions_type == "text" and self.completions_supported:
                        if self.config.reverse_proxy:
                            response = self.client.completions.create(prompt="", model=self.config.openai_model, max_tokens=50, extra_body={"proxy_password":api_key, "response_format": {"type": "json_schema", "json_schema": TestCoT.model_json_schema()}})
                        else:
                            response = self.client.completions.create(prompt="", model=self.config.openai_model, max_tokens=50, extra_body={"response_format": {"type": "json_schema", "json_schema": TestCoT.model_json_schema()}})
                    else:
                        if self.config.reverse_proxy:
                            response = self.client.chat.completions.create(messages=[{"role": "system", "content": "This is a test of the CoT system."}], model=self.config.openai_model, max_tokens=50, extra_body={"proxy_password":api_key, "response_format": {"type": "json_schema", "json_schema": TestCoT.model_json_schema()}})
                        else:
                            response = self.client.chat.completions.create(messages=[{"role": "system", "content": "This is a test of the CoT system."}], model=self.config.openai_model, max_tokens=50, extra_body={"response_format": {"type": "json_schema", "json_schema": TestCoT.model_json_schema()}})
                    print(response)
                    try:
                        try:
                            completion = response.choices[0].text
                        except:
                            pass
                        if completion is None or type(completion) != str:
                            try:
                                completion = response.choices[0]["text"]
                            except:
                                pass
                        if completion is None or type(completion) != str:
                            try:
                                completion = response.choices[0].message.content
                            except:
                                pass
                        if completion is None or type(completion) != str:
                            try:
                                completion = response.choices[0].message.content
                            except:
                                pass
                        if completion is None or type(completion) != str:
                            try:
                                completion = response.choices[0].delta.content
                            except:
                                pass
                        response = json.loads(completion.strip())
                        self.cot_supported = True
                        if not dedicated_character_generation_model_selected:
                            self.character_generation_supported = True
                        logging.success(f"OpenAI API at '{self.config.alternative_openai_api_base}' supports CoT!")
                    except:
                        self.cot_supported = False
                        logging.error(f"Current API does not support CoT! Are you using OpenAI's API? They will not work with all features of Pantella, please use OpenRouter or another API that supports CoT.")
                        # input("Press Enter to exit.")
                else:
                    self.cot_supported = False
                    logging.info("CoT is not enabled.")
            except Exception as e:
                self.cot_supported = False
                logging.error(f"Current API does not support CoT! Are you using OpenAI's API? They will not work with all features of Pantella, please use OpenRouter or another API that supports CoT.")
                logging.error(e)
                # input("Press Enter to exit.")
        else:
            logging.success("Vision is enabled -- Make sure the LLM you choose supports vision as well!")
            logging.warning("NOTICE: Completions API is not currently supported with vision enabled!")
            self.completions_supported = False
        if dedicated_character_generation_model_selected:
            logging.info(f"Testing if the dedicated character generation model '{generation_model}' supports completions...")
            try:
                if self.openai_completions_type == "text" and self.completions_supported:
                    if self.config.reverse_proxy:
                        self.client.completions.create(prompt="This is a test of the", model=generation_model, max_tokens=10, extra_body={"proxy_password":api_key})
                    else:
                        self.client.completions.create(prompt="This is a test of the", model=generation_model, max_tokens=10)
                    self.completions_supported = True
                    logging.success(f"OpenAI API at '{self.config.alternative_openai_api_base}' supports completions for the dedicated character generation model '{generation_model}'!")
                else:
                    self.completions_supported = False
                    logging.error(f"Current API does not support text completions for the dedicated character generation model '{generation_model}'! Are you using OpenAI's API? They will not work with all features of Pantella, please use OpenRouter or another API that supports raw non-chat completions.")
                    # input("Press Enter to exit.")
            except Exception as e:
                self.completions_supported = False
                logging.error(f"Current API does not support text completions for the dedicated character generation model '{generation_model}'! Are you using OpenAI's API? They will not work with all features of Pantella, please use OpenRouter or another API that supports raw non-chat completions.")
                logging.error(e)
                # input("Press Enter to exit.")
            try:
                if self.cot_enabled:
                    if self.openai_completions_type == "text" and self.completions_supported:
                        if self.config.reverse_proxy:
                            response = self.client.completions.create(prompt="", model=generation_model, max_tokens=50, extra_body={"proxy_password":api_key, "response_format": {"type": "json_schema", "json_schema": TestCoT.model_json_schema()}})
                        else:
                            response = self.client.completions.create(prompt="", model=generation_model, max_tokens=50, extra_body={"response_format": {"type": "json_schema", "json_schema": TestCoT.model_json_schema()}})
                    else:
                        if self.config.reverse_proxy:
                            response = self.client.chat.completions.create(messages=[{"role": "system", "content": "This is a test of the CoT system."}], model=generation_model, max_tokens=50, extra_body={"proxy_password":api_key, "response_format": {"type": "json_schema", "json_schema": TestCoT.model_json_schema()}})
                        else:
                            response = self.client.chat.completions.create(messages=[{"role": "system", "content": "This is a test of the CoT system."}], model=generation_model, max_tokens=50, extra_body={"response_format": {"type": "json_schema", "json_schema": TestCoT.model_json_schema()}})
                    print(response)
                    try:
                        try:
                            completion = response.choices[0].text
                        except:
                            pass
                        if completion is None or type(completion) != str:
                            try:
                                completion = response.choices[0]["text"]
                            except:
                                pass
                        if completion is None or type(completion) != str:
                            try:
                                completion = response.choices[0].message.content
                            except:
                                pass
                        if completion is None or type(completion) != str:
                            try:
                                completion = response.choices[0].message.content
                            except:
                                pass
                        if completion is None or type(completion) != str:
                            try:
                                completion = response.choices[0].delta.content
                            except:
                                pass
                        response = json.loads(completion.strip())
                        self.cot_supported = True
                        if dedicated_character_generation_model_selected:
                            self.character_generation_supported = True
                        logging.success(f"OpenAI API at '{self.config.alternative_openai_api_base}' supports CoT
                        for the dedicated character generation model '{generation_model}'!")
                    except:
                        self.cot_supported = False
                        logging.error(f"Current API does not support CoT for the dedicated character generation model '{generation_model}'! Are you using OpenAI's API? They will not work with all features of Pantella, please use OpenRouter or another API that supports CoT.")
                        # input("Press Enter to exit.")
                else:
                    self.cot_supported = False
                    logging.info("CoT is not enabled.")
            except Exception as e:
                self.cot_supported = False
                logging.error(f"Current API does not support CoT for the dedicated character generation model '{generation_model}'! Are you using OpenAI's API? They will not work with all features of Pantella, please use OpenRouter or another API that supports CoT.")
                logging.error(e)
                # input("Press Enter to exit.")

    def generate_character(self, character_name, character_ref_id, character_base_id, character_in_game_race, character_in_game_gender, character_is_guard, character_is_ghost, in_game_voice_model=None, is_generic_npc=False, location=None):
        """Generate a character based on the prompt provided"""
        if not self.character_generation_supported:
            logging.error(f"Character generation is not supported by llama-cpp-python. Please check that your model supports it and that it is enabled in config.json.")
            return None
        json_schema = self.conversation_manager.character_generator_schema.model_json_schema()
        openai_stop = list(self.stop)
        openai_stop = [self.config.message_separator] + openai_stop
        if self.config.alternative_openai_api_base == 'none': # OpenAI stop is the first 4 options in the stop list because they only support up to 4 for some asinine reason
            openai_stop = openai_stop[:4]
        else:
            openai_stop = openai_stop
        openai_stop = [stop for stop in openai_stop if stop != ""] # Remove empty strings from the stop list
        logging.info("Stop Strings:",openai_stop)
        sampler_kwargs = {
            "top_p": self.top_p,
            "temperature": self.temperature,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty
        }
        for kwarg in self.config.banned_samplers:
            if kwarg in sampler_kwargs:
                del sampler_kwargs[kwarg]
        extra_body_kwargs = {
            "min_p": self.min_p,
            "top_k":self.top_k,
            "typical_p":self.typical_p,
            "repeat_penalty":self.repeat_penalty,
            "mirostat_mode":self.mirostat_mode,
            "mirostat_tau":self.mirostat_tau,
            "mirostat_eta":self.mirostat_eta,
            "response_format": {
                "type": "json_schema",
                "json_schema": json_schema
            }
        }
        if self.config.reverse_proxy: # If using a reverse proxy, we need to include the password in the request
            extra_body_kwargs["proxy_password"] = self.api_key
        for kwarg in self.config.banned_samplers:
            if kwarg in extra_body_kwargs:
                del extra_body_kwargs[kwarg]

        character_prompt = self.conversation_manager.character_generator_schema.get_prompt(character_name, character_ref_id, character_base_id, character_in_game_race, character_in_game_gender, character_is_guard, character_is_ghost, location)

        messages = [
            {
                "role": "system",
                "content": "You are a character generator. You will be given a description of a character to generate. You will then generate a character that matches the description.\nHere are some related references to use when creating your character:",
            },
            {
                "role": "system",
                "content": get_schema_description(self.conversation_manager.character_generator_schema.model_json_schema())
            },
            {
                "role": "user",
                "content": character_prompt
            }
        ]

        generation_model = self.config.openai_model
        if self.config.openai_character_generator_model is not None and self.config.openai_character_generator_model.strip() != "":
            generation_model = self.config.openai_character_generator_model

        character = None
        tries = 5
        while character is None and tries > 0:
            try:
                if self.openai_completions_type == "text" and self.completions_supported:
                    prompt = self.tokenizer.get_string_from_messages(messages) + self.tokenizer.start_message(self.config.assistant_name)
                    completion = self.client.completions.create(prompt,
                        model=generation_model, 
                        max_tokens=self.config.max_tokens,
                        **sampler_kwargs,
                        extra_body=extra_body_kwargs,
                        stream=False,
                        logit_bias=self.logit_bias,
                    )
                    completion = completion.choices[0].text
                else:
                    completion = self.client.chat.completions.create(messages=messages,
                        model=generation_model, 
                        max_tokens=self.config.max_tokens,
                        **sampler_kwargs,
                        extra_body=extra_body_kwargs,
                        stream=False,
                        logit_bias=self.logit_bias,
                    )
                    completion = completion.choices[0].message.content.strip()
                print(completion)
                response = json.loads(completion)
                character = self.conversation_manager.character_generator_schema(**response)
                character.voice_model = self.conversation_manager.voice_model
            except Exception as e:
                logging.error(f"Error generating character",e)
                tries -= 1

        voice_model = in_game_voice_model
        if self.config.override_voice_model_with_simple_predictions and voice_model is None:
            # Predict the voice model - If these are available for a character, use them because they're probably more accurate. Though, they're not always available, and sometimes you might prefer to use the voice model from the character generator.
            simple_predictions = [
                "FemaleArgonian",
                "FemaleDarkElf",
                "FemaleKhajiit",
                "FemaleNord",
                "FemaleOrc",
                "MaleArgonian",
                "MaleDarkElf",
                "MaleKhajiit",
                "MaleNord",
                "MaleOrc",
            ]
            if character_in_game_gender+character_in_game_race in simple_predictions:
                voice_model = character_in_game_gender+character_in_game_race

        if voice_model is not None:
            character.voice_model = voice_model

        return character.get_chracter_info(character_ref_id, character_base_id, voice_model, is_generic_npc)

    @utils.time_it
    def create(self, messages):
        # logging.info(f"cMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                openai_stop = list(self.stop)
                openai_stop = [self.config.message_separator] + openai_stop
                if self.config.alternative_openai_api_base == 'none': # OpenAI stop is the first 4 options in the stop list because they only support up to 4 for some asinine reason
                    openai_stop = openai_stop[:4]
                else:
                    openai_stop = openai_stop
                openai_stop = [stop for stop in openai_stop if stop != ""] # Remove empty strings from the stop list
                logging.info("Stop Strings:",openai_stop)
                sampler_kwargs = {
                    "top_p": self.top_p,
                    "temperature": self.temperature,
                    "frequency_penalty": self.frequency_penalty,
                    "presence_penalty": self.presence_penalty
                }
                for kwarg in self.config.banned_samplers:
                    if kwarg in sampler_kwargs:
                        del sampler_kwargs[kwarg]
                extra_body_kwargs = {
                    "min_p": self.min_p,
                    "top_k":self.top_k,
                    "typical_p":self.typical_p,
                    "repeat_penalty":self.repeat_penalty,
                    "mirostat_mode":self.mirostat_mode,
                    "mirostat_tau":self.mirostat_tau,
                    "mirostat_eta":self.mirostat_eta
                }
                if self.cot_enabled and self.cot_supported and self.conversation_manager.thought_process is not None: # If COT is enabled, we need to use the JSON schema for the response format
                    extra_body_kwargs["response_format"] = {
                        "type": "json_schema",
                        "json_schema": self.conversation_manager.thought_process.model_json_schema()
                    }
                if self.config.reverse_proxy: # If using a reverse proxy, we need to include the password in the request
                    extra_body_kwargs["proxy_password"] = self.api_key
                for kwarg in self.config.banned_samplers:
                    if kwarg in extra_body_kwargs:
                        del extra_body_kwargs[kwarg]
                if self.openai_completions_type == "text" and self.completions_supported:
                    prompt = self.tokenizer.get_string_from_messages(messages) + self.tokenizer.start_message(self.config.assistant_name)
                    logging.info(f"Raw Prompt: {prompt}")
                    completion = self.client.completions.create(prompt=prompt,
                        model=self.config.openai_model, 
                        max_tokens=self.config.max_tokens,
                        **sampler_kwargs,
                        extra_body=extra_body_kwargs,
                        stream=False,
                        logit_bias=self.logit_bias,
                    )
                else:
                    completion = self.client.chat.completions.create(messages=messages,
                        model=self.config.openai_model, 
                        max_tokens=self.config.max_tokens,
                        **sampler_kwargs,
                        extra_body=extra_body_kwargs,
                        stream=False,
                        logit_bias=self.logit_bias,
                    )
                print(completion.choices[0].message)
                try:
                    completion = completion.choices[0].text
                except:
                    pass
                if completion is None or type(completion) != str:
                    try:
                        completion = completion.choices[0]["text"]
                    except:
                        pass
                if completion is None or type(completion) != str:
                    try:
                        completion = completion.choices[0].message.content
                    except:
                        pass
                if completion is None or type(completion) != str:
                    try:
                        completion = completion.choices[0].message.content
                    except:
                        pass
                if completion is None or type(completion) != str:
                    try:
                        completion = completion.choices[0].delta.content
                    except:
                        pass
                if completion is None or type(completion) != str:
                    logging.error(f"Could not get completion from OpenAI-style API. Please check your API key and internet connection.")
                    input("Press Enter to exit.")
                    raise ValueError(f"Could not get completion from OpenAI-style API. Please check your API key and internet connection.")
                    
                logging.info(f"Completion:"+str(completion))
            except Exception as e:
                logging.warning('Could not connect to LLM API, retrying in 5 seconds...')
                logging.warning(e)
                tb = traceback.format_exc()
                logging.error(tb)
                print(e)
                if retries == 1:
                    logging.error('Could not connect to LLM API after 5 retries, exiting...')
                    input('Press enter to continue...')
                    raise e
                time.sleep(5)
                retries -= 1
                continue
            break
        if type(completion) != str:
            logging.error(f"Could not get completion from OpenAI-style API. Please check your API key and internet connection.")
            input("Press Enter to exit.")
            raise ValueError(f"Could not get completion from OpenAI-style API. Please check your API key and internet connection.")
        return completion
    
    @utils.time_it
    def acreate(self, messages, message_prefix="", force_speaker=None): # Creates a completion stream for the messages provided to generate a speaker and their response
        # logging.info(f"aMessages: {messages}")
        retries = 5
        while retries > 0:
            try:
                openai_stop = list(self.stop)
                openai_stop = [self.message_separator,self.EOS_token,self.BOS_token] + openai_stop
                openai_stop = [stop for stop in openai_stop if stop != ""] # Remove empty strings from the stop list
                if self.config.alternative_openai_api_base == 'none': # OpenAI stop is the first 4 options in the stop list because they only support up to 4 for some asinine reason
                    openai_stop = openai_stop[:4]
                else:
                    openai_stop = openai_stop
                logging.info("Stop Strings:",openai_stop)
                sampler_kwargs = {
                    "top_p": self.top_p,
                    "temperature": self.temperature,
                    "frequency_penalty": self.frequency_penalty,
                    "presence_penalty": self.presence_penalty
                }
                for kwarg in self.config.banned_samplers:
                    if kwarg in sampler_kwargs:
                        del sampler_kwargs[kwarg]
                extra_body_kwargs = {
                    "min_p": self.min_p,
                    "top_k":self.top_k,
                    "typical_p":self.typical_p,
                    "repeat_penalty":self.repeat_penalty,
                    "mirostat_mode":self.mirostat_mode,
                    "mirostat_tau":self.mirostat_tau,
                    "mirostat_eta":self.mirostat_eta
                }
                if self.cot_enabled and self.cot_supported and self.conversation_manager.thought_process is not None: # If COT is enabled, we need to use the JSON schema for the response format
                    extra_body_kwargs["response_format"] = {
                        "type": "json_schema",
                        "json_schema": self.conversation_manager.thought_process.model_json_schema()
                    }
                if self.config.reverse_proxy:
                    extra_body_kwargs["proxy_password"] = self.api_key
                for kwarg in self.config.banned_samplers:
                    if kwarg in extra_body_kwargs:
                        del extra_body_kwargs[kwarg]
                if self.openai_completions_type == "text" and self.completions_supported:
                    prompt = self.tokenizer.get_string_from_messages(messages)
                    prompt += self.tokenizer.start_message(self.config.assistant_name)
                    symbol_insert = ""
                    if force_speaker is not None:
                        prompt += force_speaker.name + self.config.message_signifier
                        prompt += message_prefix
                    logging.info(f"Raw Prompt: {prompt}")
                    if symbol_insert != "":
                        logging.info(f"Symbol Inserted: {symbol_insert}")
                    if self.config.log_all_api_requests:
                        log_id = None
                        while log_id is None or os.path.exists(self.config.api_log_dir+"/"+log_id+".log"):
                            log_id = str(random.randint(100000,999999))
                        # make sure the dir exists
                        os.makedirs(self.config.api_log_dir, exist_ok=True)
                        with open(self.config.api_log_dir+"/"+log_id+".log", "w") as f:
                            f.write(prompt)
                    
                    return self.client.completions.create(prompt=prompt,
                        model=self.config.openai_model, 
                        max_tokens=self.config.max_tokens,
                        **sampler_kwargs,
                        extra_body=extra_body_kwargs,
                        stream=True,
                        logit_bias=self.logit_bias,
                    )
                else:
                    if self.openai_completions_type == "text":
                        logging.warning("Using chat completions because raw completions are not supported by the current API/settings.")
                    if self.config.log_all_api_requests:
                        log_id = None
                        while log_id is None or os.path.exists(self.config.api_log_dir+"/"+log_id+".log"):
                            log_id = str(random.randint(100000,999999))
                        os.makedirs(self.config.api_log_dir, exist_ok=True)
                        with open(self.config.api_log_dir+"/"+log_id+".json", "w") as f:
                            request_json = {
                                "messages": messages,
                                "model": self.config.openai_model,
                                "max_tokens": self.config.max_tokens,
                                **sampler_kwargs,
                                **extra_body_kwargs,
                                "stream": True,
                                "logit_bias": self.logit_bias
                            }
                            json_string = json.dumps(request_json)
                            f.write(json_string)
                    return self.client.chat.completions.create(messages=messages,
                        model=self.config.openai_model, 
                        max_tokens=self.config.max_tokens,
                        **sampler_kwargs,
                        extra_body=extra_body_kwargs,
                        stream=True,
                        logit_bias=self.logit_bias,
                    )
            except Exception as e:
                logging.warning('Could not connect to LLM API, retrying in 5 seconds...')
                logging.warning(e)
                tb = traceback.format_exc()
                logging.error(tb)
                print(e)
                if retries == 1:
                    logging.error('Could not connect to LLM API after 5 retries, exiting...')
                    input('Press enter to continue...')
                    raise e
                time.sleep(5)
                retries -= 1
                continue