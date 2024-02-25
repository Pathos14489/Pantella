import src.utils as utils
import src.llms.base_llm as base_LLM
from src.logging import logging, time

try:
    from openai import OpenAI
    loaded = True
except Exception as e:
    loaded = False

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
        self.config.maximum_local_tokens = token_limit # Set the maximum number of tokens for local models to the number of tokens available for the model chosen    

        api_key = setup_openai_secret_key(self.config.secret_key_file_path)
        if loaded:
            self.client = OpenAI(api_key=api_key)
        else:
            logging.error(f"Error loading openai. Please check that you have installed it correctly.")
            input("Press Enter to exit.")
            exit()

        if self.config.alternative_openai_api_base != 'none':
            self.client.base_url  = self.config.alternative_openai_api_base
            logging.info(f"Using OpenAI API base: {self.client.base_url}")

        if self.is_local:
            logging.info(f"Running Mantella with local language model")
        else:
            logging.info(f"Running Mantella with '{self.config.llm}'. The language model chosen can be changed via config.json")
    
    @utils.time_it
    def create(self, messages):
        # logging.info(f"cMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                prompt = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message(self.config.assistant_name) # Start empty message from no one to let the LLM generate the speaker by split \n
                logging.info(f"Raw Prompt: {prompt}")

                openai_stop = self.stop[:4] # OpenAI stop is the first 4 options in the stop list
                completion = self.client.completions.create(prompt=prompt,
                    model=self.config.llm, 
                    max_tokens=self.config.max_tokens,
                    top_p=self.top_p, 
                    temperature=self.temperature,
                    frequency_penalty=self.frequency_penalty,
                    stop=openai_stop,
                    presence_penalty=self.presence_penalty,
                    stream=False,
                )
                completion = completion.choices[0].text
                logging.info(f"Completion:"+str(completion))
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
    
    @utils.time_it
    def acreate(self, messages): # Creates a completion stream for the messages provided to generate a speaker and their response
        # logging.info(f"aMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                prompt = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message("[name]") # Start empty message from no one to let the LLM generate the speaker by split \n
                prompt = prompt.split("[name]")[0] # Start message without the name - Generates name for use in output_manager.py  process_response()
                logging.info(f"Raw Prompt: {prompt}")
                openai_stop = self.stop[:4] # OpenAI stop is the first 4 options in the stop list
                return self.client.completions.create(prompt=prompt,
                    model=self.config.llm, 
                    max_tokens=self.config.max_tokens,
                    top_p=self.top_p, 
                    temperature=self.temperature,
                    frequency_penalty=self.frequency_penalty,
                    stop=openai_stop,
                    presence_penalty=self.presence_penalty,
                    stream=True,
                )
            except Exception as e:
                logging.warning('Could not connect to LLM API, retrying in 5 seconds...')
                logging.warning(e)
                logging.info(e)
                if retries == 1:
                    logging.error('Could not connect to LLM API after 5 retries, exiting...')
                    input('Press enter to continue...')
                    exit()
                time.sleep(5)
                retries -= 1
                continue