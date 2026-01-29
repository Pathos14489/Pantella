print("Importing anthropic.py")
from src.logging import logging, time
import src.utils as utils
import src.inference_engines.base_llm as base_LLM
import random
import traceback
import os
import json
logging.info("Imported required libraries in anthropic.py")

imported = False
try:
    import anthropic
    imported = True
    logging.info("Imported anthropic in anthropic.py")
    raise DeprecationWarning("Anthropic API is deprecated and will be removed in a future version of Pantella. Please use a different inference engine.")
except Exception as e:
    logging.warn(f"Failed to load anthropic, so anthropic cannot be used! Please check that you have installed it correctly. Unless you're not using anthropic, in which case you can ignore this warning.")

inference_engine_name = "anthropic_api"
tokenizer_slug = "tiktoken" # TODO: Replace with the anthropic tokenizer for better token accuracy. Not important because this inference engine is effectively useless for Pantella, but I'm a completionist.
default_settings = {
    "anthropic_model": "claude-opus-4-20250514",
    "alternative_anthropic_api_base": "none",
    "anthropic_api_key_path": ".\\ANTHROPIC_SECRET_KEY.txt",
}
settings_description = {
    "anthropic_model": "The model to use for the Anthropic API. This can be any model that is supported by the Anthropic API, such as claude-2, claude-3, or claude-opus-4.",
    "alternative_anthropic_api_base": "The base URL for the Anthropic API. If you are using a reverse proxy, you can set this to the URL of your reverse proxy. If you are not using a reverse proxy, leave this as 'none'.",
    "anthropic_api_key_path": "The path to the file containing your Anthropic API key. This file should contain only the API key, with no extra whitespace or newlines.",
}
options = {}
settings = {}
loaded = False
description = "Anthropic API Inference Engine for Pantella. This inference engine uses the Anthropic API to generate text completions. It is not recommended to use this inference engine, as it does not support text completions and multiple system messages cannot be sent interspersed in the context. It is only included for compatibility with existing code that uses the Anthropic API."
class LLM(base_LLM.base_LLM):
    """Anthropic API Inference Engine for Pantella. This inference engine uses the Anthropic API to generate text completions.
It is not recommended to use this inference engine, as it does not support text completions and multiple system messages cannot be sent interspersed in the context.
It is only included as a proof of concept for adding new inference engines to Pantella and for the few people who might want to use it."""
    def __init__(self, conversation_manager, vision_enabled=False):
        global inference_engine_name, tokenizer_slug, loaded, default_settings
        super().__init__(conversation_manager, vision_enabled=vision_enabled)
        self.inference_engine_name = inference_engine_name
        self.tokenizer_slug = tokenizer_slug # Fastest tokenizer available. If we're guessing the token counts, might as well be fast while we're dumb!
        default_settings = self.default_inference_engine_settings
        self.llm = self.config.anthropic_model
        # Is LLM Local?
        self.is_local = False
        self.config.maximum_local_tokens = 200000 # Override to the maximum number of tokens that can be processed by anthropic

        with open(self.config.anthropic_api_key_path, 'r') as f:
            self.api_key = f.readline().strip()

        if imported:
            if self.config.alternative_anthropic_api_base.lower() != 'none' and self.config.alternative_anthropic_api_base != '':
                self.client = anthropic.Anthropic(
                    api_key=self.api_key,
                    base_url=self.config.alternative_anthropic_api_base,
                )
                logging.info(f"Using Anthropic-style API base: {self.config.alternative_anthropic_api_base}")
            else:
                self.client = anthropic.Anthropic(
                    api_key=self.api_key,
                )
        else:
            logging.error(f"Error loading anthropic. Please check that you have installed it correctly.")
            input("Press Enter to exit.")
            raise ValueError(f"Error loading anthropic. Please check that you have installed it correctly.")
        

        extra_body_kwargs = {}
        if self.config.reverse_proxy:
            extra_body_kwargs["proxy_password"] = self.api_key
        test = self.client.messages.create(
            messages=[{"role":"user","content":"Hello, how are you?"}],
            model=self.config.anthropic_model,
            max_tokens=10,
            extra_body=extra_body_kwargs,
            extra_headers={
                "anthropic-version": "2023-06-01",
            }
        )
        logging.info(f"Anthropic Test Response: {test.content}")

        logging.info(f"Running Pantella with '{self.config.anthropic_model}'. The language model chosen can be changed via config.json")
        logging.error(f"Current API does not support text completions! Anthropic API is not recommended, don't use it, use literally anything else PLEASE!")
        loaded = True

    @property
    def default_inference_engine_settings(self):
        return {
            "anthropic_model": self.config.anthropic_model,
            "alternative_anthropic_api_base": self.config.alternative_anthropic_api_base,
            "anthropic_api_key_path": self.config.anthropic_api_key_path,
        }
    
    @utils.time_it
    def create(self, messages):
        # logging.info(f"cMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                anthropic_stop = list(self.stop)
                anthropic_stop = [self.message_separator,self.EOS_token,self.BOS_token] + anthropic_stop
                anthropic_stop = [stop for stop in anthropic_stop if stop != ""] # Remove empty strings from the stop list
                logging.info("Stop Strings:",anthropic_stop)
                sampler_kwargs = {
                    "top_p": self.top_p,
                    "top_k":self.top_k,
                    "temperature": self.temperature,
                    "stop_sequences": anthropic_stop
                }
                for kwarg in self.config.banned_samplers:
                    if kwarg in sampler_kwargs:
                        del sampler_kwargs[kwarg]
                extra_body_kwargs = {}
                for kwarg in self.config.banned_samplers:
                    if kwarg in extra_body_kwargs:
                        del extra_body_kwargs[kwarg]
                if self.config.reverse_proxy:
                    extra_body_kwargs["proxy_password"] = self.api_key
                logging.warning("Using chat completions because true text completions are not supported by Anthropic. Expect performance to be degraded compared to using any provider that supports true text completions.")
                logging.info(f"Messages: {messages}")
                if self.config.log_all_api_requests:
                    log_id = None
                    while log_id is None or os.path.exists(self.config.api_log_dir+"/"+log_id+".log"):
                        log_id = str(random.randint(100000,999999))
                    os.makedirs(self.config.api_log_dir, exist_ok=True)
                    with open(self.config.api_log_dir+"/"+log_id+".json", "w") as f:
                        request_json = {
                            "messages": messages,
                            "model": self.config.anthropic_model,
                            "max_tokens": self.config.max_tokens,
                            **sampler_kwargs,
                            **extra_body_kwargs,
                        }
                        json_string = json.dumps(request_json)
                        f.write(json_string)
                completion = self.client.messages.create(messages=messages,
                    model=self.config.anthropic_model, 
                    max_tokens=self.config.max_tokens,
                    **sampler_kwargs,
                    extra_body=extra_body_kwargs,
                    extra_headers={
                        "anthropic-version": "2023-06-01",
                    }
                )
                print(completion.content)
                try:
                    completion = completion.content
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
    
    def get_context(self):
        context = super().get_context()
        new_context = []
        message_group = None
        for message in context:
            if message["role"] == "system":
                message["role"] = "user"
            if message_group is None:
                message_group = message
            else:
                if message["role"] == message_group["role"]:
                    message_group["content"] += "\n" + message["content"]
                else:
                    new_context.append(message_group)
                    message_group = message
            # new_context.append(message)
        if message_group is not None:
            new_context.append(message_group)
        return new_context
    
    @utils.time_it
    def acreate(self, messages, message_prefix="", force_speaker=None): # Creates a completion stream for the messages provided to generate a speaker and their response
        # logging.info(f"aMessages: {messages}")
        retries = 5
        while retries > 0:
            try:
                anthropic_stop = list(self.stop)
                anthropic_stop = [self.message_separator,self.EOS_token,self.BOS_token] + anthropic_stop
                anthropic_stop = [stop for stop in anthropic_stop if stop != ""] # Remove empty strings from the stop list
                logging.info("Stop Strings:",anthropic_stop)
                sampler_kwargs = {
                    "top_p": self.top_p,
                    "top_k":self.top_k,
                    "temperature": self.temperature,
                    "stop_sequences": anthropic_stop
                }
                for kwarg in self.config.banned_samplers:
                    if kwarg in sampler_kwargs:
                        del sampler_kwargs[kwarg]
                extra_body_kwargs = {}
                for kwarg in self.config.banned_samplers:
                    if kwarg in extra_body_kwargs:
                        del extra_body_kwargs[kwarg]
                if self.config.reverse_proxy:
                    extra_body_kwargs["proxy_password"] = self.api_key
                logging.warning("Using chat completions because true text completions are not supported by Anthropic. Expect performance to be degraded compared to using any provider that supports true text completions.")
                if force_speaker is not None and self._prompt_style["force_speaker"]:
                    force_speaker_string = force_speaker.name + self.config.message_signifier
                    logging.info("Assistant Prefill(Forced Author)|",force_speaker_string)
                    messages.append({
                        "role":"assistant",
                        "content":force_speaker_string,
                    })
                if message_prefix != "":
                    logging.info("Assistant Prefill(Message prefix)|",message_prefix)
                    # The last message will only be by the assistant if the speaker was forced, if it was, append the message prefix to the last message, if not, make a new message with the message prefix
                    if force_speaker is not None:
                        messages[-1]["content"] += message_prefix
                    else:
                        messages.append({
                            "role":"assistant",
                            "content":message_prefix,
                        })
                logging.info(f"Messages: {messages}")
                if self.config.log_all_api_requests:
                    log_id = None
                    while log_id is None or os.path.exists(self.config.api_log_dir+"/"+log_id+".log"):
                        log_id = str(random.randint(100000,999999))
                    os.makedirs(self.config.api_log_dir, exist_ok=True)
                    with open(self.config.api_log_dir+"/"+log_id+".json", "w") as f:
                        request_json = {
                            "messages": messages,
                            "model": self.config.anthropic_model,
                            "max_tokens": self.config.max_tokens,
                            **sampler_kwargs,
                            **extra_body_kwargs,
                            "stream": True,
                        }
                        json_string = json.dumps(request_json)
                        f.write(json_string)
                with self.client.messages.stream(messages=messages,
                    model=self.config.anthropic_model, 
                    max_tokens=self.config.max_tokens,
                    **sampler_kwargs,
                    extra_body=extra_body_kwargs,
                    extra_headers={
                        "anthropic-version": "2023-06-01",
                    }
                )  as stream:
                    for part in stream.text_stream:
                        if part is None or type(part) != str:
                            logging.error(f"Failed to parse completion part from Anthropic API. Please check your API key and internet connection.",part)
                        logging.info(f"Completion:"+str(part))
                        yield part
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