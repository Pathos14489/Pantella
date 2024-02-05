import src.utils as utils
import src.llms.base_llm as base_LLM
import src.tokenizers.base_tokenizer as tokenizer
import time
import logging

try:
    from llama_cpp import Llama
    loaded = True
except Exception as e:
    loaded = False

inference_engine_name = "llama-cpp-python"

llama_model = None # Used to store the llama-cpp-python model so it can be reused for the tokenizer

class LLM(base_LLM.base_LLM): # Uses llama-cpp-python as the LLM inference engine
    def __init__(self, conversation_manager):
        global llama_model
        global inference_engine_name
        super().__init__(conversation_manager)
        self.inference_engine_name = inference_engine_name
        if loaded:
            if llama_model is None:
                self.llm = Llama(
                    model_path=self.config.model_path,
                    n_ctx=self.config.maximum_local_tokens,
                    n_gpu_layers=self.config.n_gpu_layers,
                    n_batch=self.config.n_batch,
                    n_threads=self.config.n_threads,
                    offload_kqv=True,
                    tensor_split=self.config.tensor_split,
                    main_gpu=self.config.main_gpu,
                )
            else:
                self.llm = llama_model
        else:
            logging.error(f"Error loading llama-cpp-python. Please check that you have installed it correctly.")
            input("Press Enter to exit.")
            exit()
        llama_model = self.llm
        logging.info(f"Running Mantella with llama-cpp-python. The language model chosen can be changed via config.json")
        logging.info(f"Testing llama-cpp-python...")
        test_prompt = "Hello, I am a llama-cpp-python test prompt. I am used to test llama-cpp-python's functi"
        test_completion = self.llm.create_completion(test_prompt, max_tokens=10)
        logging.info(f"Test Completion: {test_completion}")

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

                completion = self.llm.create_completion(prompt,
                    max_tokens=self.max_tokens,
                    top_k=self.top_k,
                    top_p=self.top_p,
                    min_p=self.min_p,
                    temperature=self.temperature,
                    repeat_penalty=self.repeat_penalty, 
                    stop=self.stop,
                    frequency_penalty=self.frequency_penalty,
                    presence_penalty=self.presence_penalty,
                    stream=False
                )
                completion = completion["choices"][0]["text"]
                logging.info(f"Completion:",completion)
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
    
    def acreate(self, messages): # Creates a completion stream for the messages provided to generate a speaker and their response
        logging.info(f"aMessages: {messages}")
        retries = 5
        while retries > 0:
            logging.info(f"Retries: {retries}")
            try:
                prompt = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message("[name]") # Start empty message from no one to let the LLM generate the speaker by split \n
                prompt = prompt.split("[name]")[0] # Start message without the name - Generates name for use in process_response()
                logging.info(f"Raw Prompt: {prompt}")
                logging.info(f"Type of prompt: {type(prompt)}")
                return self.llm.create_completion(prompt=prompt,
                    max_tokens=self.max_tokens,
                    top_k=self.top_k,
                    top_p=self.top_p,
                    min_p=self.min_p,
                    temperature=self.temperature,
                    repeat_penalty=self.repeat_penalty, 
                    stop=self.stop,
                    frequency_penalty=self.frequency_penalty,
                    presence_penalty=self.presence_penalty,
                    typical_p=self.typical_p,
                    mirostat_mode=self.mirostat_mode,
                    mirostat_eta=self.mirostat_eta,
                    mirostat_tau=self.mirostat_tau,
                    stream=True,
                )
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
        # logging.info(f"Tokenizer.get_token_count() called with string: {string}")
        tokens = self.llm.tokenize(f"{string}".encode("utf-8"))
        return len(tokens)