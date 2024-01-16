import logging
import src.utils as utils
inference_engine_name = "base_LLM"
tokenizer_slug = "tiktoken" # default to tiktoken for now (Not always correct, but it's the fastest tokenizer and it works for openai's models, which a lot of users will be relying on probably)
class base_LLM():
    def __init__(self, config, token_limit, language_info):
        self.config = config
        self.tokenizer = None
        self.token_limit = token_limit
        self.language_info = language_info
        
        self.inference_engine_name = inference_engine_name
        self.tokenizer_slug = tokenizer_slug

    # the string printed when your print() this object
    def __str__(self):
        return f"{self.inference_engine_name} LLM"
    
    @utils.time_it
    def chatgpt_api(self, input_text, messages): # Creates a synchronouse completion for the messages provided to generate response for the assistant to the user. TODO: remove later
        print(f"ChatGPT API: {input_text}")
        print(f"Messages: {messages}")
        if not input_text:
            logging.warning('Empty input text, skipping...')
            return "", messages
        messages.append(
            {"role": self.config.user_name, "content": input_text},
        )
        logging.info('Getting LLM response...')
        reply = self.create(messages)
        
        messages.append(
            {"role": self.config.assistant_name, "content": reply},
        )
        logging.info(f"LLM Response: {reply}")

        return reply, messages

    def create(self, messages): # Creates a completion for the messages provided to generate response for the assistant to the user # TODO: Generalize this more
        logging.info(f"Warning: Using base_LLM.create() instead of a child class, this is probably not what you want to do. Please override this method in your child class!")
        pass

    def acreate(self, messages): # Creates a completion stream for the messages provided to generate a speaker and their response
        logging.info(f"Warning: Using base_LLM.acreate() instead of a child class, this is probably not what you want to do. Please override this method in your child class!")
        pass