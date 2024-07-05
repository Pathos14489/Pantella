print("Importing openai_api.py")
from src.logging import logging, time
import src.utils as utils
import src.llms.base_llm as base_LLM
import random
logging.info("Imported required libraries in openai_api.py")

try:
    from openai import OpenAI
    loaded = True
    logging.info("Imported openai in openai_api.py")
except Exception as e:
    loaded = False
    logging.warn(f"Failed to load openai, so openai_api cannot be used! Please check that you have installed it correctly. Unless you're not using openai, in which case you can ignore this warning.")

inference_engine_name = "openai"

def setup_openai_secret_key(file_name):
    with open(file_name, 'r') as f:
        api_key = f.readline().strip()
    return api_key

class LLM(base_LLM.base_LLM):
    def __init__(self, conversation_manager):
        global inference_engine_name
        global tokenizer_slug
        super().__init__(conversation_manager)
        self.inference_engine_name = inference_engine_name
        self.tokenizer_slug = "tiktoken" # Fastest tokenizer for OpenAI models, change if you want to use a different tokenizer (use 'embedding' for compatibility with any model using the openai API)
        
        # Is LLM Local?
        self.is_local = True
        if self.config.alternative_openai_api_base == 'none' or self.config.alternative_openai_api_base == "https://openrouter.ai/api/v1" or self.config.alternative_openai_api_base == "http://openrouter.ai/api/v1":
            self.is_local = False

        llm = self.config.llm
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
        elif self.is_local:
            logging.info(f"Could not find number of available tokens for {llm} for tiktoken. Defaulting to token count of {str(self.config.maximum_local_tokens)} (this number can be changed via the `maximum_local_tokens` setting in config.json).")
            logging.info("WARNING: Tiktoken is being run using the default tokenizer, which is not always correct. If you're using a local model, try using the embedding tokenizer instead if it's supported by your API emulation method. It's slower and might be incompatible with some configurations, but more accurate.")
            token_limit = self.config.maximum_local_tokens # Default to 4096 tokens for local models
        else:
            logging.warn(f"Could not find number of available tokens for {llm} for tiktoken. Defaulting to token count of 4096.")
            token_limit = 4096
        self.config.maximum_local_tokens = token_limit # Set the maximum number of tokens for local models to the number of tokens available for the model chosen    

        api_key = setup_openai_secret_key(self.config.secret_key_file_path)
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
            logging.info(f"Running Pantella with '{self.config.llm}'. The language model chosen can be changed via config.json")

        try:
            self.client.completions.create(prompt="This is a test of the", model=self.config.llm, max_tokens=10)
            self.completions_supported = True
            logging.info(f"OpenAI API at '{self.config.alternative_openai_api_base}' supports completions!")
        except Exception as e:
            self.completions_supported = False
            logging.error(f"Current API does not support raw completions! Are you using OpenAI's API? They will not work with all features of Pantella, please use OpenRouter or another API that supports raw non-chat completions.")
    
    def get_context(self):
        context = super().get_context()
        new_context = []
        for message in context:
            new_content = message["content"]
            if "name" in message:
                new_content = message["name"] +": "+ new_content
            new_context.append({
                "role": message["role"],
                "content": new_content
            })
        return new_context
    
    @utils.time_it
    def create(self, messages):
        # logging.info(f"cMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                openai_stop = list(self.stop)
                openai_stop = [self.config.message_seperator] + openai_stop
                if self.config.alternative_openai_api_base == 'none': # OpenAI stop is the first 4 options in the stop list because they only support up to 4 for some asinine reason
                    openai_stop = openai_stop[:4]
                else:
                    openai_stop = openai_stop
                openai_stop = [stop for stop in openai_stop if stop != ""] # Remove empty strings from the stop list
                logging.info("Stop Strings:",openai_stop)
                if self.completions_supported:
                    prompt = self.tokenizer.get_string_from_messages(messages) + self.tokenizer.start_message(self.config.assistant_name)
                    logging.info(f"Raw Prompt: {prompt}")
                    completion = self.client.completions.create(prompt=prompt,
                        model=self.config.llm, 
                        max_tokens=self.config.max_tokens,
                        top_p=self.top_p, 
                        temperature=self.temperature,
                        frequency_penalty=self.frequency_penalty,
                        stop=openai_stop,
                        presence_penalty=self.presence_penalty,
                        extra_body={ # Extra body is used to pass additional parameters to the API
                            "min_p": self.min_p,
                            "top_k":self.top_k,
                            "typical_p":self.typical_p,
                            "repeat_penalty":self.repeat_penalty,
                            "mirostat_mode":self.mirostat_mode,
                            "mirostat_tau":self.mirostat_tau,
                            "mirostat_eta":self.mirostat_eta
                        },
                        stream=False,
                    )
                else:
                    completion = self.client.chat.completions.create(messages=messages,
                        model=self.config.llm, 
                        max_tokens=self.config.max_tokens,
                        top_p=self.top_p, 
                        temperature=self.temperature,
                        frequency_penalty=self.frequency_penalty,
                        stop=openai_stop,
                        presence_penalty=self.presence_penalty,
                        extra_body={
                            "min_p": self.min_p,
                            "top_k":self.top_k,
                            "typical_p":self.typical_p,
                            "repeat_penalty":self.repeat_penalty,
                            "mirostat_mode":self.mirostat_mode,
                            "mirostat_tau":self.mirostat_tau,
                            "mirostat_eta":self.mirostat_eta
                        },
                        stream=False,
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
                openai_stop = [self.config.message_seperator,self.config.message_signifier,self.config.EOS_token,self.config.BOS_token] + openai_stop
                if self.config.alternative_openai_api_base == 'none': # OpenAI stop is the first 4 options in the stop list because they only support up to 4 for some asinine reason
                    openai_stop = openai_stop[:4]
                else:
                    openai_stop = openai_stop
                openai_stop = [stop for stop in openai_stop if stop != ""] # Remove empty strings from the stop list
                logging.info("Stop Strings:",openai_stop)
                if self.completions_supported:
                    prompt = self.tokenizer.get_string_from_messages(messages)
                    prompt += self.tokenizer.start_message(self.config.assistant_name)
                    symbol_insert = ""
                    if force_speaker is not None:
                        prompt += force_speaker.name + self.config.message_signifier
                        prompt += message_prefix
                    logging.info(f"Raw Prompt: {prompt}")
                    if symbol_insert != "":
                        logging.info(f"Symbol Inserted: {symbol_insert}")
                    return self.client.completions.create(prompt=prompt,
                        model=self.config.llm, 
                        max_tokens=self.config.max_tokens,
                        top_p=self.top_p, 
                        temperature=self.temperature,
                        frequency_penalty=self.frequency_penalty,
                        stop=openai_stop,
                        presence_penalty=self.presence_penalty,
                        extra_body={ # Extra body is used to pass additional parameters to the API
                            "min_p": self.min_p,
                            "top_k":self.top_k,
                            "typical_p":self.typical_p,
                            "repeat_penalty":self.repeat_penalty,
                            "mirostat_mode":self.mirostat_mode,
                            "mirostat_tau":self.mirostat_tau,
                            "mirostat_eta":self.mirostat_eta
                        },
                        stream=True,
                    )
                else:
                    return self.client.chat.completions.create(messages=messages,
                        model=self.config.llm, 
                        max_tokens=self.config.max_tokens,
                        top_p=self.top_p, 
                        temperature=self.temperature,
                        frequency_penalty=self.frequency_penalty,
                        stop=openai_stop,
                        presence_penalty=self.presence_penalty,
                        extra_body={
                            "min_p": self.min_p,
                            "top_k":self.top_k,
                            "typical_p":self.typical_p,
                            "repeat_penalty":self.repeat_penalty,
                            "mirostat_mode":self.mirostat_mode,
                            "mirostat_tau":self.mirostat_tau,
                            "mirostat_eta":self.mirostat_eta
                        },
                        stream=True,
                    )
            except Exception as e:
                logging.warning('Could not connect to LLM API, retrying in 5 seconds...')
                logging.warning(e)
                logging.info(e)
                if retries == 1:
                    logging.error('Could not connect to LLM API after 5 retries, exiting...')
                    input('Press enter to continue...')
                    raise e
                time.sleep(5)
                retries -= 1
                continue