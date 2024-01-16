import src.utils as utils
import src.llms.base_llm as base_LLM
import time
from openai import OpenAI
import logging

inference_engine_name = "openai"
tokenizer_slug = "tiktoken"

def setup_openai_secret_key(file_name):
    with open(file_name, 'r') as f:
        api_key = f.readline().strip()
    return api_key

class LLM(base_LLM.base_LLM):
    def __init__(self, config, token_limit, language_info):
        super().__init__(config, token_limit, language_info)
        self.inference_engine_name = inference_engine_name
        self.tokenizer_slug = tokenizer_slug # Fastest tokenizer for OpenAI models, change if you want to use a different tokenizer (use 'embedding' for compatibility with any model using the openai API)
        api_key = setup_openai_secret_key(self.config.secret_key_file_path)
        self.client = OpenAI(api_key=api_key)

        if config.alternative_openai_api_base != 'none':
            self.client.base_url  = config.alternative_openai_api_base
            logging.info(f"Using OpenAI API base: {self.client.base_url}")

        if config.is_local:
            logging.info(f"Running Mantella with local language model")
        else:
            logging.info(f"Running Mantella with '{config.llm}'. The language model chosen can be changed via config.ini")
    
    @utils.time_it
    def create(self, messages):
        # print(f"cMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                prompt = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message(self.config.assistant_name) # Start empty message from no one to let the LLM generate the speaker by split \n
                print(f"Raw Prompt: {prompt}")

                completion = self.client.completions.create(
                    model=self.config.llm, prompt=prompt, max_tokens=self.config.max_tokens
                )
                completion = completion.choices[0].text
                print(f"Completion:",completion)
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
        # print(f"aMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                prompt = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message("[name]") # Start empty message from no one to let the LLM generate the speaker by split \n
                prompt = prompt.split("[name]")[0] # Start message without the name - Generates name for use in output_manager.py  process_response()
                logging.info(f"Raw Prompt: {prompt}")
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