import tiktoken
import time
import src.utils as utils
import logging

class Tokenizer(): # Tokenizes(only availble for counting the tokens in a string presently for local_models), and parses and formats messages for use with the language model
    def __init__(self,config, client):
        self.encoding = None
        self.config = config
        self.client = client
        if not self.config.is_local: # If we're using OpenAI, we can use the tiktoken library to get the number of tokens used by the prompt
            self.encoding = tiktoken.encoding_for_model(config.llm)
            
        self.BOS_token = self.config.BOS_token
        self.EOS_token = self.config.EOS_token
        self.message_signifier = config.message_signifier
        self.message_seperator = config.message_seperator
        self.message_format = config.message_format

    def named_parse(self, msg, name): # Parses a string into a message format with the name of the speaker
        if not name:
            name = "[name]"
        if not msg:
            return self.start_message(name) + self.end_message(name)
        parsed_msg = self.message_format
        parsed_msg = parsed_msg.replace("[BOS_token]",self.BOS_token)
        parsed_msg = parsed_msg.replace("[name]",name)
        parsed_msg = parsed_msg.replace("[message_signifier]",self.message_signifier)
        parsed_msg = parsed_msg.replace("[content]",msg)
        parsed_msg = parsed_msg.replace("[EOS_token]",self.EOS_token)
        parsed_msg = parsed_msg.replace("[message_seperator]",self.message_seperator)
        return parsed_msg

    def start_message(self, name): # Returns the start of a message with the name of the speaker
        parsed_msg = self.message_format
        parsed_msg = parsed_msg.split("[content]")[0]
        parsed_msg = parsed_msg.replace("[BOS_token]",self.BOS_token)
        parsed_msg = parsed_msg.replace("[name]",name)
        parsed_msg = parsed_msg.replace("[message_signifier]",self.message_signifier)
        parsed_msg = parsed_msg.replace("[EOS_token]",self.EOS_token)
        parsed_msg = parsed_msg.replace("[message_seperator]",self.message_seperator)
        return parsed_msg

    def end_message(self, name=""): # Returns the end of a message with the name of the speaker (Incase the message format chosen requires the name be on the end for some reason, but it's optional to include the name in the end message)
        parsed_msg = self.message_format
        parsed_msg = parsed_msg.split("[content]")[1]
        parsed_msg = parsed_msg.replace("[BOS_token]",self.BOS_token)
        parsed_msg = parsed_msg.replace("[name]",name)
        parsed_msg = parsed_msg.replace("[message_signifier]",self.message_signifier)
        parsed_msg = parsed_msg.replace("[EOS_token]",self.EOS_token)
        parsed_msg = parsed_msg.replace("[message_seperator]",self.message_seperator)
        return parsed_msg

    def get_string_from_messages(self, messages): # Returns a formatted string from a list of messages
        context = ""
        for message in messages:
            context += self.named_parse(message["content"],message["role"])
        return context

    def num_tokens_from_messages(self, messages): # Returns the number of tokens used by a list of messages
        """Returns the number of tokens used by a list of messages"""
        context = self.get_string_from_messages(messages)
        context += self.start_message(self.config.assistant_name) # Simulate the assistant replying to add a little more to the token count to be safe (this is a bit of a hack, but it should work 99% of the time I think) TODO: Determine if needed
        return self.get_token_count(context)
        
    def get_token_count(self, string):
        if self.config.is_local: # If we're using the api, we can just ask it how many tokens it used by looking at the prompt_tokens usage via an embedding call
            embedding = self.client.embeddings.create(
                model=self.config.llm,
                input=string
            )
            num_tokens = int(embedding.usage.prompt_tokens)
        else: # If we're using OpenAI, we can use the tiktoken library to get the number of tokens used by the prompt
            tokens = self.encoding.encode(string)
            num_tokens = len(tokens)
        return num_tokens

class LLM():
    def __init__(self, config, client, tokenizer, token_limit, language_info):
        self.config = config
        self.client = client
        self.tokenizer = tokenizer
        self.token_limit = token_limit
        self.language_info = language_info
    
    @utils.time_it
    def chatgpt_api(self, input_text, messages):
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
    
    def create(self, messages):
        print(f"cMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                prompt = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message(self.config.assistant_name) # Start empty message from no one to let the LLM generate the speaker by split \n
                completion = self.client.completions.create(
                    model=self.config.llm, prompt=prompt, max_tokens=self.config.max_tokens
                )
                completion = completion.choices[0].text
                print(f"Prompt: {prompt}")
                print(f"Completion:",completion)
            except Exception as e:
                logging.warning('Could not connect to LLM API, retrying in 5 seconds...')
                logging.warning(e)
                print(e)
                if retries == 1:
                    logging.error('Could not connect to LLM API after 5 retries, exiting...')
                    input('Press enter to continue...')
                    exit()
                time.sleep(5)
                retries -= 1
                continue
            break
        return completion
    
    def acreate(self, messages): # Creates a completion stream for the messages provided to generate a speaker and their response
        # print(f"Messages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                prompt = self.tokenizer.get_string_from_messages(messages)
                prompt += self.tokenizer.start_message("[name]") # Start empty message from no one to let the LLM generate the speaker by split \n
                prompt = prompt.split("[name]")[0] # Start message without the name - Generates name for use in output_manager.py  process_response()
                logging.info(f"Raw Prompt: {prompt}")
                return self.client.completions.create(
                    model=self.config.llm, prompt=prompt, max_tokens=self.config.max_tokens, stream=True # , stop=self.stop, temperature=self.temperature, top_p=self.top_p, frequency_penalty=self.frequency_penalty, stream=True
                )
            except Exception as e:
                logging.warning('Could not connect to LLM API, retrying in 5 seconds...')
                logging.warning(e)
                print(e)
                if retries == 1:
                    logging.error('Could not connect to LLM API after 5 retries, exiting...')
                    input('Press enter to continue...')
                    exit()
                time.sleep(5)
                retries -= 1
                continue
