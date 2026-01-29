from src.logging import logging
from src.message_formatter import MessageFormatter, PromptStyle
tokenizer_slug = "base_tokenizer"
class base_Tokenizer(): # Tokenizes(only availble for counting the tokens in a string presently for local_models), and parses and formats messages for use with the language model
    def __init__(self, conversation_manager, tokenizer_slug_override=None):
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config
        self.tokenizer_slug = tokenizer_slug # Fastest tokenizer for OpenAI models, change if you want to use a different tokenizer (use 'embedding' for compatibility with any model using the openai API)
        if tokenizer_slug_override is not None:
            self.tokenizer_slug = tokenizer_slug_override
        
    def set_prompt_style(self, prompt_style: dict):
        """Sets the prompt style for the tokenizer"""
        self.message_formatter = MessageFormatter(PromptStyle(**prompt_style["style"]))

    @property
    def BOS_token(self):
        return self.config.BOS_token

    @property
    def EOS_token(self):
        return self.config.EOS_token

    @property
    def role_separator(self):
        return self.config.role_separator
    
    @property
    def message_signifier(self):
        return self.config.message_signifier
    
    @property
    def message_separator(self):
        return self.config.message_separator
    
    @property
    def message_format(self):
        return self.config.message_format
    
    def get_role_prefix(self, role: str) -> str: # Returns the prefix for a role
        """Returns the prefix for a role"""
        return self.message_formatter.get_role_prefix(role)
    
    def get_role_suffix(self, role: str) -> str: # Returns the suffix for a role
        """Returns the suffix for a role"""
        return self.message_formatter.get_role_suffix(role)

    def new_message(self, content, role, name=None): # Parses a string into a message format with the name of the speaker
        """Parses a string into a message format with the name of the speaker"""
        return self.message_formatter.new_message(content, role, name)

    def start_message(self, role="", name=None): # Returns the start of a message with the name of the speaker
        """Returns the start of a message with the name of the speaker"""
        return self.message_formatter.start_message(role, name)

    def end_message(self, role="", name=None): # Returns the end of a message with the name of the speaker (Incase the message format chosen requires the name be on the end for some reason, but it's optional to include the name in the end message)
        """Returns the end of a message with the name of the speaker (Incase the message format chosen requires the name be on the end for some reason, but it's optional to include the name in the end message)"""
        return self.message_formatter.end_message(role, name)

    def get_string_from_messages(self, messages): # Returns a formatted string from a list of messages
        """Returns a formatted string from a list of messages"""
        return self.message_formatter.get_string_from_messages(messages)

    def num_tokens_from_messages(self, messages): # Returns the number of tokens used by a list of messages
        """Returns the number of tokens used by a list of messages"""
        context, _images = self.get_string_from_messages(messages)
        context += self.start_message("assistant") # Simulate the assistant replying to add a little more to the token count to be safe (this is a bit of a hack, but it should work 99% of the time I think) TODO: Determine if needed
        return self.get_token_count(context)
    
    def get_token_count_of_message(self, message): # Returns the number of tokens in a message
        """Returns the number of tokens in a message"""
        if "name" not in message:
            message["name"] = None
        return self.get_token_count(self.new_message(message["content"], message["role"], message["name"]))
        
    def get_token_count(self, string):
        """Returns the number of tokens in a string"""
        # logging.info(f"base_Tokenizer.get_token_count() called with string: {string}")
        logging.info(f"You should override this method in your tokenizer class! Please do so! I'm going to crash until you do actually, just to encourage you to do so! <3")
        input("Press enter to continue...")
        raise NotImplementedError("You should override this method in your tokenizer class! Please do so! I'm going to crash until you do actually, just to encourage you to do so! <3")