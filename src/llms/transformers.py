import src.utils as utils
import src.llms.base_llm as base_LLM
import src.tokenizers.base_tokenizer as tokenizer
import time
import logging
from threading import Thread

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
    loaded = True
except Exception as e:
    loaded = False

inference_engine_name = "transformers"

llm_model = None # Used to store the  transformer model so it can be reused for the tokenizer
llm_tokenizer = None 

class LLM(base_LLM.base_LLM): # Uses llama-cpp-python as the LLM inference engine
    def __init__(self, conversation_manager):
        global llm_model
        global llm_tokenizer
        global inference_engine_name
        super().__init__(conversation_manager)
        self.inference_engine_name = inference_engine_name
        if loaded:
            if llm_model is None:
                self.llm = AutoModelForCausalLM.from_pretrained(self.transformers_model_slug,
                    device_map=self.device_map,
                    trust_remote_code=self.trust_remote_code,
                    load_in_8bit=self.load_in_8bit,
                    torch_dtype="auto",
                ).eval()
                llm_model = self.llm
            else:
                self.llm = llm_model
            if llm_tokenizer is None:
                self.tokenizer = Tokenizer(self.conversation_manager)
            else:
                self.tokenizer = llm_tokenizer
        else:
            logging.error(f"Error loading transformers. Please check that you have installed it correctly.")
            input("Press Enter to exit.")
            exit()
        logging.info(f"Running Mantella with transformers. The language model chosen can be changed via config.json")
        logging.info(f"Testing transformers...")
        test_prompt = "Hello, I am a transformers test prompt. I am used to test transformers's functi"
        test_completion = self._generate(test_prompt, 10)
        logging.info(f"Test Completion: {test_completion}")
        logging.info(f"Starting transformers test stream...")
        test_stream = self._create_completion_stream([
            {"role": "user", "content": "Hello, what is your name?"},
            {"role": "assistant", "content": "My name is Mantella, an AI language model assistant designed to run Skyrim NPCs."},
            {"role": "user", "content": "Nice to meet you. What can you do?"}
        ])
        logging.info(f"Streaning now...")
        for token in test_stream:
            print({
                "token": token,
            })
        logging.info(f"Stream complete.")

    
    def _generate(self, string, max_length):
        max_length = max_length if max_length is not None else self.max_tokens
        inputs = self.tokenizer.tokenizer(string, return_tensors="pt").to(self.device_map)
        outputs = self.llm.generate(**inputs,
                max_new_tokens=max_length,
                temperature=self.temperature,
                top_k=self.top_k,
                top_p=self.top_p,
                typical_p=self.typical_p,
                repetition_penalty=self.repeat_penalty,
                
                do_sample=True,
            )
        return self.tokenizer.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def _create_completion(self, messages):
        """Return complete completion from the LLM"""
        prompt = self.tokenizer.get_string_from_messages(messages)
        prompt += self.tokenizer.start_message(self.config.assistant_name) # Start empty message from no one to let the LLM generate the speaker by split \n
        logging.info(f"Raw Prompt: {prompt}")
        inputs = self.tokenizer.tokenizer(prompt, return_tensors="pt").to(self.device_map)
        return self.llm.generate(**inputs, **self.generation_kwargs)
    
    @property
    def generation_kwargs(self):
        return {
            "max_new_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "repetition_penalty": self.repeat_penalty,
            "do_sample": True,
        }

    def _create_completion_stream(self, messages):
        """Return a completion stream from the LLM"""
        prompt = self.tokenizer.get_string_from_messages(messages)
        prompt += self.tokenizer.start_message(self.config.assistant_name) # Start empty message from no one to let the LLM generate the speaker by split \n
        logging.info(f"Raw Prompt: {prompt}")
        logging.info(f"Type of prompt: {type(prompt)}")
        inputs = self.tokenizer.tokenizer(prompt, return_tensors="pt").to(self.device_map)
        streamer = TextIteratorStreamer(self.tokenizer.tokenizer)
        # Combine self.generation_kwargs and streamer
        generation_kwargs = dict(inputs, streamer=streamer, **self.generation_kwargs)
        generation_kwargs["streamer"] = streamer
        thread = Thread(target=self.llm.generate, kwargs=generation_kwargs)
        thread.start()
        return streamer
    

    @utils.time_it
    def create(self, messages):
        # logging.info(f"cMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                completion = self._create_completion(messages)
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
                return self._create_completion_stream(messages)
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
    def __init__(self, conversation_manager):
        global llm_tokenizer
        super().__init__(conversation_manager)
        if llm_tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.transformers_model_slug,
                trust_remote_code=self.config.trust_remote_code,
            )
            llm_tokenizer = self
        else:
            self.tokenizer = llm_tokenizer.tokenizer
            
    @utils.time_it
    def get_token_count(self, string):
        # logging.info(f"Tokenizer.get_token_count() called with string: {string}")
        tokens = self.tokenizer.encode(string, return_tensors="pt")
        return tokens.shape[1] # Return the number of tokens in the string