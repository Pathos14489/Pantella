print("Loading llava_cpp_python.py")
from src.logging import logging, time
import src.utils as utils
import src.llms.llama_cpp_python as llama_cpp_python_LLM
import ctypes
import array
import urllib.request
import numpy as np
import base64
import os
from PIL import Image
import io
logging.info("Imported required libraries in llava_cpp_python.py")

try:
    import pygetwindow
    loaded_pygetwindow = True
    logging.info("Imported pygetwindow in llava_cpp_python.py")
except Exception as e:
    loaded_pygetwindow = False
    logging.warn(f"Failed to load pygetwindow, so llava-cpp-python inference engine cannot be used! Please check that you have installed it correctly if you want to use it, otherwise you can ignore this warning.")

try:
    import dxcam
    loaded_dxcam = True
    logging.info("Imported dxcam in llava_cpp_python.py")
except Exception as e:
    loaded_dxcam = False
    logging.warn(f"Failed to load dxcam, so llava-cpp-python inference engine cannot be used! Please check that you have installed it correctly if you want to use it, otherwise you can ignore this warning.")

try:
    from llama_cpp.llava_cpp import llava_eval_image_embed, llava_image_embed_make_with_bytes, clip_model_load, llava_image_embed_free
    loaded = True
    logging.info("Imported llama-cpp-python in llava_cpp_python.py")
except Exception as e:
    loaded = False
    logging.warn(f"Failed to load llama-cpp-python, so llava-cpp-python inference engine cannot be used! Please check that you have installed it correctly if you want to use it, otherwise you can ignore this warning.")

try:
    from paddleocr import PaddleOCR, draw_ocr
    ocr_loaded = True
    logging.info("Imported paddleocr in llava_cpp_python.py")
except Exception as e:
    ocr_loaded = False
    logging.warn(f"Error loading paddleocr for 'llava-cpp-python'(not a typo) inference engine. Please check that you have installed paddleocr correctly. OCR will not be used but basic image embedding will still work.")
    logging.warn(e)


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


class LLM(llama_cpp_python_LLM.LLM): # Uses llama-cpp-python as the LLM inference engine
    def __init__(self, conversation_manager):
        global inference_engine_name
        super().__init__(conversation_manager)
        if loaded:
            try:
                self.clip_model = clip_model_load(self.config.llava_clip_model_path.encode(), 1)
            except Exception as e:
                logging.error(f"Error loading clip model for 'llava-cpp-python'(not a typo) inference engine. Please check that the model path is correct in config.json.")
                input("Press Enter to exit.")
                raise e
        else:
            logging.error(f"Error loading llama-cpp-python for 'llava-cpp-python'(not a typo) inference engine. Please check that you have installed llama-cpp-python correctly.")
            input("Press Enter to exit.")
            raise Exception("Llama-cpp-python not installed, install llama-cpp-python to use llama-cpp-python.")
        if self.config.paddle_ocr and not ocr_loaded: # Load paddleocr if it's installed
            logging.error(f"Error loading paddleocr for 'llava-cpp-python'(not a typo) inference engine. Please check that you have installed paddleocr correctly. OCR will not be used but basic image embedding will still work.")
            raise Exception("PaddleOCR not installed, disable paddle_ocr in config.json or install PaddleOCR to use paddle_ocr.")
        elif self.config.paddle_ocr and ocr_loaded:
            self.ocr = PaddleOCR(use_angle_cls=self.config.ocr_use_angle_cls, lang=self.config.ocr_lang)
        self.append_system_image_near_end = self.config.append_system_image_near_end
        if not self.append_system_image_near_end:
            self.prompt_style = "vision"
        self.game_window = None
        self.game_window_name = None
        if loaded_dxcam:
            self.camera = dxcam.create()
        else:
            logging.error(f"Error loading dxcam for 'llava-cpp-python'(not a typo) inference engine. Please check that you have installed dxcam correctly.")
            input("Press Enter to exit.")
            raise Exception("DXCam not installed, install DXCam to use LLaVA via llama-cpp-python(Windows only).")
        if not loaded_pygetwindow:
            logging.error(f"Error loading pygetwindow for 'llava-cpp-python'(not a typo) inference engine. Please check that you have installed pygetwindow correctly.")
            input("Press Enter to exit.")
            raise Exception("PyGetWindow not installed, install PyGetWindow to use LLaVA via llama-cpp-python(Windows only).")
        self.get_game_window()

    @property
    def ocr_resolution(self):
        return self.config.ocr_resolution
    
    @property
    def clip_resolution(self):
        return self.config.clip_resolution

    def get_game_window(self):
        if not loaded_pygetwindow:
            raise Exception("PyGetWindow not installed, install PyGetWindow to use LLaVA via llama-cpp-python.")
        if self.game_window_name != None:
            try:
                self.game_window = pygetwindow.getWindowsWithTitle(self.game_window_name)[0]
                logging.info(f"Game Window Found: {self.game_window_name}")
            except:
                logging.error(f"Error loading game window for 'llava-cpp-python'(not a typo) inference engine. Game window lost - Was the game closed? Please restart the game and try again.")
                input("Press Enter to exit.")
                raise Exception("Game window lost - Was the game closed? Please restart the game and Pantella and try again.")
        if self.config.game_id == "fallout4":
            game_windows = pygetwindow.getWindowsWithTitle("Fallout 4")
            self.game_window_name = "Fallout 4"
            if len(game_windows) == 0:
                game_windows = pygetwindow.getWindowsWithTitle("Fallout 4 VR")
                self.game_window_name = "Fallout 4 VR"
            if len(game_windows) == 0:
                game_windows = pygetwindow.getWindowsWithTitle("Fallout4VR")
                self.game_window_name = "Fallout 4 VR"
            logging.info(f"Game Window Found: {self.game_window_name}")
        elif self.config.game_id == "skyrim":
            game_windows = pygetwindow.getWindowsWithTitle("Skyrim Special Edition")
            self.game_window_name = "Skyrim Special Edition"
            if len(game_windows) == 0:
                game_windows = pygetwindow.getWindowsWithTitle("Skyrim VR")
                self.game_window_name = "Skyrim VR"
            logging.info(f"Game Window Found: {self.game_window_name}")
        else:
            logging.error(f"Error loading game window for 'llava-cpp-python'(not a typo) inference engine. No game window found  - Game might not be supported by llava-cpp-python inference engine by default - Please specify the name of the Game Window EXACTLY as it's shown in the title bar of the game window: ")
            game_name = input("Game Name: ")
            try:
                game_windows = pygetwindow.getWindowsWithTitle(game_name)
                self.game_window_name = game_name
            except Exception as e:
                logging.error(f"Error loading game window for 'llava-cpp-python'(not a typo) inference engine. No game window found or game not supported by inference engine.")
                input("Press Enter to exit.")
                raise e
        if len(game_windows) == 0:
            logging.error(f"Error loading game window for 'llava-cpp-python'(not a typo) inference engine. No game window found or game not supported by inference engine.")
            input("Press Enter to exit.")
            raise Exception("No game window found or game not supported by inference engine.")
        self.game_window = game_windows[0]

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

    def get_ascii_block(self, paddle_result, img, ascii_representation_max_size = 128):
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
        logging.info("Theoretical ASCII Area:",theoretical_ascii_area)
        logging.info("True ASCII Area:",true_area)
        # write to ascii_representation
        ocr_filter = self.config.ocr_filter # list of bad strings to filter out
        for i in range(len(boxes)):
            logging.info("Box:",boxes[i],txts[i])
            point_1 = boxes[i][0]
            point_2 = boxes[i][1]
            point_3 = boxes[i][2]
            point_4 = boxes[i][3]
            text = txts[i]
            filtered = False
            for bad_string in ocr_filter:
                if bad_string in text or text == "" or text.strip() == "" or bad_string.lower() in text.lower():
                    filtered = True
                    break
            if filtered:
                continue
            centered_x = int((point_1[0] + point_2[0] + point_3[0] + point_4[0]) / 4)
            centered_y = int((point_1[1] + point_2[1] + point_3[1] + point_4[1]) / 4)
            centered_point = (centered_x, centered_y)
            logging.info("Centered Point:",centered_point)
            centered_x = int((centered_x / image_width) * ascii_representation_size[0])
            centered_y = int((centered_y / image_height) * ascii_representation_size[1])
            centered_point = (centered_x, centered_y)
            logging.info("Centered Point:",centered_point)
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
        logging.info("---BLOCK TOP")
        logging.info(ascii_representation)
        logging.info("---BLOCK BOTTOM")
        return ascii_representation
    
    def get_player_perspective(self):
        """Get the player's perspective image embed using dxcam"""
        left, top, right, bottom = self.game_window.left, self.game_window.top, self.game_window.right, self.game_window.bottom
        region = (left, top, right, bottom)
        frame = self.camera.grab(region=region) # Return array of shape (height, width, 3)
        frame = Image.fromarray(frame)

        if self.config.paddle_ocr:
            result = self.ocr.ocr(np.array(frame), cls=self.config.ocr_use_angle_cls)
            ascii_block = self.get_ascii_block(result, frame, self.ocr_resolution)
        else:
            ascii_block = ""

        frame = frame.convert("RGB")
        frame = frame.resize((self.clip_resolution, self.clip_resolution))
        # frame.show()
        buffered = io.BytesIO() # Don't ask me why this is needed - it just is for some reason.
        frame.save(buffered, format="PNG")
        return self.get_image_embed_from_bytes(buffered.getvalue()), ascii_block
    
        # return self.get_image_embed_from_file(self.config.game_path+"/PlayerPerspective.png")

    def get_context(self):
        context = self.get_context()
        if self.append_system_image_near_end:
            image_message = {
                "role": self.config.system_name,
                "content": self.config.llava_image_message
            }
            depth = self.config.llava_image_message_depth
            context = context[:depth] + [image_message] + context[depth:] # Add the image message to the context
        return context
    
    def multimodal_prompt_format(self, prompt):
        if os.path.exists(self.config.game_path+"/PlayerPerspective.png") and "<image>" in prompt:
            logging.info(f"PlayerPerspective.png exists - using it for multimodal completion")
            image_embed, ascii_block = self.get_player_perspective()
            if "<ocr>" in prompt:
                prompt = prompt.replace("<ocr>", ascii_block)
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
                prompt += self.tokenizer.start_message(self.config.assistant_name) # Start empty message from no one to let the LLM generate the speaker by split \n
                logging.info(f"Raw Prompt: {prompt}")
                prompt = self.multimodal_prompt_format(prompt)
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
                    raise e
                time.sleep(5)
                retries -= 1
                continue
            break
        return completion
    
    def acreate(self, messages, message_prefix="", force_speaker=None, banned_chars=[]): # Creates a completion stream for the messages provided to generate a speaker and their response
        logging.info(f"aMessages: {messages}")
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
                prompt = self.multimodal_prompt_format(prompt)
                # logging.info(f"Embedded Prompt: {prompt}")
                logging.info(f"Type of prompt: {type(prompt)}")
                return self.llm.create_completion(prompt=prompt,
                    max_tokens=self.max_tokens,
                    top_k=self.top_k,
                    top_p=self.top_p,
                    min_p=self.min_p,
                    temperature=self.temperature,
                    repeat_penalty=self.repeat_penalty, 
                    stop=self.stop + banned_chars,
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
                    raise e
                time.sleep(5)
                retries -= 1
                continue

class Tokenizer(llama_cpp_python_LLM.Tokenizer): # Uses llama-cpp-python's tokenizer
    def __init__(self, conversation_manager):
        super().__init__(conversation_manager)