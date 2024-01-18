import src.utils as utils
import src.tokenizers.base_tokenizer as tokenizer
import tiktoken
tokenizer_slug = "tiktoken" # default to tiktoken for now (Not always correct, but it's the fastest tokenizer and it works for openai's models, which a lot of users will be relying on probably)
class Tokenizer(tokenizer.base_Tokenizer): # Tokenizes(only availble for counting the tokens in a string presently for local_models), and parses and formats messages for use with the language model
    def __init__(self,conversation_manager, client):
        super().__init__(conversation_manager)
        self.tokenizer_slug = tokenizer_slug # Fastest tokenizer for OpenAI models, change if you want to use a different tokenizer (use 'embedding' for compatibility with any model using the openai API)
        self.client = client
        self.encoding = tiktoken.encoding_for_model(self.config.llm)

    @utils.time_it
    def get_token_count(self, string):
        tokens = self.encoding.encode(string)
        num_tokens = len(tokens)
        return num_tokens