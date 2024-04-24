from src.logging import logging
tokenizer_slug = "base_tokenizer"
class base_Tokenizer(): # Tokenizes(only availble for counting the tokens in a string presently for local_models), and parses and formats messages for use with the language model
    def __init__(self, conversation_manager):
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config
        self.tokenizer_slug = tokenizer_slug # Fastest tokenizer for OpenAI models, change if you want to use a different tokenizer (use 'embedding' for compatibility with any model using the openai API)
        # Prommpt Parsing Stuff
        # self.BOS_token = self.config.BOS_token # Beginning of string token
        # self.EOS_token = self.config.EOS_token # End of string token
        # self.role_seperator = self.config.role_seperator # Seperates the role from the name
        # self.message_signifier = self.config.message_signifier # Signifies the start of a message
        # self.message_seperator = self.config.message_seperator # Seperates messages
        # self.message_format = self.config.message_format # Format of a message. A string of messages formatted like this is what is sent to the language model, typically following by the start of a message from the assistant to generate a response

    @property
    def BOS_token(self):
        return self.config.BOS_token

    @property
    def EOS_token(self):
        return self.config.EOS_token

    @property
    def role_seperator(self):
        return self.config.role_seperator
    
    @property
    def message_signifier(self):
        return self.config.message_signifier
    
    @property
    def message_seperator(self):
        return self.config.message_seperator
    
    @property
    def message_format(self):
        return self.config.message_format

    def new_message(self, content, role, name=None): # Parses a string into a message format with the name of the speaker
        """Parses a string into a message format with the name of the speaker"""
        parsed_msg = self.start_message(role, name)
        if content.strip() == "":
            return ""
        parsed_msg += content
        parsed_msg += self.end_message(role, name)
        return parsed_msg

    def start_message(self, role="", name=None): # Returns the start of a message with the name of the speaker
        """Returns the start of a message with the name of the speaker"""
        parsed_msg_part = self.message_format
        msg_sig = self.message_signifier
        if not name:
            name = ""
            msg_sig = ""
        role_sep = self.role_seperator
        if role == "":
            role_sep = ""
            
        if name == "":
            parsed_msg_part = parsed_msg_part.split("[message_signifier]")[0]
        if role == "":
            parsed_msg_part = parsed_msg_part.split("[role_seperator]")[0]
        parsed_msg_part = parsed_msg_part.replace("[BOS_token]",self.BOS_token)
        parsed_msg_part = parsed_msg_part.replace("[role]",role)
        parsed_msg_part = parsed_msg_part.replace("[role_seperator]",role_sep)
        parsed_msg_part = parsed_msg_part.replace("[name]",name)
        parsed_msg_part = parsed_msg_part.replace("[message_signifier]",msg_sig)
        parsed_msg_part = parsed_msg_part.replace("[EOS_token]",self.EOS_token)
        parsed_msg_part = parsed_msg_part.replace("[message_seperator]",self.message_seperator)
        parsed_msg_part = parsed_msg_part.split("[content]")[0]
        return parsed_msg_part

    def end_message(self, role="", name=None): # Returns the end of a message with the name of the speaker (Incase the message format chosen requires the name be on the end for some reason, but it's optional to include the name in the end message)
        """Returns the end of a message with the name of the speaker (Incase the message format chosen requires the name be on the end for some reason, but it's optional to include the name in the end message)"""
        parsed_msg_part = self.message_format
        msg_sig = self.message_signifier
        if not name:
            name = ""
            msg_sig = ""
        role_sep = self.role_seperator
        if role == "":
            role_sep = ""
        if name == "":
            parsed_msg_part = parsed_msg_part.split("[message_signifier]")[1]
        if role == "":
            parsed_msg_part = parsed_msg_part.split("[role_seperator]")[1]
        parsed_msg_part = parsed_msg_part.replace("[BOS_token]",self.BOS_token)
        parsed_msg_part = parsed_msg_part.replace("[role]",role)
        parsed_msg_part = parsed_msg_part.replace("[role_seperator]",role_sep)
        parsed_msg_part = parsed_msg_part.replace("[name]",name)
        parsed_msg_part = parsed_msg_part.replace("[message_signifier]",msg_sig)
        parsed_msg_part = parsed_msg_part.replace("[EOS_token]",self.EOS_token)
        parsed_msg_part = parsed_msg_part.replace("[message_seperator]",self.message_seperator)
        parsed_msg_part = parsed_msg_part.split("[content]")[1]
        return parsed_msg_part

    def get_string_from_messages(self, messages): # Returns a formatted string from a list of messages
        """Returns a formatted string from a list of messages"""
        context = ""
        logging.info(f"Creating string from messages: {len(messages)}")
        for message in messages:
            logging.info(f"Message:",message)
            if "content" in message:
                content = message["content"]
            else:
                raise ValueError("Message does not have 'content' key!")
            if "role" in message:
                role = message["role"]
            else:
                raise ValueError("Message does not have 'role' key!")
            if "name" in message:
                name = message["name"]
            else:
                name = None
            msg_string = self.new_message(content, role, name)
            context += msg_string
        return context

    def num_tokens_from_messages(self, messages): # Returns the number of tokens used by a list of messages
        """Returns the number of tokens used by a list of messages"""
        context = self.get_string_from_messages(messages)
        context += self.start_message(self.config.assistant_name) # Simulate the assistant replying to add a little more to the token count to be safe (this is a bit of a hack, but it should work 99% of the time I think) TODO: Determine if needed
        return self.get_token_count(context)
        
    def get_token_count(self, string):
        """Returns the number of tokens in a string"""
        # logging.info(f"base_Tokenizer.get_token_count() called with string: {string}")
        logging.info(f"You should override this method in your tokenizer class! Please do so! I'm going to crash until you do actually, just to encourage you to do so! <3")
        input("Press enter to continue...")
        raise NotImplementedError("You should override this method in your tokenizer class! Please do so! I'm going to crash until you do actually, just to encourage you to do so! <3")