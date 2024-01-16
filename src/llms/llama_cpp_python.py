import src.utils as utils
import src.llms.base_llm as base_LLM
import src.tokenizers.base_tokenizer as tokenizer
import time
from llama_cpp import Llama
import logging

inference_engine_name = "llama-cpp-python"

llama_model = None # Used to store the llama-cpp-python model so it can be reused for the tokenizer

class LLM(base_LLM.base_LLM): # Uses llama-cpp-python as the LLM inference engine
    def __init__(self, config, token_limit, language_info):
        global llama_model
        super().__init__(config, token_limit, language_info)
        self.inference_engine_name = inference_engine_name
        config.is_local = True
        if llama_model is None:
            self.llm = Llama(
                model_path=self.config.model_path,
                n_ctx=self.config.maximum_local_tokens,
                n_gpu_layers=self.config.n_gpu_layers,
                n_batch=self.config.n_batch,
                n_threads=self.config.n_threads,
                tensor_split=self.config.tensor_split,
                main_gpu=self.config.main_gpu
            )
        else:
            self.llm = llama_model
        llama_model = self.llm
        logging.info(f"Running Mantella with llama-cpp-python. The language model chosen can be changed via config.ini")

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

                completion = self.llm.create_completion(prompt, max_tokens=self.config.max_tokens, top_k=self.config.top_k, top_p=self.config.top_p, temperature=self.config.temperature, repeat_penalty=self.config.repeat_penalty)
                completion = completion.choices[0].text
                print(f"Completion:",completion)
            except Exception as e:
                logging.warning('Error generating completion, retrying in 5 seconds...')
                logging.warning(e)
                print(e)
                if retries == 1:
                    logging.error('Error generating completion after 5 retries, exiting...')
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
                return self.llm.create_completion(prompt, max_tokens=self.config.max_tokens, top_k=self.config.top_k, top_p=self.config.top_p, temperature=self.config.temperature, repeat_penalty=self.config.repeat_penalty, stream=True)
            except Exception as e:
                logging.warning('Error creating completion stream, retrying in 5 seconds...')
                logging.warning(e)
                print(e)
                if retries == 1:
                    logging.error('Error creating completion stream after 5 retries, exiting...')
                    input('Press enter to continue...')
                    exit()
                time.sleep(5)
                retries -= 1
                continue

class Tokenizer(tokenizer.base_Tokenizer): # Uses llama-cpp-python's tokenizer
    def __init__(self, config):
        global llama_model
        super().__init__(config)
        if llama_model is None:
            self.llm = Llama(model_path=config.model_path)
        else:
            self.llm = llama_model
            
    @utils.time_it
    def get_token_count(self, string):
        logging.info(f"Tokenizer.get_token_count() called with string: {string}")
        tokens = self.llm.tokenize(string)
        return len(tokens)