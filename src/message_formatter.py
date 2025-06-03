from pydantic import BaseModel
import json
from typing import Optional, Union

class MessageRole(BaseModel):
    role_name: str = "assistant"
    role_prefix_insert: str = "<|assistant_id|>"
    role_suffix_insert: str = "<|eot_id|>"

class PromptStyle(BaseModel):
    stop: list[str] = ["<|eot_id|>","<|end_header_id|>"]
    banned_chars: list[str] = ["{", "}", "\"" ]
    end_of_sentence_chars: list[str] = [".", "?", "!"]
    BOS_token: str = "<|start_header_id|>"
    EOS_token: str = "<|eot_id|>"
    message_signifier: str = ": "
    role_seperator: str = "<|end_header_id|>\n\n"
    message_seperator: str = ""
    message_format: str = "[BOS_token][role_prefix_insert][role_seperator][name][message_signifier][content][role_suffix_insert][EOS_token][message_seperator]"
    chat_format: str = "[messages]"
    # system_name: str = "system"
    # user_name: str = "user"
    # assistant_name: str = "assistant"
    # system_EOS_token: str = ""
    # user_EOS_token: str = ""
    # assistant_EOS_token: str = ""
    message_roles: list[MessageRole] = [
        MessageRole(role_name="system", role_prefix_insert="system", role_suffix_insert=""),
        MessageRole(role_name="user", role_prefix_insert="user", role_suffix_insert=""),
        MessageRole(role_name="assistant", role_prefix_insert="assistant", role_suffix_insert="")
    ]

class MessageTextContent(BaseModel):
    type: str = "text"
    text: Optional[str]

class ImageUrl(BaseModel):
    url: str

class MessageImageURLContent(BaseModel):
    type: str = "image_url"
    url: Optional[str]
    image_url: Optional[ImageUrl]

class MessageImageBase64Content(BaseModel):
    type: str = "image"
    base64: Optional[str]

class Message(BaseModel):
    role: str
    content: Union[str, list[dict]] # Union[MessageTextContent, MessageImageURLContent, MessageImageBase64Content]
    name: Optional[str] = ""

class MessageFormatter(): # Tokenizes(only availble for counting the tokens in a string presently for local_models), and parses and formats messages for use with the language model
    def __init__(self, prompt_style: Optional[PromptStyle] = None): # Initializes the message formatter with a prompt style
        if prompt_style == None:
            ps = PromptStyle()
        else:
            ps = prompt_style
        self._prompt_style = ps
        self.stop = ps.stop
        self.banned_chars = ps.banned_chars
        self.end_of_sentence_chars = ps.end_of_sentence_chars
        self.BOS_token = ps.BOS_token
        self.EOS_token = ps.EOS_token
        self.message_signifier = ps.message_signifier
        self.role_seperator = ps.role_seperator
        self.message_seperator = ps.message_seperator
        self.message_format = ps.message_format
        self.chat_format = ps.chat_format
        self.message_roles = ps.message_roles

    def _version(self): # Returns the version of the message formatter
        """Returns the version of the message formatter"""
        return "0.0.5"
    
    def get_role_prefix(self, role: str) -> str: # Returns the prefix for a role
        """Returns the prefix for a role"""
        for message_role in self.message_roles:
            if message_role.role_name == role:
                return message_role.role_prefix_insert
        raise ValueError(f"Role '{role}' not found in message roles:", self.message_roles)
    
    def get_role_suffix(self, role: str) -> str: # Returns the suffix for a role
        """Returns the suffix for a role"""
        for message_role in self.message_roles:
            if message_role.role_name == role:
                return message_role.role_suffix_insert
        raise ValueError(f"Role {role} not found in message roles")
        
    def new_message(self, content, role, name=None): # Parses a string into a message format with the name of the speaker
        """Parses a string into a message format with the name of the speaker"""
        if type(name) == str: # If the name is a string, check if it's empty and set it to None if it is
            if name.strip() == "":
                name = None
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
        parsed_msg_part = parsed_msg_part.replace("[role_prefix_insert]",self.get_role_prefix(role))
        parsed_msg_part = parsed_msg_part.replace("[role_seperator]",role_sep)
        parsed_msg_part = parsed_msg_part.replace("[name]",name)
        parsed_msg_part = parsed_msg_part.replace("[message_signifier]",msg_sig)
        parsed_msg_part = parsed_msg_part.replace("[role_suffix_insert]",self.get_role_suffix(role))
        parsed_msg_part = parsed_msg_part.replace("[EOS_token]",self.EOS_token)
        parsed_msg_part = parsed_msg_part.replace("[message_seperator]",self.message_seperator)
        parsed_msg_part = parsed_msg_part.split("[content]")[0]
        print(f"Parsed message first part: {parsed_msg_part}")
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
        parsed_msg_part = parsed_msg_part.replace("[role_prefix_insert]",self.get_role_prefix(role))
        parsed_msg_part = parsed_msg_part.replace("[role_seperator]",role_sep)
        parsed_msg_part = parsed_msg_part.replace("[name]",name)
        parsed_msg_part = parsed_msg_part.replace("[message_signifier]",msg_sig)
        parsed_msg_part = parsed_msg_part.replace("[role_suffix_insert]",self.get_role_suffix(role))
        parsed_msg_part = parsed_msg_part.replace("[EOS_token]",self.EOS_token)
        parsed_msg_part = parsed_msg_part.replace("[message_seperator]",self.message_seperator)
        parsed_msg_part = parsed_msg_part.split("[content]")[1]
        print(f"Parsed message second part: {parsed_msg_part}")
        return parsed_msg_part

    def get_string_from_messages(self, messages: list[Message]): # Returns a formatted string from a list of messages
        """Returns a formatted string from a list of messages"""
        print(f"Using message format: {self.message_format}")
        context = f"{self.chat_format}"
        images = []
        print(f"Creating string from messages: {len(messages)}")
        messages_context = ""
        for message in messages:
            if type(message) == str:
                message = json.loads(message)
            if type(message) == dict:
                message = Message(**message)
            if not isinstance(message, Message):
                raise TypeError(f"Message must be of type Message, dict that can be parsed to a Message object or a str that can be loaded as a dict to parse into a Message object, got {type(message)}")
            if type(message.content) == str:
                content = message.content
            else:
                content = ""
                for content_item in message.content:
                    if content_item["type"] == "text":
                        content += content_item["text"]
                    elif content_item["type"] == "image_url":
                        content += "{image}"
                        images.append(content_item)
                    elif content_item["type"] == "image":
                        content += "{image}"
                        images.append(content_item)
            if "role" in message:
                role = message["role"]
            else:
                try:
                    role = message.role
                except:
                    raise ValueError("Message does not have 'role' key!")
            if "name" in message:
                name = message["name"]
            else:
                try:
                    name = message.name
                except:
                    name = None
            msg_string = self.new_message(content, role, name)
            messages_context += msg_string
        context = context.replace("[messages]", messages_context)
        print(f"Context:")
        print(context)
        return context, images
    
    def __str__(self):
        return json.dumps(self._prompt_style.model_dump(), indent=4)