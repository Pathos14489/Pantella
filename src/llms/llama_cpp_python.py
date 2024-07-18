print("Importing llama_cpp_python.py")
import src.utils as utils
import ctypes
import array
import numpy as np
import os
from src.llms.base_llm import base_LLM, load_image
import src.tokenizers.base_tokenizer as tokenizer
from src.logging import logging, time
import traceback
logging.info("Imported required libraries in llama_cpp_python.py")

try:
    from llama_cpp import Llama
    from llama_cpp.llava_cpp import llava_eval_image_embed, llava_image_embed_make_with_bytes, clip_model_load, llava_image_embed_free
    loaded = True
    logging.info("Imported llama-cpp-python in llama_cpp_python.py")
except Exception as e:
    loaded = False
    logging.warning("Failed to load llama-cpp-python. Please check that you have installed it correctly if you intend to use it. If you don't intend to use it, you can ignore this message.")

inference_engine_name = "llama-cpp-python"

llama_model = None # Used to store the llama-cpp-python model so it can be reused for the tokenizer

class LLM(base_LLM): # Uses llama-cpp-python as the LLM inference engine
    def __init__(self, conversation_manager, vision_enabled=False):
        global llama_model
        global inference_engine_name
        super().__init__(conversation_manager, vision_enabled=vision_enabled)
        self.inference_engine_name = inference_engine_name
        if loaded:
            if llama_model is None:
                tensor_split = self.config.tensor_split
                if len(tensor_split) == 0:
                    tensor_split = None
                self.llm = Llama(
                    model_path=self.config.model_path,
                    n_ctx=self.config.maximum_local_tokens,
                    n_gpu_layers=self.config.n_gpu_layers,
                    n_batch=self.config.n_batch,
                    n_threads=self.config.n_threads,
                    tensor_split=tensor_split,
                    main_gpu=self.config.main_gpu,
                    split_mode=self.config.split_mode,
                    use_mmap=self.config.use_mmap,
                    use_mlock=self.config.use_mlock,
                    n_threads_batch=self.config.n_threads_batch,
                    offload_kqv=self.config.offload_kqv,
                )
            else:
                self.llm = llama_model
        else:
            logging.error(f"Error loading llama-cpp-python. Please check that you have installed it correctly.")
            input("Press Enter to exit.")
            raise ValueError(f"Error loading llama-cpp-python. Please check that you have installed it correctly.")
        llama_model = self.llm
        logging.info(f"Running Pantella with llama-cpp-python. The language model chosen can be changed via config.json")
        logging.info(f"Testing llama-cpp-python...")
        test_prompt = "Hello, I am a llama-cpp-python test prompt. I am used to test llama-cpp-python's functi"
        test_completion = self.llm.create_completion(test_prompt, max_tokens=10)
        logging.info(f"Test Completion: {test_completion}")
        if self.vision_enabled:
            logging.info("Vision is enabled for llama-cpp-python")
            if loaded:
                try:
                    self.clip_model = clip_model_load(self.config.llava_clip_model_path.encode(), 1)
                except Exception as e:
                    logging.error(f"Error loading clip model for 'llava-cpp-python'(not a typo) inference engine. Please check that the model path is correct in config.json.")
                    tb = traceback.format_exc()
                    logging.error(tb)
                    input("Press Enter to exit.")
                    raise e
            else:
                logging.error(f"Error loading llama-cpp-python for 'llava-cpp-python'(not a typo) inference engine. Please check that you have installed llama-cpp-python correctly.")
                input("Press Enter to exit.")
                raise Exception("Llama-cpp-python not installed, install llama-cpp-python to use llama-cpp-python.")

    def get_image_embed_from_bytes(self, image_bytes):
        data_array = array.array("B", image_bytes)
        c_ubyte_ptr = (
            ctypes.c_ubyte * len(data_array)
        ).from_buffer(data_array)
        embed = (
            llava_image_embed_make_with_bytes(
                ctx_clip=self.clip_model,
                n_threads=self.config.n_threads,
                image_bytes=c_ubyte_ptr,
                image_bytes_length=len(image_bytes),
            )
        )
        return embed
    
    def get_image_embed_from_url(self, url):
        image_bytes = load_image(url)
        return self.get_image_embed_from_bytes(image_bytes)

    def get_image_embed_from_file(self, path):
        with open(path, "rb") as f:
            image_bytes = f.read()
        return self.get_image_embed_from_bytes(image_bytes)

    def get_image_embed_from_PIL(self, image):
        image_bytes = image.tobytes()
        return self.get_image_embed_from_bytes(image_bytes)

    def eval_image_embed(self, embed):
        try:
            n_past = ctypes.c_int(self.llm.n_tokens)
            n_past_p = ctypes.pointer(n_past)
            
            llava_eval_image_embed(
                ctx_llama=self.llm.ctx,
                embed=embed,
                n_batch=self.llm.n_batch,
                n_past=n_past_p,
            )
            assert self.llm.n_ctx() >= n_past.value
            self.llm.n_tokens = n_past.value
        except Exception as e:
            print(e)
            print("Failed to eval image")
        finally:
            llava_image_embed_free(embed)
            
    def multimodal_eval(self, text, embeds): # -> prompt
        """Evaluates a multimodal prompt with text and image embeds. The text is split by "{image}" and the image embeds are inserted in the order they appear in the text. The text is then tokenized and the image embeds are evaluated in the model. The input_ids are then returned."""
        assert len(embeds) > 0
        assert type(text) == str
        assert type(embeds) == list
        
        text_chunks = text.split("{image}")
        assert len(text_chunks) == len(embeds) + 1
        text_chunks = [chunk.encode("utf8") for chunk in text_chunks]

        self.llm.reset() # Reset the model
        # clear the input_ids
        self.llm.input_ids = np.ndarray((self.llm.n_ctx(),), dtype=np.intc)
        # print(text_chunks)
        for i, chunk in enumerate(text_chunks):
            self.llm.eval(self.llm.tokenize(chunk, add_bos=True if i == 0 else False))
            if i < len(embeds):
                self.eval_image_embed(embeds[i])
        return self.llm.input_ids[: self.llm.n_tokens].tolist()
    
    def multimodal_prompt_format(self, prompt):
        if os.path.exists(self.config.game_path+"/PlayerPerspective.png") and "{image}" in prompt:
            logging.info(f"PlayerPerspective.png exists - using it for multimodal completion")
            image_embed, ascii_block = self.get_player_perspective()
            if "{ocr}" in prompt:
                prompt = prompt.replace("{ocr}", ascii_block)
            prompt = self.multimodal_eval(prompt, [image_embed])
        return prompt

    @utils.time_it
    def create(self, messages):
        # logging.info(f"cMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                prompt = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message(self.config.assistant_name)
                logging.info(f"Raw Prompt: {prompt}")
                if self.vision_enabled:
                    prompt = self.multimodal_prompt_format(prompt)

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
                    logit_bias=self.logit_bias,
                    stream=False,
                )
                completion = completion["choices"][0]["text"]
                logging.info(f"Completion:",completion)
            except Exception as e:
                logging.warning('Error generating completion, retrying in 5 seconds...')
                logging.warning(e)
                print(e)
                tb = traceback.format_exc()
                logging.error(tb)
                # raise e
                if retries == 1:
                    logging.error('Error generating completion after 5 retries, exiting...')
                    input('Press enter to continue...')
                    raise e
                time.sleep(5)
                retries -= 1
                continue
            break
        return completion
    
    def acreate(self, messages, message_prefix="", force_speaker=None): # Creates a completion stream for the messages provided to generate a speaker and their response
        logging.info(f"aMessages: {messages}")
        retries = 5
        while retries > 0:
            logging.info(f"Retries: {retries}")
            try:
                prompt = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message(self.config.assistant_name)
                if force_speaker is not None:
                    prompt += force_speaker.name + self.config.message_signifier
                    prompt += message_prefix
                logging.info(f"Raw Prompt: {prompt}")
                if self.vision_enabled:
                    prompt = self.multimodal_prompt_format(prompt)
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
                    logit_bias=self.logit_bias,
                    tfs_z=self.tfs_z,
                    stream=True,
                )
            except Exception as e:
                logging.warning('Error creating completion stream, retrying in 5 seconds...')
                logging.warning(e)
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
        global llama_model
        super().__init__(conversation_manager)
        if llama_model is None:
            self.llm = Llama(model_path=self.conversation_manager.config.model_path)
        else:
            self.llm = llama_model
            
    @utils.time_it
    def get_token_count(self, string):
        # logging.info(f"Tokenizer.get_token_count() called with string: {string}")
        tokens = self.llm.tokenize(f"{string}".encode("utf-8"))
        return len(tokens)