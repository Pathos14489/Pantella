print("Importing llama_cpp_python.py")
import src.utils as utils
import ctypes
import array
import numpy as np
import io
from src.inference_engines.base_llm import base_LLM, load_image, TestCoT, get_schema_description
import src.tokenizers.base_tokenizer as tokenizer
from src.logging import logging, time
import traceback
import json
logging.info("Imported required libraries in llama_cpp_python.py")

imported = False
try:
    from llama_cpp import Llama
    from llama_cpp.llava_cpp import llava_eval_image_embed, llava_image_embed_make_with_bytes, clip_model_load, llava_image_embed_free
    import llama_cpp
    import torch
    imported = True
    logging.info("Imported llama-cpp-python in llama_cpp_python.py")
except Exception as e:
    logging.warning("Failed to load llama-cpp-python. Please check that you have installed it correctly if you intend to use it. If you don't intend to use it, you can ignore this message.", e)

llama_model = None # Used to store the llama-cpp-python model so it can be reused for the tokenizer

inference_engine_name = "llama_cpp_python"
tokenizer_slug = "llama_cpp_python" # This slug is effectively unused but it is here for consistency with other inference engines
default_settings = {
    "model_path": ".\\model.gguf",
    "llava_clip_model_path": ".\\clip_model.gguf",
    "n_gpu_layers": 0,
    "n_threads": 4,
    "n_batch": 512,
    "tensor_split": [], # [0.5,0.5] for 2 gpus split evenly, [0.3,0.7] for 2 gpus split unevenly
    "main_gpu": 0,
    "split_mode": 0, # 0 = single gpu, 1 = split layers and kv across gpus, 2 = split rows across gpus
    "use_mmap": True,
    "use_mlock": False,
    "n_threads_batch": 1,
    "offload_kqv": True,
}
settings_description = {
    "model_path": "The path to the model file. This is required for the model to work. If you are using a local model, this should be the path to the model file. If you are using a remote model, this should be the URL to the model file.",
    "llava_clip_model_path": "The path to the clip model file. This is required for the model to work with vision. If you are using a local model, this should be the path to the model file. If you are using a remote model, this should be the URL to the model file.",
    "n_gpu_layers": "The number of layers to run on the GPU. This is used to split the model across multiple GPUs. If you are using a single GPU, this should be 0.",
    "n_threads": "The number of threads to use for the model. This is used to speed up the model inference. If you are using a single GPU, this should be the number of CPU threads you want to use.",
    "n_batch": "The number of tokens to process in a batch. This is used to speed up the model inference. If you are using a single GPU, this should be the number of tokens you want to process in a batch.",
    "tensor_split": "The tensor split to use for the model. This is used to split the model across multiple GPUs. If you are using a single GPU, this should be an empty list.",
    "main_gpu": "The main GPU to use for the model. This is used to split the model across multiple GPUs. If you are using a single GPU, this should be 0.",
    "split_mode": "The split mode to use for the model. This is used to split the model across multiple GPUs. If you are using a single GPU, this should be 0.",
    "use_mmap": "Whether to use memory-mapped files for the model. This is used to speed up the model inference. If you are using a single GPU, this should be True.",
    "use_mlock": "Whether to use mlock to lock the model in memory. This is used to speed up the model inference. If you are using a single GPU, this should be False.",
    "n_threads_batch": "The number of threads to use for the batch processing. This is used to speed up the model inference. If you are using a single GPU, this should be 1.",
    "offload_kqv": "Whether to offload the key-value pairs to the CPU. This is used to speed up the model inference. If you are using a single GPU, this should be True.",
}
options = {
    "main_gpu": [], # The main GPU to use for the model, if using multiple GPUs
    "split_mode": [
        {
            "name": "Single GPU",
            "value": 0,
            "description": "Use a single GPU for the model. This is the default mode and is recommended for most users.",
            "default": True,
            "disabled": False
        },
        {
            "name": "Split Layers and KV across GPUs",
            "value": 1,
            "description": "Split the model layers and key-value pairs across multiple GPUs. This is recommended for users with multiple GPUs and large models.",
            "default": False,
            "disabled": False
        }, 
        {
            "name": "Split Rows across GPUs",
            "value": 2,
            "description": "Split the model rows across multiple GPUs. This is recommended for users with multiple GPUs and large models.",
            "default": False,
            "disabled": False
        }
    ],
}
settings = {}
loaded = False
description = "This inference engine uses llama-cpp-python to run the LLM. It is a high-performance inference engine that supports various models and features. This, and using a compatible model over OpenAI API, is the recommended way to run Pantella. It supports vision and COT (Chain of Thought) reasoning, and can generate characters based on the prompt provided. It also supports multimodal prompts with text and image embeds for NPCs that can see what you see."

if imported:
    if torch.cuda.is_available():
        # add the available GPUs to the main_gpu option
        for i in range(torch.cuda.device_count()):
            gpu_name = torch.cuda.get_device_name(i)
            if gpu_name is None or gpu_name == "":
                gpu_name = f"GPU {i}"
            if i not in [option["value"] for option in options["main_gpu"]]: # Avoid duplicates
                # Add the GPU to the main_gpu option
                if i == 0:
                    description = "Use the first GPU for the model. This is the default GPU and is recommended for most users."
                else:
                    description = f"Use GPU {i} for the model. This is recommended if you have a multi-GPU setup and want to use a specific GPU for the model."
                options["main_gpu"].append({
                    "name": gpu_name,
                    "value": i,
                    "description": description,
                    "default": True if i == 0 else False, # Default to the first GPU
                    "disabled": False
                })
    # If no GPUs are available, disable the main_gpu option
    if len(options["main_gpu"]) == 0:
        options["main_gpu"].append({
            "name": "No GPU",
            "value": -1,
            "description": "No GPU available. The model will run on the CPU.",
            "default": True,
            "disabled": True
        })
        default_settings["main_gpu"] = -1 # Set the main GPU to -1 if no GPUs are available
    # If no GPUs are available, disable the split_mode option
    if len(options["main_gpu"]) == 1 and options["main_gpu"][0]["value"] == -1:
        options["split_mode"] = [
            {
                "name": "No GPU Available",
                "value": 0,
                "description": "No GPU available. The model will run on the CPU. If you do have a compatible GPU, please check that you have installed llama-cpp-python and torch correctly.",
                "default": True,
                "disabled": True
            }
        ]
else:
    logging.warning("llama-cpp-python not imported, skipping GPU detection.")
    
class LLM(base_LLM): # Uses llama-cpp-python as the LLM inference engine
    def __init__(self, conversation_manager, vision_enabled=False):
        global llama_model, inference_engine_name, loaded, default_settings
        super().__init__(conversation_manager, vision_enabled=vision_enabled)
        default_settings = self.default_inference_engine_settings
        self.inference_engine_name = inference_engine_name
        if imported:
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
        logging.output(f"Test Completion: {test_completion}")
        if self.vision_enabled:
            logging.info("Vision is enabled for llama-cpp-python")
            if imported:
                try:
                    self.clip_model = clip_model_load(self.config.llava_clip_model_path.encode(), 1)
                    logging.success(f"Loaded vision model for llama-cpp-python")
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
            
        if self.cot_enabled:
            logging.info("COT is enabled for llama-cpp-python")
            if self.cot_enabled and self.conversation_manager.thought_process is not None: # If COT is enabled, we need to use the JSON schema for the response format
                grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(TestCoT.model_json_schema()))
                completion = self.llm.create_completion("",
                    max_tokens=512,
                    logit_bias=self.logit_bias,
                    stream=False,
                    grammar=grammar,
                )
                completion = completion["choices"][0]["text"].strip()
                try:
                    response = json.loads(completion)
                    print(response)
                    self.cot_supported = True
                    self.character_generation_supported = True
                    logging.success(f"llama-cpp-python supports CoT!")
                except:
                    self.cot_supported = False
                    logging.error(f"llama-cpp-python encountered an error while testing CoT. GBNF grammars are not supported by your model or your version of llama-cpp-python.")
                    # input("Press Enter to exit.")
        loaded = True
            
    @property
    def default_inference_engine_settings(self):
        """Returns the default settings for the llama-cpp-python inference engine"""
        return {
            "model_path": self.config.model_path,
            "n_gpu_layers": self.config.n_gpu_layers,
            "n_threads": self.config.n_threads,
            "n_batch": self.config.n_batch,
            "tensor_split": self.config.tensor_split, # [0.5,0.5] for 2 gpus split evenly, [0.3,0.7] for 2 gpus split unevenly
            "main_gpu": self.config.main_gpu,
            "split_mode": self.config.split_mode, # 0 = single gpu, 1 = split layers and kv across gpus, 2 = split rows across gpus
            "use_mmap": self.config.use_mmap,
            "use_mlock": self.config.use_mlock,
            "n_threads_batch": self.config.n_threads_batch,
            "offload_kqv": self.config.offload_kqv,
        }

    def generate_character(self, character_name, character_ref_id, character_base_id, character_in_game_race, character_in_game_gender, character_is_guard=False, character_is_ghost=False, in_game_voice_model=None, location=None):
        """Generate a character based on the prompt provided"""
        if not self.character_generation_supported:
            logging.error(f"Character generation is not supported by llama-cpp-python. Please check that your model supports it and that it is enabled in config.json.")
            return None
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
        prompt, images = self.tokenizer.get_string_from_messages(messages)
        prompt += self.tokenizer.start_message("assistant")
        logging.info(f"Raw Prompt: {prompt}")
        json_schema = self.conversation_manager.character_generator_schema.model_json_schema()
        grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(json_schema))
        character = None
        tries = 5
        while character is None and tries > 0:
            try:
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
                    grammar=grammar,
                )
                completion = completion["choices"][0]["text"]
                response = json.loads(completion)
                character = self.conversation_manager.character_generator_schema(**response)
            except Exception as e:
                logging.error(f"Error generating character:", e)
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

        return character.get_chracter_info(character_ref_id, character_base_id, voice_model)
    
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
    
    def get_player_perspective(self, check_vision=False):
        _, frame, ascii_block = super().get_player_perspective(check_vision)
        buffered = io.BytesIO() # Don't ask me why this is needed - it just is for some reason.
        frame.save(buffered, format="PNG")
        return self.get_image_embed_from_bytes(buffered.getvalue()), ascii_block

    def multimodal_prompt_format(self, prompt):
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
                prompt, images = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message("assistant")
                logging.info(f"Raw Prompt: {prompt}")
                if self.vision_enabled:
                    prompt = self.multimodal_prompt_format(prompt)

                if self.cot_enabled and self.cot_supported and self.conversation_manager.thought_process is not None: # If COT is enabled, we need to use the JSON schema for the response format
                    grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(self.conversation_manager.thought_process.model_json_schema()))
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
                        grammar=grammar,
                    )
                else:
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
                prompt, images = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message("assistant")
                if force_speaker is not None and self._prompt_style["force_speaker"]:
                    prompt += force_speaker.name + self.config.message_signifier
                    prompt += message_prefix
                logging.info(f"Raw Prompt: {prompt}")
                if self.vision_enabled:
                    prompt = self.multimodal_prompt_format(prompt)
                if self.cot_enabled and self.cot_supported and self.conversation_manager.thought_process is not None: # If COT is enabled, we need to use the JSON schema for the response format
                    print("Using CoT Grammar")
                    grammar = llama_cpp.LlamaGrammar.from_json_schema(json.dumps(self.conversation_manager.thought_process.model_json_schema()))
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
                        grammar=grammar,
                    )
                else:
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