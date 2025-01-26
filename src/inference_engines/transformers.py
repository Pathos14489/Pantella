print("Importing transformers.py...")
from src.logging import logging, time
import src.utils as utils
import src.inference_engines.base_llm as base_LLM
import src.tokenizers.base_tokenizer as tokenizer
from threading import Thread
import traceback
logging.info("Imported required libraries in transformers.py")

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer, StoppingCriteria, StoppingCriteriaList
    loaded = True
    logging.info("Successfully imported transformers")
except Exception as e:
    loaded = False
    logging.warn("Failed to import transformers! Please check that you have installed it correctly, or if you don't plan to use it, ignore this warning.")

inference_engine_name = "transformers"

llm_model = None # Used to store the  transformer model so it can be reused for the tokenizer
llm_tokenizer = None 

class StoppingTextIteratorStoppingCriteria(StoppingCriteria):
    def __init__(self, stop_bool):
        self.stop_bool = stop_bool

    def __call__(self, input_ids, scores, **kwargs):
        return self.stop_bool

class StoppingTextIteratorStreamer(TextIteratorStreamer):
    def __init__(self, tokenizer, llm, stops=[], skip_prompt=False, timeout=None, **decode_kwargs):
        super().__init__(tokenizer, skip_prompt, timeout, **decode_kwargs)
        self.llm = llm
        self.stops = stops
        self.full_string = ""
        self.stop_bool = False

    def on_finalized_text(self, text: str, stream_end: bool = False):
        """Put the new text in the queue. If the stream is ending, also put a stop signal in the queue."""
        self.full_string += text
        formatted_text = text
        for stop in self.stops:
            formatted_text = formatted_text.split(stop)[0]
        self.text_queue.put(formatted_text, timeout=self.timeout)

        contains_stops = False
        # self.stops = self.stops
        for stop in self.stops:
            if stop in self.full_string:
                contains_stops = True
                break

        if contains_stops and not stream_end:
            stream_end = True
            self.stop_bool = True
        if stream_end:
            self.text_queue.put(self.stop_signal, timeout=self.timeout)

class LLM(base_LLM.base_LLM): # Uses llama-cpp-python as the LLM inference engine
    def __init__(self, conversation_manager, vision_enabled=False):
        global llm_model
        global llm_tokenizer
        global inference_engine_name
        super().__init__(conversation_manager, vision_enabled=vision_enabled)
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
            raise ValueError(f"Error loading transformers. Please check that you have installed it correctly.")
        self.generation_thread = None
        logging.info(f"Running Pantella with transformers. The language model chosen can be changed via config.json")
        logging.info(f"Testing transformers...")
        test_prompt = "Hello, I am a transformers test prompt. I am used to test transformers's functi"
        test_completion = self._generate(test_prompt, 10)
        logging.info(f"Test Completion: {test_completion}")
        logging.info(f"Starting transformers test stream...")
        test_stream = self._create_completion_stream([
            {"role": "user", "content": "Hello, what is your name?"},
            {"role": "assistant", "content": "My name is Pantella, an AI language model assistant designed to run Skyrim NPCs."},
            {"role": "user", "content": "Nice to meet you. What can you do?"}
        ])
        logging.info(f"Streaning now...")
        for token in test_stream:
            if token is not None and token != "":
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
        
        streamer = StoppingTextIteratorStreamer(self.tokenizer.tokenizer, self, stops=self.config.stop, skip_prompt=True)
        criteria = StoppingTextIteratorStoppingCriteria(streamer.stop_bool)
        criteria_list = StoppingCriteriaList()
        criteria_list.append(criteria)
        
        generation_kwargs = dict(inputs, streamer=streamer, stopping_criteria=criteria_list, **self.generation_kwargs)
        self.generation_thread = Thread(target=self.llm.generate, kwargs=generation_kwargs) # Run the generation in a separate thread, so that we can fetch the generated text in a non-blocking way.
        self.generation_thread.start()
        return streamer
    

    @utils.time_it
    def create(self, messages):
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                completion = self._create_completion(messages)
                logging.info(f"Completion:",completion)
            except Exception as e:
                logging.warning('Error generating completion, retrying in 5 seconds...')
                logging.warning(e)
                tb = traceback.format_exc()
                logging.error(tb)
                print(e)
                if retries == 1:
                    logging.error('Error generating completion after 5 retries, exiting...')
                    input('Press enter to continue...')
                    raise e
                time.sleep(5)
                retries -= 1
                continue
            break
        return completion
    
    def acreate(self, messages,  message_prefix="", force_speaker=None): # Creates a completion stream for the messages provided to generate a speaker and their response
        retries = 5
        while retries > 0:
            logging.info(f"Retries: {retries}")
            try:
                prompt = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message(self.config.assistant_name) # Start empty message from no one to let the LLM generate the speaker by split \n
                if force_speaker is not None:
                    prompt += force_speaker.name + self.config.message_signifier
                    prompt += message_prefix
                logging.info(f"Raw Prompt: {prompt}")
                logging.info(f"Type of prompt: {type(prompt)}")
                inputs = self.tokenizer.tokenizer(prompt, return_tensors="pt").to(self.device_map)
                
                streamer = StoppingTextIteratorStreamer(self.tokenizer.tokenizer, self, stops=self.config.stop, skip_prompt=True)
                criteria = StoppingTextIteratorStoppingCriteria(streamer.stop_bool)
                criteria_list = StoppingCriteriaList()
                criteria_list.append(criteria)
                
                generation_kwargs = dict(inputs, streamer=streamer, stopping_criteria=criteria_list, **self.generation_kwargs)
                self.generation_thread = Thread(target=self.llm.generate, kwargs=generation_kwargs) # Run the generation in a separate thread, so that we can fetch the generated text in a non-blocking way.
                self.generation_thread.start()
                return streamer
            except Exception as e:
                logging.warning('Error creating completion stream, retrying in 5 seconds...')
                logging.warning(e)
                tb = traceback.format_exc()
                logging.error(tb)
                print(e)
                if retries == 1:
                    logging.error('Error creating completion stream after 5 retries, exiting...')
                    input('Press enter to continue...')
                    raise e
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