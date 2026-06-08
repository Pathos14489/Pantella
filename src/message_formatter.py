from pydantic import BaseModel
import json
from typing import Optional, Union

class MessageRole(BaseModel):
    role_name: str = "assistant"
    role_prefix_insert: str = "<|assistant_id|>"
    role_suffix_insert: str = "<|eot_id|>"

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
    reasoning: Optional[str] = ""
    name: Optional[str] = ""

class HardcodedMessage(Message):
    insertion_index: int = 0
    insertion_direction: str = "start" # "start" or "end"

class PromptStyle(BaseModel):
    stop: list[str] = ["<|eot_id|>","<|end_header_id|>"]
    BOS_token: str = "<|start_header_id|>"
    EOS_token: str = "<|eot_id|>"
    message_signifier: str = ": "
    role_seperator: str = "<|end_header_id|>\n\n"
    message_seperator: str = ""
    message_format: str = "[BOS_token][role_prefix_insert][role_seperator][name][message_signifier][content][role_suffix_insert][EOS_token][message_seperator]"
    chat_format: str = "[messages]"
    thinking: bool = False
    keep_empty_thoughts: bool = True
    start_thinking_token: str = "<think>"
    end_thinking_token: str = "</think>"
    thinking_token_prefix: str = ""
    thinking_token_suffix: str = "\n\n"
    thinking_prefill: Optional[str] = ""
    thinking_stops: list[str] = []
    no_think_empty_thoughts: bool = False
    # thinking_style: dict = {
    #     "enabled": True,
    #     "start_token": "<thinking>",
    #     "end_token": "</thinking>"
    # }
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
    hardcoded_messages: list[HardcodedMessage] = []

class MessageFormatter(): # Tokenizes(only availble for counting the tokens in a string presently for local_models), and parses and formats messages for use with the language model
    def __init__(self, prompt_style: Optional[PromptStyle] = None): # Initializes the message formatter with a prompt style
        if prompt_style == None:
            ps = PromptStyle()
        else:
            ps = prompt_style
        self._prompt_style = ps
        self.stop = ps.stop
        self.BOS_token = ps.BOS_token
        self.EOS_token = ps.EOS_token
        self.message_signifier = ps.message_signifier
        self.role_seperator = ps.role_seperator
        self.message_seperator = ps.message_seperator
        self.message_format = ps.message_format
        self.chat_format = ps.chat_format
        self.thinking = ps.thinking
        self.keep_empty_thoughts = ps.keep_empty_thoughts
        self.start_thinking_token = ps.start_thinking_token
        self.end_thinking_token = ps.end_thinking_token
        self.thinking_token_prefix = ps.thinking_token_prefix
        self.thinking_token_suffix = ps.thinking_token_suffix
        self.thinking_prefill = ps.thinking_prefill
        self.thinking_stops = ps.thinking_stops
        self.no_think_empty_thoughts = ps.no_think_empty_thoughts
        self.message_roles = ps.message_roles
        self.hardcoded_messages = ps.hardcoded_messages

    def _version(self): # Returns the version of the message formatter
        """Returns the version of the message formatter"""
        return "0.0.13"
    
    def get_role_prefix(self, role: str) -> str: # Returns the prefix for a role
        """Returns the prefix for a role"""
        if role == "":
            return ""
        for message_role in self.message_roles:
            if message_role.role_name == role:
                return message_role.role_prefix_insert
        raise ValueError(f"Role '{role}' not found in message roles:", self.message_roles)
    
    def get_role_suffix(self, role: str) -> str: # Returns the suffix for a role
        """Returns the suffix for a role"""
        if role == "":
            return ""
        for message_role in self.message_roles:
            if message_role.role_name == role:
                return message_role.role_suffix_insert
        raise ValueError(f"Role {role} not found in message roles")
        
    def new_message(self, content, role, reasoning="", name=None, thinking=False): # Parses a string into a message format with the name of the speaker
        """Parses a string into a message format with the name of the speaker"""
        # if type(name) == str: # If the name is a string, check if it's empty and set it to None if it is
        #     if name.strip() == "":
        #         name = None
        # parsed_msg = self.start_message(role, name, thinking)
        # if content.strip() == "":
        #     return ""
        # parsed_msg += content
        # parsed_msg += self.end_message(role, name, thinking)
        parsed_msg = self.message_format
        msg_sig = self.message_signifier
        if not name:
            name = ""
            msg_sig = ""
        role_sep = self.role_seperator
        if role == "":
            role_sep = ""

        parsed_msg = parsed_msg.replace("[BOS_token]",self.BOS_token)
            
        if role == "":
            parsed_msg = parsed_msg.split("[role_seperator]")[0]
        else:
            parsed_msg = parsed_msg.replace("[role_seperator]",role_sep)

        if name == "":
            parsed_msg = parsed_msg.replace("[name]", "")
            parsed_msg = parsed_msg.replace("[message_signifier]", "")
        else:
            parsed_msg = parsed_msg.replace("[name]", name)
            parsed_msg = parsed_msg.replace("[message_signifier]", msg_sig)

        parsed_msg = parsed_msg.replace("[role_prefix_insert]",self.get_role_prefix(role))
        parsed_msg = parsed_msg.replace("[name]",name)
        parsed_msg = parsed_msg.replace("[message_signifier]",msg_sig)
        # If thinking is enabled, add the thinking start and end tokens
        if self.thinking and thinking and role == "assistant" and (reasoning.strip() != "" or self.keep_empty_thoughts):
            parsed_msg = parsed_msg.replace("[start_thinking_token]", self.start_thinking_token)
            parsed_msg = parsed_msg.replace("[end_thinking_token]", self.end_thinking_token)
            parsed_msg = parsed_msg.replace("[thinking_token_prefix]", self.thinking_token_prefix)
            parsed_msg = parsed_msg.replace("[thinking_token_suffix]", self.thinking_token_suffix)
        else:
            parsed_msg = parsed_msg.replace("[start_thinking_token]", "")
            parsed_msg = parsed_msg.replace("[end_thinking_token]", "")
            parsed_msg = parsed_msg.replace("[thinking_token_prefix]", "")
            parsed_msg = parsed_msg.replace("[thinking_token_suffix]", "")

        parsed_msg = parsed_msg.replace("[role_suffix_insert]",self.get_role_suffix(role))
        parsed_msg = parsed_msg.replace("[EOS_token]",self.EOS_token)
        parsed_msg = parsed_msg.replace("[message_seperator]",self.message_seperator)
        if self.thinking and thinking and role == "assistant":
            parsed_msg = parsed_msg.replace("[thought_content]", reasoning)
        else:
            parsed_msg = parsed_msg.replace("[thought_content]", "")
        parsed_msg = parsed_msg.replace("[content]", content)
        print(f"Parsed message part: {parsed_msg}")
        return parsed_msg

    def start_message(self, role="", name=None, thinking=False): # Returns the start of a message with the name of the speaker
        """Returns the start of a message with the name of the speaker"""
        parsed_msg_part = self.message_format
        msg_sig = self.message_signifier
        if not name:
            name = ""
            msg_sig = ""
        role_sep = self.role_seperator
        if role == "":
            role_sep = ""

        parsed_msg_part = parsed_msg_part.replace("[BOS_token]",self.BOS_token)
            
        if role == "":
            parsed_msg_part = parsed_msg_part.split("[role_seperator]")[0]
        else:
            parsed_msg_part = parsed_msg_part.replace("[role_seperator]",role_sep)

        if name == "":
            parsed_msg_part = parsed_msg_part.replace("[name]", "")
            parsed_msg_part = parsed_msg_part.replace("[message_signifier]", "")
        else:
            parsed_msg_part = parsed_msg_part.replace("[name]", name)
            parsed_msg_part = parsed_msg_part.replace("[message_signifier]", msg_sig)

        parsed_msg_part = parsed_msg_part.replace("[role_prefix_insert]",self.get_role_prefix(role))
        parsed_msg_part = parsed_msg_part.replace("[name]",name)
        parsed_msg_part = parsed_msg_part.replace("[message_signifier]",msg_sig)
        # If thinking is enabled, add the thinking start and end tokens
        if ((self.thinking and thinking) or self.no_think_empty_thoughts) and role == "assistant":
            parsed_msg_part = parsed_msg_part.replace("[start_thinking_token]", self.start_thinking_token)
            parsed_msg_part = parsed_msg_part.replace("[end_thinking_token]", self.end_thinking_token)
            parsed_msg_part = parsed_msg_part.replace("[thinking_token_prefix]", self.thinking_token_prefix)
            parsed_msg_part = parsed_msg_part.replace("[thinking_token_suffix]", self.thinking_token_suffix)
        else:
            parsed_msg_part = parsed_msg_part.replace("[start_thinking_token]", "")
            parsed_msg_part = parsed_msg_part.replace("[end_thinking_token]", "")
            parsed_msg_part = parsed_msg_part.replace("[thinking_token_prefix]", "")
            parsed_msg_part = parsed_msg_part.replace("[thinking_token_suffix]", "")

        parsed_msg_part = parsed_msg_part.replace("[role_suffix_insert]",self.get_role_suffix(role))
        parsed_msg_part = parsed_msg_part.replace("[EOS_token]",self.EOS_token)
        parsed_msg_part = parsed_msg_part.replace("[message_seperator]",self.message_seperator)
        if self.thinking and thinking and role == "assistant":
            parsed_msg_part = parsed_msg_part.split("[thought_content]")[0]
        else:
            parsed_msg_part = parsed_msg_part.replace("[thought_content]", "")
            parsed_msg_part = parsed_msg_part.split("[content]")[0]
        print(f"Parsed message first part: {parsed_msg_part}")
        return parsed_msg_part

    def end_message(self, role="", name=None, thinking=False): # Returns the end of a message with the name of the speaker (Incase the message format chosen requires the name be on the end for some reason, but it's optional to include the name in the end message)
        """Returns the end of a message with the name of the speaker (Incase the message format chosen requires the name be on the end for some reason, but it's optional to include the name in the end message)"""
        parsed_msg_part = self.message_format
        msg_sig = self.message_signifier
        if not name:
            name = ""
            msg_sig = ""
        role_sep = self.role_seperator
        if role == "":
            role_sep = ""

        parsed_msg_part = parsed_msg_part.replace("[BOS_token]",self.BOS_token)
            
        if role == "":
            parsed_msg_part = parsed_msg_part.split("[role_seperator]")[1]
        else:
            parsed_msg_part = parsed_msg_part.replace("[role_seperator]",role_sep)

        if name == "":
            parsed_msg_part = parsed_msg_part.replace("[name]", "")
            parsed_msg_part = parsed_msg_part.replace("[message_signifier]", "")
        else:
            parsed_msg_part = parsed_msg_part.replace("[name]", name)
            parsed_msg_part = parsed_msg_part.replace("[message_signifier]", msg_sig)

        parsed_msg_part = parsed_msg_part.replace("[role_prefix_insert]",self.get_role_prefix(role))
        parsed_msg_part = parsed_msg_part.replace("[name]",name)
        parsed_msg_part = parsed_msg_part.replace("[message_signifier]",msg_sig)
        # If thinking is enabled, add the thinking start and end tokens
        if self.thinking and thinking and role == "assistant":
            parsed_msg_part = parsed_msg_part.replace("[start_thinking_token]", self.start_thinking_token)
            parsed_msg_part = parsed_msg_part.replace("[end_thinking_token]", self.end_thinking_token)
            parsed_msg_part = parsed_msg_part.replace("[thinking_token_prefix]", self.thinking_token_prefix)
            parsed_msg_part = parsed_msg_part.replace("[thinking_token_suffix]", self.thinking_token_suffix)
        else:
            parsed_msg_part = parsed_msg_part.replace("[start_thinking_token]", "")
            parsed_msg_part = parsed_msg_part.replace("[end_thinking_token]", "")
            parsed_msg_part = parsed_msg_part.replace("[thinking_token_prefix]", "")
            parsed_msg_part = parsed_msg_part.replace("[thinking_token_suffix]", "")

        parsed_msg_part = parsed_msg_part.replace("[role_suffix_insert]",self.get_role_suffix(role))
        parsed_msg_part = parsed_msg_part.replace("[EOS_token]",self.EOS_token)
        parsed_msg_part = parsed_msg_part.replace("[message_seperator]",self.message_seperator)
        if self.thinking and thinking and role == "assistant":
            parsed_msg_part = parsed_msg_part.split("[thought_content]")[1]
        else:
            parsed_msg_part = parsed_msg_part.replace("[thought_content]", "")
        parsed_msg_part = parsed_msg_part.split("[content]")[1]
        print(f"Parsed message second part: {parsed_msg_part}")
        return parsed_msg_part

    def get_string_from_messages(self, messages: list[Message], thinking: bool = False, start_message: bool = False, response_type: str = "assistant"): # Returns a formatted string from a list of messages
        """Returns a formatted string from a list of messages"""
        print(f"Using message format: {self.message_format}")
        for hardcoded_message in self.hardcoded_messages:
            if hardcoded_message.insertion_direction == "start":
                messages.insert(hardcoded_message.insertion_index, hardcoded_message)
            elif hardcoded_message.insertion_direction == "end":
                messages.insert(len(messages) - hardcoded_message.insertion_index, hardcoded_message)
            else:
                raise ValueError(f"Invalid insertion direction for hardcoded message: {hardcoded_message.insertion_direction}")
        context = f"{self.chat_format}"
        print(f"Creating string from messages: {len(messages)}")
        messages_context = ""
        for message in messages:
            # print(f"Message:",message)
            # if "content" in message:
            #     content = message["content"]
            # else:
            #     try:
            #         content = message.content
            #     except:
            #         raise ValueError("Message does not have 'content' key!")
            if type(message) == dict:
                message = Message(
                    role=message["role"],
                    content=message["content"],
                    reasoning=message.get("reasoning", ""),
                    name=message.get("name", "")
                )
            try:
                if type(message.content) == str:
                    content = message.content
                else:
                    content = ""
                    for content_item in message.content:
                        if content_item["type"] == "text":
                            content += content_item["text"]
            except:
                raise ValueError("Message does not have 'content' key!", message)
            if type(message.reasoning) == str:
                reasoning = message.reasoning
            else:
                reasoning = ""
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
            msg_string = self.new_message(content, role, reasoning, name, thinking)
            messages_context += msg_string
        context = context.replace("[messages]", messages_context)
        # print(f"Context:")
        # print(context)
        if start_message:
            context += self.start_message(role=response_type, thinking=thinking)
        return context
    
    def __str__(self):
        return json.dumps(self._prompt_style.model_dump(), indent=4)