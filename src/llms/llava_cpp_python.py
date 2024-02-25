import src.utils as utils
import src.llms.llama_cpp_python as llama_cpp_python_LLM
import src.tokenizers.base_tokenizer as tokenizer
from src.logging import logging, time
import ctypes
import array
import urllib.request
import numpy as np
import base64
import os
import dxcam
import pygetwindow
from PIL import Image
import io

try:
    from llama_cpp import Llama
    from llama_cpp.llava_cpp import llava_eval_image_embed, llava_image_embed_make_with_bytes, clip_model_load, llava_image_embed_free
    loaded = True
except Exception as e:
    loaded = False

try:
    from paddleocr import PaddleOCR, draw_ocr
    ocr_loaded = True
except Exception as e:
    ocr_loaded = False

inference_engine_name = "llava-cpp-python"

def get_data_url(url):
    return "data:image/png;base64," + base64.b64encode(urllib.request.urlopen(url).read()).decode("utf-8")

def load_image( image_url: str) -> bytes:
    if image_url.startswith("data:"):
        import base64

        image_bytes = base64.b64decode(image_url.split(",")[1])
        return image_bytes
    else:
        import urllib.request

        with urllib.request.urlopen(image_url) as f:
            image_bytes = f.read()
            return image_bytes

def get_ascii_block(paddle_result, img, ascii_representation_max_size = 128):
    image_width, image_height = img.size
    ascii_representation_size = (0,0)
    if image_width > image_height:
        ascii_representation_size = (ascii_representation_max_size, int(ascii_representation_max_size * (image_height / image_width)))
    else:
        ascii_representation_size = (int(ascii_representation_max_size * (image_width / image_height)), ascii_representation_max_size)
    # ascii_representation = "#" * (ascii_representation_size[0]+2) + "\n"
    ascii_representation = ""

    print("ASCII Size:",ascii_representation_size)
    paddle_result = paddle_result[0]
    if paddle_result == None or len(paddle_result) == 0:
        return ""
    boxes = [line[0] for line in paddle_result]
    txts = [line[1][0] for line in paddle_result]
    _scores = [line[1][1] for line in paddle_result]
    true_area = 0
    # blank ascii_representation
    for i in range(ascii_representation_size[1]):
        blank_line = " " * ascii_representation_size[0] + "\n" # "#" + 
        true_area += len(blank_line)
        ascii_representation += blank_line
    theoretical_ascii_area = ascii_representation_size[0] * ascii_representation_size[1]
    print("Theoretical ASCII Area:",theoretical_ascii_area)
    print("True ASCII Area:",true_area)
    # write to ascii_representation
    for i in range(len(boxes)):
        print("Box:",boxes[i])
        point_1 = boxes[i][0]
        point_2 = boxes[i][1]
        point_3 = boxes[i][2]
        point_4 = boxes[i][3]
        text = txts[i]
        centered_x = int((point_1[0] + point_2[0] + point_3[0] + point_4[0]) / 4)
        centered_y = int((point_1[1] + point_2[1] + point_3[1] + point_4[1]) / 4)
        centered_point = (centered_x, centered_y)
        print("Centered Point:",centered_point)
        centered_x = int((centered_x / image_width) * ascii_representation_size[0])
        centered_y = int((centered_y / image_height) * ascii_representation_size[1])
        centered_point = (centered_x, centered_y)
        print("Centered Point:",centered_point)
        # overwrite ascii_representation to include text centered at centered_point offset by half the length of text
        text_length = len(text)
        text_start = centered_x - int(text_length / 2)
        text_end = text_start + text_length
        
        ascii_lines = ascii_representation.split("\n")
        ascii_lines[centered_y] = ascii_lines[centered_y][:text_start] + text + ascii_lines[centered_y][text_end:]
        ascii_representation = "\n".join(ascii_lines)
        

    new_ascii_representation = ""
    for line in ascii_representation.split("\n"):
        if line.strip() != "":
            new_ascii_representation += line + "\n"
    ascii_representation = new_ascii_representation
    # ascii_representation += "#" * (ascii_representation_size[0]+2)
    print("TOP")
    print(ascii_representation)
    print("BOTTOM")
    return ascii_representation

class LLM(llama_cpp_python_LLM.LLM): # Uses llama-cpp-python as the LLM inference engine
    def __init__(self, conversation_manager):
        global inference_engine_name
        super().__init__(conversation_manager)
        if loaded:
            self.clip_model = clip_model_load(self.config.llava_clip_model_path.encode(), 1)
        else:
            logging.error(f"Error loading llama-cpp-python for 'llava-cpp-python'(not a typo) inference engine. Please check that you have installed llama-cpp-python correctly.")
            input("Press Enter to exit.")
            exit()
        if ocr_loaded:
            self.ocr = PaddleOCR(use_angle_cls=self.config.ocr_use_angle_cls, lang=self.config.ocr_lang)
        else:
            logging.error(f"Error loading paddleocr for 'llava-cpp-python'(not a typo) inference engine. Please check that you have installed paddleocr correctly. OCR will not be used but basic image embedding will still work.")
        self.append_system_image_near_end = self.config.append_system_image_near_end
        if not self.append_system_image_near_end:
            self.prompt_style = "vision"
        self.game_window = None
        self.game_window_name = None
        self.camera = dxcam.create()
        self.get_game_window()

    def get_context(self):
        context = super().get_context()
        if self.append_system_image_near_end:
            image_message = {
                "role": "system",
                "content": "The image below is {player_perspective_name}'s perspective:\n<image>",
            }
            depth = self.config.llava_image_message_depth
            context = context[:depth] + [image_message] + context[depth:] # Add the image message to the context
        return context

    def get_game_window(self):
        if self.game_window_name != None:
            try:
                self.game_window = pygetwindow.getWindowsWithTitle(self.game_window_name)[0]
                logging.info(f"Game Window Found: {self.game_window_name}")
            except:
                logging.error(f"Error loading game window for 'llava-cpp-python'(not a typo) inference engine. Game window lost - Was the game closed? Please restart the game and try again.")
                input("Press Enter to exit.")
                exit()
        if self.config.game_id == "fallout4":
            self.game_window = pygetwindow.getWindowsWithTitle("Fallout 4")[0]
            self.game_window_name = "Fallout 4"
            logging.info(f"Game Window Found: {self.game_window_name}")
        elif self.config.game_id == "skyrim":
            self.game_window = pygetwindow.getWindowsWithTitle("Skyrim Special Edition")[0]
            self.game_window_name = "Skyrim Special Edition"
            logging.info(f"Game Window Found: {self.game_window_name}")
        else:
            logging.error(f"Error loading game window for 'llava-cpp-python'(not a typo) inference engine. No game window found  - Game might not be supported by llava-cpp-python inference engine by default - Please specify the name of the Game Window EXACTLY as it's shown in the title bar of the game window: ")
            game_name = input("Game Name: ")
            try:
                self.game_window = pygetwindow.getWindowsWithTitle(game_name)[0]
                self.game_window_name = game_name
            except Exception as e:
                logging.error(f"Error loading game window for 'llava-cpp-python'(not a typo) inference engine. No game window found or game not supported by inference engine.")
                input("Press Enter to exit.")
                exit()

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
        """Evaluates a multimodal prompt with text and image embeds. The text is split by "<image>" and the image embeds are inserted in the order they appear in the text. The text is then tokenized and the image embeds are evaluated in the model. The input_ids are then returned."""
        assert len(embeds) > 0
        assert type(text) == str
        assert type(embeds) == list
        
        text_chunks = text.split("<image>")
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

    def get_player_perspective(self):
        """Get the player's perspective image embed using dxcam"""
        left, top, right, bottom = self.game_window.left, self.game_window.top, self.game_window.right, self.game_window.bottom
        region = (left, top, right, bottom)
        frame = self.camera.grab(region=region) # Return array of shape (height, width, 3)
        frame = Image.fromarray(frame)
        frame = frame.convert("RGB")
        frame = frame.resize((672, 672))
        # frame.show()
        buffered = io.BytesIO() # Don't ask me why this is needed - it just is for some reason.
        frame.save(buffered, format="PNG")
        return self.get_image_embed_from_bytes(buffered.getvalue())
    
        # return self.get_image_embed_from_file(self.config.game_path+"/PlayerPerspective.png")

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
                if os.path.exists(self.config.game_path+"/PlayerPerspective.png") and "<image>" in prompt:
                    logging.info(f"PlayerPerspective.png exists - using it for multimodal completion")
                    prompt = self.multimodal_eval(prompt, [self.get_player_perspective()])
                # logging.info(f"Embedded Prompt: {prompt}")
                logging.info(f"Type of prompt: {type(prompt)}")
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
                if os.path.exists(self.config.game_path+"/PlayerPerspective.png") and "<image>" in prompt:
                    logging.info(f"PlayerPerspective.png exists - using it for multimodal completion")
                    prompt = self.multimodal_eval(prompt, [self.get_player_perspective()])
                # logging.info(f"Embedded Prompt: {prompt}")
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
                    exit()
                time.sleep(5)
                retries -= 1
                continue

class Tokenizer(llama_cpp_python_LLM.Tokenizer): # Uses llama-cpp-python's tokenizer
    def __init__(self, conversation_manager):
        super().__init__(conversation_manager)