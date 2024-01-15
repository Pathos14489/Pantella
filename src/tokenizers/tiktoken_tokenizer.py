import src.utils as utils
import src.tokenizers.base_tokenizer as tokenizer
import tiktoken
class Tokenizer(tokenizer.base_Tokenizer): # Tokenizes(only availble for counting the tokens in a string presently for local_models), and parses and formats messages for use with the language model
    def __init__(self,config, client):
        super().__init__(config)
        self.client = client
        self.encoding = tiktoken.encoding_for_model(config.llm)

    @utils.time_it
    def get_token_count(self, string):
        tokens = self.encoding.encode(string)
        num_tokens = len(tokens)
        return num_tokens