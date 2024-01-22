import src.utils as utils
import src.tokenizers.base_tokenizer as tokenizer
import logging
import requests
tokenizer_slug = "koboldcpp"
class Tokenizer(tokenizer.base_Tokenizer): # Gets token count from OpenAI's embedding API -- WARNING SLOW AS HELL -- Only use if you don't want to set up the right tokenizer for your local model or if you don't know how to do that
    def __init__(self, conversation_manager, client):
        super().__init__(conversation_manager)
        if not (self.config.inference_engine == "openai" or self.config.inference_engine == "default"):
            logging.error(f"koboldcpp tokenizer only works using OpenAI's API! Please check your config.ini file and try again!")
            input("Press enter to continue...")
            exit()
        self.tokenizer_slug = tokenizer_slug
        self.client = client # Unnecessary for this tokenizer, but it's here for compatibility with other openai tokenizers
        
    @utils.time_it
    def get_token_count(self, string):
        url = self.config.alternative_openai_api_base + "/extra/tokencount"
        data = {"prompt": string}
        r = requests.post(url, json=data)
        num_tokens = int(r.text)
        return num_tokens
    