print("Importing openai_api_CoT.py")
from src.logging import logging, time
import src.utils as utils
from src.llms.openai_api import LLM
import random
import traceback
import os
import json
import re
import unicodedata
import time
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
logging.info("Imported required libraries in openai_api_CoT.py")

inference_engine_name = "openai_cot"

def get_schema_description(schema):
    schema_description = ""
    print("Schema:", schema)
    if "description" in schema and schema["description"] is not None:
        schema_description += schema["description"]
    for key in schema["properties"]:
        def parse_property(property,schema_description):
            if type(property) == dict:
                if "title" in property and property["title"] is not None:
                    description_part = property["title"] + ": "
                else:
                    description_part = ""
                add_to_description = False
                if "description" in property and property["description"] is not None and "title" in property and property["title"] is not None:
                    description_part += property["description"]
                    add_to_description = True
                if "examples" in property and property["examples"] is not None:
                    description_part += "\nExamples: " + ", ".join(property["examples"])
                    add_to_description = True
                if "$ref" in property:
                    reference = schema["$defs"][property["$ref"].split("/")[-1]]
                    if "title" in reference and reference["title"] is not None:
                        description_part += reference["title"] + ": "
                        add_to_description = True   
                    if "description" in reference and reference["description"] is not None:
                        description_part += reference["description"]
                        add_to_description = True
                    if "examples" in reference and reference["examples"] is not None:
                        description_part += "\nExamples: " + ", ".join(reference["examples"])
                        add_to_description = True
                    if "properties" in reference and reference["properties"] is not None:
                        for sub_key in reference["properties"]:
                            print("Sub Key:", sub_key)
                            description_part = parse_property(reference["properties"][sub_key],description_part)
                            add_to_description = True
                if "items" in property and property["items"] is not None:
                    if "$ref" in property["items"]:
                        reference = schema["$defs"][property["items"]["$ref"].split("/")[-1]]
                        # if "title" in reference and reference["title"] is not None:
                        #     description_part += "\n" + reference["title"] + ": "
                        if "description" in reference and reference["description"] is not None:
                            description_part += reference["description"]
                            add_to_description = True
                        if "examples" in reference and reference["examples"] is not None:
                            description_part += "\nExamples: " + ", ".join(reference["examples"])
                            add_to_description = True
                        if "properties" in reference and reference["properties"] is not None:
                            for sub_key in reference["properties"]:
                                print("Sub Key:", sub_key)
                                description_part = parse_property(reference["properties"][sub_key],description_part)
                                add_to_description = True
                if "properties" in property and property["properties"] is not None:
                    for sub_key in property["properties"]:
                        print("Sub Key:", sub_key)
                        description_part = parse_property(property["properties"][sub_key],description_part)
                        add_to_description = True
                if add_to_description:
                    schema_description += "\n" + description_part
            return schema_description
        print("Key:", key)
        # print("Value:", character_card_schema[key])
        schema_description = parse_property(schema["properties"][key],schema_description)
    return schema_description

class LLM(LLM):
    def __init__(self, conversation_manager, vision_enabled=False):
        global inference_engine_name
        super().__init__(conversation_manager, vision_enabled=vision_enabled)
    
    def format_content(self, chunk):
        # TODO: This is a temporary fix. The LLM class should be returning a string only, but some inference engines don't currently. This will be fixed in the future.
        # logging.info(f"Formatting content type: {type(chunk)}")
        # logging.info(chunk)
        if type(chunk) == dict:
            # logging.info(chunk)
            try:
                content = chunk['choices'][0]['text']
            except:
                try:
                    content = chunk.choices[0].text
                except:
                    logging.error("Could not get text from chunk.")
        elif type(chunk) == str:
            # logging.info(chunk)
            content = chunk
        else:
            # logging.debug(chunk.model_dump_json())
            content = None
            error = "Errors getting text from chunk:\n"
            if content is None:
                try:
                    content = chunk.choices[0].text
                except Exception as e:
                    # logging.debug("Error getting text from chunk - 1")
                    # logging.debug(e)
                    error += str(e) + "\n"
                    pass
            if content is None:
                try:
                    content = chunk.choices[0].content
                except Exception as e:
                    # logging.debug("Error getting text from chunk - 2")
                    # logging.debug(e)
                    error += str(e) + "\n"
                    pass
            if content is None:
                try:
                    content = chunk.choices[0]["text"]
                except Exception as e:
                    # logging.debug("Error getting text from chunk - 2")
                    # logging.debug(e)
                    error += str(e) + "\n"
                    pass
            if content is None:
                try:
                    content = chunk.choices[0]["content"]
                except Exception as e:
                    # logging.debug("Error getting text from chunk - 2")
                    # logging.debug(e)
                    error += str(e) + "\n"
                    pass
            if content is None:
                try:
                    content = chunk.choices[0].delta.text
                except Exception as e:
                    # logging.debug("Error getting text from chunk - 2")
                    # logging.debug(e)
                    error += str(e) + "\n"
                    pass
            if content is None:
                try:
                    content = chunk.choices[0].delta["text"]
                except Exception as e:
                    # logging.debug("Error getting text from chunk - 2")
                    # logging.debug(e)
                    error += str(e) + "\n"
                    pass
            if content is None:
                try:
                    content = chunk.choices[0].delta.content
                except Exception as e:
                    # logging.debug("Error getting text from chunk - 2")
                    # logging.debug(e)
                    error += str(e) + "\n"
                    pass
            if content is None:
                try:
                    content = chunk.choices[0].delta['content']
                except Exception as e:
                    logging.debug(error + str(e))
                    raise e
        return content
    
    def generate_response(self, message_prefix="", force_speaker=None):
        """Generate response from LLM one text chunk at a time"""
        raw_response = ""
        response_json = {}
        last_diff_json = {}
        for chunk in self.acreate(self.get_context(), message_prefix=message_prefix, force_speaker=force_speaker):
            # logging.info(f"Raw Chunk: {chunk}")
            formatted_chunk = self.format_content(chunk)
            raw_response += formatted_chunk

            special_characters = [
                "{",
                "}",
                "[",
                "]",
            ]
            raw_special_character_list = ""
            for character in raw_response:
                if character in special_characters:
                    raw_special_character_list += character
            
            reflection_characters = list(raw_special_character_list)
            reflection_characters.reverse()
            response_ending = ""
            left_bracket_ignore = 0 
            left_square_bracket_ignore = 0
            for character in reflection_characters:
                if character == "{":
                    if left_bracket_ignore > 0:
                        left_bracket_ignore -= 1
                    else:
                        response_ending = response_ending + "}"
                elif character == "}":
                    left_bracket_ignore += 1
                elif character == "[":
                    if left_square_bracket_ignore > 0:
                        left_square_bracket_ignore -= 1
                    else:
                        response_ending = response_ending + "]"
                elif character == "]":
                    left_square_bracket_ignore += 1

            diff_json = {}

            def parse_list(new_json, orig_json):
                res_json = {}
                for i in range(len(new_json)):
                    if type(new_json[i]) == list and len(new_json[i]) > 0:
                        if i < len(orig_json):
                            if new_json[i] != orig_json[i]:
                                # res_json.append(parse_list(new_json[i], orig_json[i]))
                                res_json[i] = parse_list(new_json[i], orig_json[i])
                        else:
                            # res_json.append(new_json[i])
                            res_json[i] = new_json[i]
                    elif type(new_json[i]) == dict:
                        if i < len(orig_json):
                            if new_json[i] != orig_json[i]:
                                # res_json.append(parse_dict(new_json[i], orig_json[i]))
                                res_json[i] = parse_dict(new_json[i], orig_json[i])
                        else:
                            # res_json.append(new_json[i])
                            # res_json[i] = new_json[i]
                            res_json[i] = {}
                            for key in new_json[i]:
                                if key not in orig_json[i]:
                                    res_json[i][key] = new_json[i][key]
                    else:
                        if i < len(orig_json):
                            if type(new_json[i]) == str:
                                # res_json.append(new_json[i][len(orig_json[i]):])
                                # if res_json[-1] == "":
                                #     res_json.pop()
                                string_new = str(new_json[i])
                                string_orig = str(orig_json[i])
                                string_diff = string_new[len(string_orig):]
                                if string_diff != "":
                                    res_json[i] = string_diff
                            else:
                                string_new = str(new_json[i])
                                string_orig = str(orig_json[i])
                                string_diff = string_new[len(string_orig):]
                                # if string_diff != "":
                                #     res_json.append(type(orig_json[i])(string_diff))
                                # else:
                                #     res_json.append(orig_json[i])
                                if string_diff != "":
                                    res_json[i] = type(orig_json[i])(string_diff)
                        else:
                            # res_json.append(new_json[i])
                            res_json[i] = new_json[i]
                return res_json

            def parse_dict(new_json, orig_json):
                # print("New JSON:",new_json)
                # print("Orig JSON:",orig_json)
                res_json = {}
                for key in new_json:
                    if type(new_json[key]) == list and len(new_json[key]) > 0:
                        if key in orig_json: # key in orig_json
                            if new_json[key] != orig_json[key]:
                                res_json[key] = parse_list(new_json[key], orig_json[key])
                        else: # key not in orig_json
                            res_json[key] = new_json[key]
                    elif type(new_json[key]) == dict: # key is a dictionary
                        if key in orig_json: # key in orig_json
                            if new_json[key] != orig_json[key]:
                                res_json[key] = parse_dict(new_json[key], orig_json[key])
                        else: # key not in orig_json
                            res_json[key] = {}
                            for sub_key in new_json[key]:
                                if key not in orig_json:
                                    res_json[key][sub_key] = new_json[key][sub_key]

                    else:
                        if key in orig_json: # key in orig_json
                            if type(new_json[key]) == str: # key is a string 
                                res_json[key] = new_json[key][len(orig_json[key]):]
                                if res_json[key] == "":
                                    del res_json[key]
                            else: # key is a number
                                string_new = str(new_json[key])
                                string_orig = str(orig_json[key])
                                string_diff = string_new[len(string_orig):]
                                if string_diff != "":
                                    res_json[key] = type(orig_json[key])(string_diff)
                                else:
                                    del res_json[key]
                        else: # key not in orig_json
                            res_json[key] = new_json[key]
                return res_json

            reference_response = str(raw_response).strip()

            if reference_response.endswith(","):
                reference_response = reference_response[:-1]
            try:
                new_response_json = json.loads(reference_response)
            except:
                try:
                    new_response_json = json.loads(reference_response+response_ending)
                except:
                    try:
                        new_response_json = json.loads(reference_response+"\""+response_ending)
                    except:
                        # logging.error(f"Could not parse JSON from response: {reference_response}")
                        # logging.debug(f"Response Ending: {response_ending}")
                        new_response_json = {}
            
            if new_response_json != response_json:
                diff_json = parse_dict(new_response_json, response_json)
            # else:
            #     logging.info("No new JSON found.")
            response_json = new_response_json
                    
            if diff_json != {} and diff_json != last_diff_json:
                last_diff_json = diff_json
                yield diff_json, response_json
        
    @utils.time_it
    def create(self, messages):
        # logging.info(f"cMessages: {messages}")
        retries = 5
        completion = None
        while retries > 0 and completion is None:
            try:
                openai_stop = list(self.stop)
                openai_stop = [self.config.message_separator] + openai_stop
                if self.config.alternative_openai_api_base == 'none': # OpenAI stop is the first 4 options in the stop list because they only support up to 4 for some asinine reason
                    openai_stop = openai_stop[:3]
                else:
                    openai_stop = openai_stop
                openai_stop.append("}")
                openai_stop = [stop for stop in openai_stop if stop != ""] # Remove empty strings from the stop list
                logging.info("Stop Strings:",openai_stop)
                sampler_kwargs = {
                    "top_p": self.top_p,
                    "temperature": self.temperature,
                    "frequency_penalty": self.frequency_penalty,
                    "presence_penalty": self.presence_penalty
                }
                for kwarg in self.config.banned_samplers:
                    if kwarg in sampler_kwargs:
                        del sampler_kwargs[kwarg]
                extra_body_kwargs = {
                    "min_p": self.min_p,
                    "top_k":self.top_k,
                    "typical_p":self.typical_p,
                    "repeat_penalty":self.repeat_penalty,
                    "mirostat_mode":self.mirostat_mode,
                    "mirostat_tau":self.mirostat_tau,
                    "mirostat_eta":self.mirostat_eta,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": self.conversation_manager.thought_process.model_json_schema()
                    }
                }
                for kwarg in self.config.banned_samplers:
                    if kwarg in extra_body_kwargs:
                        del extra_body_kwargs[kwarg]
                if self.config.reverse_proxy:
                    extra_body_kwargs["proxy_password"] = self.api_key
                if self.completions_supported:
                    prompt = self.tokenizer.get_string_from_messages(messages) + self.tokenizer.start_message(self.config.assistant_name)
                    logging.info(f"Raw Prompt: {prompt}")
                    completion = self.client.completions.create(prompt=prompt,
                        model=self.config.openai_model, 
                        max_tokens=self.config.max_tokens,
                        **sampler_kwargs,
                        extra_body=extra_body_kwargs,
                        stream=False,
                        logit_bias=self.logit_bias,
                    )
                else:
                    completion = self.client.chat.completions.create(messages=messages,
                        model=self.config.openai_model, 
                        max_tokens=self.config.max_tokens,
                        **sampler_kwargs,
                        extra_body=extra_body_kwargs,
                        stream=False,
                        logit_bias=self.logit_bias,
                    )
                print(completion.choices[0].message)
                try:
                    completion = completion.choices[0].text
                except:
                    pass
                if completion is None or type(completion) != str:
                    try:
                        completion = completion.choices[0]["text"]
                    except:
                        pass
                if completion is None or type(completion) != str:
                    try:
                        completion = completion.choices[0].message.content
                    except:
                        pass
                if completion is None or type(completion) != str:
                    try:
                        completion = completion.choices[0].message.content
                    except:
                        pass
                if completion is None or type(completion) != str:
                    try:
                        completion = completion.choices[0].delta.content
                    except:
                        pass
                if completion is None or type(completion) != str:
                    logging.error(f"Could not get completion from OpenAI-style API. Please check your API key and internet connection.")
                    input("Press Enter to exit.")
                    raise ValueError(f"Could not get completion from OpenAI-style API. Please check your API key and internet connection.")
                    
                logging.info(f"Completion:"+str(completion))
            except Exception as e:
                logging.warning('Could not connect to LLM API, retrying in 5 seconds...')
                logging.warning(e)
                tb = traceback.format_exc()
                logging.error(tb)
                print(e)
                if retries == 1:
                    logging.error('Could not connect to LLM API after 5 retries, exiting...')
                    input('Press enter to continue...')
                    raise e
                time.sleep(5)
                retries -= 1
                continue
            break
        if type(completion) != str:
            logging.error(f"Could not get completion from OpenAI-style API. Please check your API key and internet connection.")
            input("Press Enter to exit.")
            raise ValueError(f"Could not get completion from OpenAI-style API. Please check your API key and internet connection.")
        return completion
    
    @utils.time_it
    def acreate(self, messages, message_prefix="", force_speaker=None): # Creates a completion stream for the messages provided to generate a speaker and their response
        # logging.info(f"aMessages: {messages}")
        retries = 5
        while retries > 0:
            try:
                openai_stop = list(self.stop)
                openai_stop = [self.message_separator,self.EOS_token,self.BOS_token] + openai_stop
                openai_stop = [stop for stop in openai_stop if stop != ""] # Remove empty strings from the stop list
                if self.config.alternative_openai_api_base == 'none': # OpenAI stop is the first 4 options in the stop list because they only support up to 4 for some asinine reason
                    openai_stop = openai_stop[:3]
                else:
                    openai_stop = openai_stop
                openai_stop.append("}")
                logging.info("Stop Strings:",openai_stop)
                sampler_kwargs = {
                    "top_p": self.top_p,
                    "temperature": self.temperature,
                    "frequency_penalty": self.frequency_penalty,
                    "presence_penalty": self.presence_penalty
                }
                for kwarg in self.config.banned_samplers:
                    if kwarg in sampler_kwargs:
                        del sampler_kwargs[kwarg]
                extra_body_kwargs = {
                    "min_p": self.min_p,
                    "top_k":self.top_k,
                    "typical_p":self.typical_p,
                    "repeat_penalty":self.repeat_penalty,
                    "mirostat_mode":self.mirostat_mode,
                    "mirostat_tau":self.mirostat_tau,
                    "mirostat_eta":self.mirostat_eta,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": self.conversation_manager.thought_process.model_json_schema()
                    }
                }
                for kwarg in self.config.banned_samplers:
                    if kwarg in extra_body_kwargs:
                        del extra_body_kwargs[kwarg]
                if self.config.reverse_proxy:
                    extra_body_kwargs["proxy_password"] = self.api_key

                schema_description = get_schema_description(self.conversation_manager.thought_process.model_json_schema())
                schema_message = {
                    "role": "system",
                    "content": schema_description
                }
                messages.insert(-2,schema_message)

                if self.completions_supported:
                    prompt = self.tokenizer.get_string_from_messages(messages)
                    prompt += self.tokenizer.start_message(self.config.assistant_name)
                    symbol_insert = ""
                    if force_speaker is not None:
                        prompt += force_speaker.name + self.config.message_signifier
                        prompt += message_prefix
                    logging.info(f"Raw Prompt: {prompt}")
                    if symbol_insert != "":
                        logging.info(f"Symbol Inserted: {symbol_insert}")
                    if self.config.log_all_api_requests:
                        log_id = None
                        while log_id is None or os.path.exists(self.config.api_log_dir+"/"+log_id+".log"):
                            log_id = str(random.randint(100000,999999))
                        # make sure the dir exists
                        os.makedirs(self.config.api_log_dir, exist_ok=True)
                        with open(self.config.api_log_dir+"/"+log_id+".log", "w") as f:
                            f.write(prompt)
                    
                    return self.client.completions.create(prompt=prompt,
                        model=self.config.openai_model, 
                        max_tokens=self.config.max_tokens,
                        **sampler_kwargs,
                        extra_body=extra_body_kwargs,
                        stream=True,
                        logit_bias=self.logit_bias,
                    )
                else:
                    logging.warning("Using chat completions because raw completions are not supported by the current API/settings.")
                    if self.config.log_all_api_requests:
                        log_id = None
                        while log_id is None or os.path.exists(self.config.api_log_dir+"/"+log_id+".log"):
                            log_id = str(random.randint(100000,999999))
                        os.makedirs(self.config.api_log_dir, exist_ok=True)
                        with open(self.config.api_log_dir+"/"+log_id+".json", "w") as f:
                            request_json = {
                                "messages": messages,
                                "model": self.config.openai_model,
                                "max_tokens": self.config.max_tokens,
                                **sampler_kwargs,
                                **extra_body_kwargs,
                                "stream": True,
                                "logit_bias": self.logit_bias
                            }
                            json_string = json.dumps(request_json)
                            f.write(json_string)
                    return self.client.chat.completions.create(messages=messages,
                        model=self.config.openai_model, 
                        max_tokens=self.config.max_tokens,
                        **sampler_kwargs,
                        extra_body=extra_body_kwargs,
                        stream=True,
                        logit_bias=self.logit_bias,
                    )
            except Exception as e:
                logging.warning('Could not connect to LLM API, retrying in 5 seconds...')
                logging.warning(e)
                tb = traceback.format_exc()
                logging.error(tb)
                print(e)
                if retries == 1:
                    logging.error('Could not connect to LLM API after 5 retries, exiting...')
                    input('Press enter to continue...')
                    raise e
                time.sleep(5)
                retries -= 1
                continue

    async def process_response(self, sentence_queue, event, force_speaker=None):
        """Stream response from LLM one sentence at a time"""
        logging.info(f"Processing response...")
        logging.info("Prompt Style:", self._prompt_style)
        logging.info("Language:", self.language["language_name"] + "("+self.language["language_code"]+") known in-game as "+self.language["in_game_language_name"])
        logging.info("Dynamic Stops:", self.stop)
        next_author = None # used to determine who is speaking next in a conversation
        verified_author = False # used to determine if the next author has been verified

        possible_players = [
            self.player_name,
            self.player_name.lower(),
            self.player_name.upper(),
        ]
        for character in self.conversation_manager.character_manager.active_characters.values():
            perspective_player_name, _ = character.get_perspective_player_identity()
            possible_players.append(perspective_player_name)
            possible_players.append(perspective_player_name.lower())
        possible_players.extend(self.player_name.split(" "))
        possible_players.extend(self.player_name.lower().split(" "))
        possible_players.extend(self.player_name.upper().split(" "))
        possible_players.extend(self.config.custom_possible_player_aliases)
        possible_players = list(set(possible_players)) # remove duplicates
        logging.info("Possible Player Aliases:",possible_players)

        # first_period = False # used to determine if the first period has been added to the sentence
        
        retries = self.config.retries
        bad_author_retries = self.config.bad_author_retries
        system_loop = self.config.system_loop

        logging.info(f"Retries Available: {retries}")
        logging.info(f"Bad Author Retries Available: {bad_author_retries}")
        logging.info(f"System Loops Available: {system_loop}")

        symbol_insert=""
        if self.conversation_manager.conversation_step == 1:
            first_message_hidden_symbol = self.conversation_manager.character_manager.language["first_message_hidden_symbol"]
            if len(first_message_hidden_symbol) > 0:
                symbol_insert = random.choice(first_message_hidden_symbol)
                logging.info(f"Symbol to Insert: {symbol_insert}")
        else:
            message_hidden_symbol = self.conversation_manager.character_manager.language["message_hidden_symbol"]
            if len(message_hidden_symbol) > 0:
                symbol_insert = random.choice(message_hidden_symbol)
                logging.info(f"Symbol to Insert: {symbol_insert}")

        
        

        while retries >= 0: # keep trying to connect to the API until it works
            # if full_reply != '': # if the full reply is not empty, then the LLM has generated a response and the next_author should be extracted from the start of the generation
            #     self.conversation_manager.new_message({"role": next_author, "content": full_reply})
            #     logging.info(f"LLM returned full reply: {full_reply}")
            #     full_reply = ''
            #     next_author = None
            #     verified_author = False
            #     sentence = ''
            #     num_sentences = 0
            #     retries = 5
            try:
                # Reset variables every retry
                proposed_next_author = '' # used to store the proposed next author
                if not self.completions_supported:
                    logging.warning(f"Completions are not supported by the current LLM. There might be more regenerations and errors because of this as we don't have full control over the exact prompt that is sent to the LLM.")
                    force_speaker = None
                    next_author = None
                    verified_author = False
                else:
                    if force_speaker is not None: # Force speaker to a specific character
                        logging.info(f"Forcing speaker to: {force_speaker.name}")
                        next_author = force_speaker.name
                        proposed_next_author = next_author
                        verified_author = True
                    elif self.conversation_manager.character_manager.active_character_count() == 1: # if there is only one active character, then the next author should most likely always be the only active character
                        logging.info(f"Only one active character. Attempting to force speaker to: {self.conversation_manager.game_interface.active_character.name}")
                        next_author = self.conversation_manager.game_interface.active_character.name
                        proposed_next_author = next_author
                        verified_author = True
                        force_speaker = self.conversation_manager.game_interface.active_character
                start_time = time.time()
                beginning_of_sentence_time = time.time()
                last_chunk = None
                same_chunk_count = 0
                new_speaker = False
                eos = False 
                typing_roleplay = self._prompt_style["roleplay_inverted"]
                if symbol_insert == self._prompt_style["roleplay_prefix"] or symbol_insert == self._prompt_style["roleplay_suffix"]:
                    typing_roleplay = not typing_roleplay
                was_typing_roleplay = typing_roleplay
        
                raw_reply = '' # used to store the raw reply
                full_reply = '' # used to store the full reply

                voice_line = '' # used to store the current voice line being generated
                sentence = '' # used to store the current sentence being generated
                next_sentence = '' # used to store the next sentence being generated # example: "*She walked to the store to pick up juice"
                next_speaker_sentence = '' # used to store the next speaker's sentence
                
                num_sentences = 0 # used to keep track of how many sentences have been generated total
                voice_line_sentences = 0 # used to keep track of how many sentences have been generated for the current voice line
                send_voiceline = False # used to determine if the current sentence should be sent early

                voice_lines = [] # used to store the voice lines generated
                same_roleplay_symbol = self._prompt_style["roleplay_suffix"] == self._prompt_style["roleplay_prefix"] # used to determine if the roleplay symbol is the same for both the prefix and suffix

                full_json = {}

                logging.info(f"Starting response generation...")
                for chunk, complete_json in self.generate_response(message_prefix=symbol_insert, force_speaker=force_speaker):
                    full_json = complete_json
                    if "response_to_user" not in chunk:
                        logging.info(f"Thought Chunk:",chunk)
                        continue
                    else:
                        logging.info(f"Response Chunk:",chunk)
                        chunk = chunk["response_to_user"]
                    content = chunk # example: ".* Hello"
                    logging.out(f"Content: {content}")
                    if content is None:
                        logging.error(chunk)
                        logging.error(f"Content is None")
                        raise Exception('Content is None')
                    if content is not last_chunk: # if the content is not the same as the last chunk, then the LLM is not stuck in a loop and the generation should continue
                        same_chunk_count = 0
                    else: # if the content is the same as the last chunk, then the LLM is probably stuck in a loop and the generation should stop
                        same_chunk_count += 1
                        if same_chunk_count > self.config.same_output_limit:
                            logging.error(f"Same chunk returned {same_chunk_count} times in a row. Stopping generation.")
                            raise Exception('Same chunk returned too many times in a row')
                        else:
                            logging.debug(f"Same chunk returned {same_chunk_count} times in a row.")
                    last_chunk = content
                    if content is None:
                        continue
                    if eos: # if the EOS token has been detected, then the generation should stop
                        logging.info(f"EOS token detected. Stopping generation.")
                        break

                    raw_reply += content

                    # EOS token detection
                    if self.EOS_token in raw_reply:
                        logging.info(f"Sentence contains EOS token. Stopping generation.")
                        eos = True
                    elif self.EOS_token.lower() in raw_reply.lower():
                        logging.info(f"Sentence probably contains EOS token(determined by lower() checking.). Stopping generation.")
                        eos = True

                    def raise_invalid_author(retries, bad_author_retries):
                        logging.info(f"Next author is None. Failed to extract author from: {sentence}")
                        logging.info(f"Retrying...")
                        retries += 1
                        bad_author_retries -= 1
                        if bad_author_retries == 0:
                            logging.info(f"LLM Could not suggest a valid author, picking one at random from active characters to break the loop...")
                            random_authors = list(self.conversation_manager.character_manager.active_characters.keys())
                            next_author = random.choice(random_authors)
                        else:
                            raise Exception('Invalid author')
                        return next_author, retries, bad_author_retries

                    contains_end_of_sentence_character = any(char in unicodedata.normalize('NFKC', content) for char in self.end_of_sentence_chars)
                    contains_roleplay_symbol = any(char in unicodedata.normalize('NFKC', content) for char in [self._prompt_style["roleplay_prefix"],self._prompt_style["roleplay_suffix"]])
                    for replacement in self.replacements:
                        char, replacement_char = replacement["char"], replacement["replacement"]
                        if char in content:
                            logging.debug(f"Replacement character '{char}' found in sentence: '{content}'")
                            logging.debug("Replacement Characters:",self.replacements)
                            content = content.replace(char, replacement_char)
                    # Propose Author or Write their response
                    if next_author is None: # if next_author is None after generating a chunk of content, then the LLM didn't choose a character to speak next yet.
                        proposed_next_author += content
                        if self.message_signifier in proposed_next_author: # if the proposed next author contains the message signifier, then the next author has been chosen
                            sentence, next_author, verified_author, retries, bad_author_retries, system_loop = self.check_author(proposed_next_author, next_author, verified_author, possible_players, retries, bad_author_retries, system_loop)
                        if (contains_end_of_sentence_character or contains_roleplay_symbol) and next_author is None:
                            next_author, retries, bad_author_retries = raise_invalid_author(retries, bad_author_retries)
                    else: # if the next author is already chosen, then the LLM is generating the response for the next author
                        sentence += content # add the content to the sentence in progress
                        for replacement in self.replacements:
                            char, replacement_char = replacement["char"], replacement["replacement"]
                            if char in sentence:
                                logging.debug(f"Replacement character '{char}' found in sentence: {sentence}")
                                logging.debug("Replacement Characters:",self.replacements)
                                sentence = sentence.replace(char, replacement_char)
                        for char in self.stop:
                            if char in sentence:
                                logging.debug(f"Banned character '{char}' found in sentence: {sentence}")
                                logging.debug("Banned Characters:",self.stop)
                                eos = True
                                sentence = sentence.split(char)[0]
                                raw_reply = raw_reply.split(char)[0]
                                logging.info(f"Trimming last sentence to: {sentence}")
                        if self.config.assist_check and 'assist' in sentence and num_sentences > 0: # if remote, check if the response contains the word assist for some reason. Probably some OpenAI nonsense.# Causes problems if asking a follower if you should "assist" someone, if they try to say something along the lines of "Yes, we should assist them." it will cut off the sentence and basically ignore the player. TODO: fix this with a more robust solution
                            logging.info(f"'assist' keyword found. Ignoring sentence which begins with: {sentence}") 
                            break # stop generating response
                        if self.config.break_on_time_announcements and typing_roleplay and "The time is now" in sentence:
                            logging.info(f"Breaking on time announcement")
                            break

                    if eos: # remove the EOS token from the sentence and trim the sentence to the EOS token's position
                        sentence = sentence.split(self.EOS_token)[0]
                        raw_reply = raw_reply.split(self.EOS_token)[0]


                        
                    # contains_banned_character = any(char in content for char in self.stop)
                    effective_voice_line_sentences = int(voice_line_sentences)
                    if contains_roleplay_symbol: # if the content contains an asterisk, then either the narrator has started speaking or the narrator has stopped speaking and the NPC is speaking
                        logging.info(f"Roleplay symbol found in content: {content}")
                        if self._prompt_style["roleplay_suffix"] in sentence:
                            sentences = sentence.split(self._prompt_style["roleplay_suffix"], 1)
                        elif self._prompt_style["roleplay_prefix"] in sentence:
                            sentences = sentence.split(self._prompt_style["roleplay_prefix"], 1)
                        else:
                            logging.warn(f"But roleplay symbol was not found in sentence?!")
                            sentences = [sentence]
                        sentences = [sentence for sentence in sentences if sentence.strip() != '']
                        if len(sentences) == 2: # content HAS a roleplay symbol and the sentence is not empty
                            logging.info(f"Roleplay symbol found in content: {content}")
                            logging.info(f"New Speaker, splitting sentence at roleplay symbol")
                            sentence, next_speaker_sentence = sentences[0], sentences[1]
                            effective_voice_line_sentences += 1
                        elif content.strip() == self._prompt_style["roleplay_prefix"] or content.strip() == self._prompt_style["roleplay_suffix"]: # content IS a roleplay symbol and the sentence is empty
                            logging.info(f"Roleplay symbol was latest content: {content}")
                            if len(sentence.replace(self._prompt_style["roleplay_prefix"], "").replace(self._prompt_style["roleplay_suffix"], "").strip()) > 0:
                                logging.info(f"Roleplay symbol was latest content: {content} - Sentence is not empty")
                                effective_voice_line_sentences += 1
                            else:
                                logging.info(f"Roleplay symbol was latest content: {content} - Sentence is empty")
                                sentence = ""
                            next_speaker_sentence = ''
                        elif len(sentences) == 1 and content.strip().startswith(self._prompt_style["roleplay_prefix"]): # content HAS a roleplay symbol and the sentence is empty
                            logging.info(f"Roleplay symbol was latest content: {content} - Starting with roleplay symbol")
                            sentence = ""
                            next_speaker_sentence = sentences[0]
                        elif len(sentences) == 1 and content.strip().endswith(self._prompt_style["roleplay_suffix"]): # content HAS a roleplay symbol and the next_speaker_sentence is empty 
                            logging.info(f"Roleplay symbol was latest content: {content} - Ending with roleplay symbol")
                            sentence = sentences[0]
                            next_speaker_sentence = ""
                            effective_voice_line_sentences += 1
                        
                        was_typing_roleplay = bool(typing_roleplay)
                        typing_roleplay = not typing_roleplay
                        
                        if typing_roleplay:
                            full_reply = full_reply.strip() +"[ns-1]"+ self._prompt_style["roleplay_prefix"]
                        
                        
                        if effective_voice_line_sentences > 0 or len(voice_line) > 0: # if the sentence is not empty and the number of sentences is greater than 0, then the narrator is speaking
                            logging.info(f"New speaker")
                            new_speaker = True
                        else: # if the sentence is empty and the number of sentences is 0, then the narrator is not speaking
                            logging.info(f"Same speaker")
                        speaker = "Narrator" if typing_roleplay else next_author
                        logging.debug(f"New speaker - Toggling speaker to: {speaker}")
                        # if effective_voice_line_sentences == 0: # if the sentence is empty, then the speaker toggled before any content was added to the voice_line
                        #     new_speaker = False
                        if next_speaker_sentence != "":
                            logging.info(f"Next speaker sentence part: {next_speaker_sentence}")
                    logging.info(f"Voice Line Sentences: {voice_line_sentences}")
                    logging.info(f"Effective Voice Line Sentences: {effective_voice_line_sentences}")

                    parsing_sentence = contains_end_of_sentence_character or eos or contains_roleplay_symbol # check if the sentence is complete and ready to be parsed
                    if (parsing_sentence or new_speaker) and (len(sentence) > 0 or (contains_roleplay_symbol and effective_voice_line_sentences > 0)): # check if content marks the end of a sentence or if the speaker is switching
                        logging.out(f"Sentence: {sentence}")
                        logging.debug(f"was_typing_roleplay: {was_typing_roleplay}")
                        logging.debug(f"currently_typing_roleplay: {typing_roleplay}")
                        if next_author is None: # if next_author is None after generating a sentence, then there was an error generating the output. The LLM didn't choose a character to speak next.
                            next_author, retries, bad_author_retries = raise_invalid_author()
                        if not new_speaker:
                            sentence, next_sentence = self.split_and_preverse_strings_on_end_of_sentence(sentence, next_sentence)
                            logging.info(f"Split sentence: {sentence}")
                            logging.info(f"Next sentence: {next_sentence}")

                        logging.info(f"LLM took {time.time() - beginning_of_sentence_time} seconds to generate sentence")
                        logging.info(f"Checking for behaviors using behavior style: {self.behavior_style}")


                        found_behaviors = []
                        if self.behavior_style["prefix"] in sentence:
                            sentence_words = sentence.split(" ")
                            new_sentence = ""
                            for word in sentence_words: # Rebuild the sentence while checking for behavior keywords(or pseudo-keywords and removing them when found)
                                if self.behavior_style["prefix"] in word and self.behavior_style["suffix"] in word:
                                    new_behaviors = self.conversation_manager.behavior_manager.evaluate(word, self.conversation_manager.game_interface.active_character, sentence) # check if the sentence contains any behavior keywords for NPCs
                                    if len(new_behaviors) > 0:
                                        found_behaviors.extend(new_behaviors)
                                        logging.info(f"Behaviors triggered: {new_behaviors}")
                                        new_sentence += word + " " # Only add the word back if it was a real behavior keyword
                                # elif self.behavior_style["prefix"] in word and not self.behavior_style["suffix"] in word: # if the word contains the prefix but not the suffix, then the suffix is probably in the next word, which is likely a format break.
                                #     break
                                else:
                                    new_sentence += word + " "
                            sentence = new_sentence.strip()
                        if len(found_behaviors) == 0:
                            logging.warn(f"No behaviors triggered by sentence: {sentence}")
                        else:
                            for behavior in found_behaviors:
                                logging.info(f"Behavior(s) triggered: {behavior.keyword}")
                        if not new_speaker:
                            sentence = self.clean_sentence(sentence) # clean the sentence
                        logging.info(f"Full Reply Before: {full_reply}")
                        logging.info(f"Sentence: {sentence}")

                        voice_line = voice_line.strip() + " " + sentence.strip() # add the sentence to the voice line in progress
                        full_reply = full_reply.strip()
                        if len(full_reply) > 0 and (not full_reply.endswith(self._prompt_style["roleplay_suffix"]) and not full_reply.endswith(self._prompt_style["roleplay_prefix"])): # if the full reply is not empty and the last character is not a roleplay symbol, then just add the sentence with a space
                            full_reply = full_reply.strip() + "[s0] " + sentence.strip() # add the sentence to the full reply
                        else: # if the full reply is empty or ends with a roleplay symbol, then figure out if the sentence should be added with or without a space
                            if same_roleplay_symbol:
                                if not was_typing_roleplay and typing_roleplay: # If just started roleplay, add the sentence without a space
                                    full_reply = full_reply.strip() + "[ns1]" + sentence.strip()
                                elif was_typing_roleplay and not typing_roleplay: # If just stopped roleplaying, or if you're still actively/not actively roleplaying, add the sentence with a space
                                    full_reply = full_reply.strip() + sentence.strip()
                                elif was_typing_roleplay and typing_roleplay:
                                    if num_sentences == 1:
                                        full_reply = full_reply.strip() + "[ns3] " + sentence.strip()
                                    else:
                                        full_reply = full_reply.strip() + "[s1] " + sentence.strip()
                                else:
                                    full_reply = full_reply.strip() + "[s2] " +  sentence.strip()
                            else:
                                if full_reply.endswith(self._prompt_style["roleplay_suffix"]):
                                    full_reply = full_reply.strip() + "[s3] " + sentence.strip()
                                else:
                                    full_reply = full_reply.strip() + "[ns4]" + sentence.strip()
                            # if len(full_reply) > 0:
                            #     if typing_roleplay:
                            #         full_reply = full_reply.strip() + sentence.strip()
                            #     else:
                            #         full_reply = full_reply.strip() + " " + sentence.strip()
                            # else:
                            #     full_reply = sentence.strip()
                        full_reply = full_reply.strip()
                        if new_speaker:
                            if not typing_roleplay:
                                full_reply = full_reply.strip() + "[ns5]" + self._prompt_style["roleplay_suffix"]
                            # else:
                            #     full_reply = full_reply.strip() + "[ns6]" + self._prompt_style["roleplay_prefix"]
                        num_sentences += 1 # increment the total number of sentences generated
                        voice_line_sentences += 1 # increment the number of sentences generated for the current voice line
                        

                        logging.debug(f"Parsed sentence: {sentence}")
                        logging.debug(f"Parsed full reply: {full_reply}")
                        logging.debug(f"Parsed voice line: {voice_line}")
                        logging.debug(f"Number of sentences: {num_sentences}")
                        logging.debug(f"Number of sentences in voice line: {voice_line_sentences}")
                        
                        grammarless_stripped_voice_line = voice_line.replace(".", "").replace("?", "").replace("!", "").replace(",", "").replace("-", "").replace("*", "").replace("\"", "").strip()
                        if grammarless_stripped_voice_line == '' or voice_line.strip() == "": # if the voice line is empty, then the narrator is speaking
                            logging.info(f"Skipping empty voice line")
                            send_voiceline = False
                            voice_line = ''

                        if voice_line_sentences == self.config.sentences_per_voiceline or new_speaker: # if the voice line is ready, then generate the audio for the voice line
                            if was_typing_roleplay:
                                logging.info(f"Generating voiceline: \"{voice_line.strip()}\" for narrator.")
                            else:
                                logging.info(f"Generating voiceline: \"{voice_line.strip()}\" for {self.conversation_manager.game_interface.active_character.name}.")
                            send_voiceline = True

                        if send_voiceline: # if the voice line is ready, then generate the audio for the voice line
                            logging.info(f"Voice line contains {voice_line_sentences} sentences.")
                            logging.info(f"Voice line should be spoken by narrator: {typing_roleplay}")
                            if self.config.strip_smalls and len(voice_line.strip()) < self.config.small_size:
                                logging.info(f"Skipping small voice line: {voice_line}")
                                break
                            voice_line = voice_line.replace('[', '(')
                            voice_line = voice_line.replace(']', ')')
                            voice_line = voice_line.replace('{', '(')
                            voice_line = voice_line.replace('}', ')')
                            # remove any parentheses groups from the voiceline.
                            voice_line = re.sub(r'\([^)]*\)', '', voice_line)
                            if not voice_line.strip() == "":
                                logging.info(f"Voice line: \"{voice_line}\" is definitely not empty.")
                                self.conversation_manager.behavior_manager.pre_sentence_evaluate(self.conversation_manager.game_interface.active_character, sentence,) # check if the sentence contains any behavior keywords for NPCs
                                if was_typing_roleplay: # if the asterisk is open, then the narrator is speaking
                                    time.sleep(self.config.narrator_delay)
                                    voice_lines.append((voice_line.strip(), "narrator"))
                                    voiceline_path = self.conversation_manager.synthesizer._say(voice_line.strip(), self.config.narrator_voice, self.config.narrator_volume)
                                    # audio_duration = await self.conversation_manager.game_interface.get_audio_duration(voiceline_path)
                                    # logging.info(f"Waiting {int(round(audio_duration,4))} seconds for audio to finish playing...")
                                    # time.sleep(audio_duration)
                                else: # if the asterisk is closed, then the NPC is speaking
                                    voice_lines.append((voice_line.strip(), self.conversation_manager.game_interface.active_character.name))
                                    await self.generate_voiceline(voice_line.strip(), sentence_queue, event)
                                self.conversation_manager.behavior_manager.post_sentence_evaluate(self.conversation_manager.game_interface.active_character, sentence) # check if the sentence contains any behavior keywords for NPCs
                            voice_line_sentences = 0 # reset the number of sentences generated for the current voice line
                            voice_line = '' # reset the voice line for the next iteration
                            # if single_sentence_roleplay:
                            #     roleplaying = not roleplaying
                            #     single_sentence_roleplay = False

                        logging.debug(f"Next sentence: {next_sentence}")
                        grammarless_stripped_next_sentence = next_sentence.replace(".", "").replace("?", "").replace("!", "").replace(",", "").strip()
                        if grammarless_stripped_next_sentence != '': # if there is a next sentence, then set the current sentence to the next sentence
                            sentence = next_sentence
                            next_sentence = ''
                        else:
                            sentence = '' # reset the sentence for the next iteration
                            next_sentence = ''

                        logging.debug(f"Current sentence: {sentence}")
                        logging.debug(f"Next speaker sentence piece: {next_speaker_sentence}")
                        if new_speaker:
                            grammarless_stripped_next_speaker_sentence = next_speaker_sentence.replace(".", "").replace("?", "").replace("!", "").replace(",", "").strip()
                            if grammarless_stripped_next_speaker_sentence != '': # if there is a next speaker's sentence, then set the current sentence to the next speaker's sentence
                                sentence += next_speaker_sentence
                                next_speaker_sentence = ''
                            else:
                                sentence = '' # reset the sentence for the next iteration
                            next_sentence = '' # reset the next sentence for the next iteration
                        logging.debug(f"Final sentence?: {sentence}")

                        radiant_dialogue_update = self.conversation_manager.game_interface.is_radiant_dialogue() # check if the conversation has switched from radiant to multi NPC
                        # stop processing LLM response if:
                        # max_response_sentences reached (and the conversation isn't radiant)
                        # conversation has switched from radiant to multi NPC (this allows the player to "interrupt" radiant dialogue and include themselves in the conversation)
                        # the conversation has ended
                        new_speaker = False
                        send_voiceline = False
                        if new_speaker:
                            typing_roleplay = not typing_roleplay
                        if ((num_sentences >= self.max_response_sentences) and not self.conversation_manager.radiant_dialogue) or (self.conversation_manager.radiant_dialogue and not radiant_dialogue_update) or self.conversation_manager.game_interface.is_conversation_ended() or eos: # if the conversation has ended, stop generating responses
                            logging.info(f"Response generation complete. Stopping generation.")
                            break
                
                print(f"Full Thought Process:",json.dumps(full_json, indent=4))

                # input('Press enter to continue...')
                logging.info(f"LLM response took {time.time() - start_time} seconds to execute")
                if full_reply.strip() == "":
                    if self.config.error_on_empty_full_reply:
                        raise Exception('Empty full reply')
                if num_sentences == 0: # if no sentences were generated, then the LLM failed to generate a response
                    logging.error(f"LLM failed to generate a response or a valid Author. Retrying...")
                    retries += 1
                    continue
                break
            except Exception as e:
                if force_speaker is not None:
                    next_author = force_speaker.name
                    proposed_next_author = next_author
                else:
                    next_author = None
                    proposed_next_author = ''
                verified_author = False
                sentence = ''
                next_sentence = ''
                next_speaker_sentence = ''
                voice_line = ''
                full_reply = ''
                num_sentences = 0
                voice_line_sentences = 0
                send_voiceline = False
                if retries == 0:
                    logging.error(f"Could not connect to LLM API\nError:")
                    logging.error(e)
                    input('Press enter to continue...')
                    raise e
                logging.error(f"LLM API Error: {e}")
                tb = traceback.format_exc()
                logging.error(tb)
                if not self.config.continue_on_llm_api_error:
                    raise e
                if 'Invalid author' in str(e):
                    logging.info(f"Retrying without saying error voice line")
                    retries += 1
                    continue
                if 'Voiceline too short' in str(e):
                    logging.info(f"Retrying without saying error voice line")
                    retries += 1
                    continue
                elif 'Empty sentence' in str(e):
                    logging.info(f"Retrying without saying error voice line")
                    retries += 1
                    continue
                else:
                    # raise e # Enable this to stop the conversation if the LLM fails to generate a response so that the user can see the error
                    self.conversation_manager.game_interface.active_character.say("I can't find the right words at the moment.")
                    logging.info('Retrying connection to API...')
                    retries -= 1
                    time.sleep(5)

        if voice_line_sentences > 0: # if the voice line is not empty, then generate the audio for the voice line
            logging.info(f"Generating voiceline: \"{voice_line.strip()}\" for {self.conversation_manager.game_interface.active_character.name}.")
            if typing_roleplay: # if the asterisk is open, then the narrator is speaking
                time.sleep(self.config.narrator_delay)
                voiceline_path = self.conversation_manager.synthesizer._say(voice_line.strip(), self.config.narrator_voice, self.config.narrator_volume)
                voice_lines.append((voice_line.strip(), "narrator"))
                # audio_duration = await self.conversation_manager.game_interface.get_audio_duration(voiceline_path)
                # logging.info(f"Waiting {int(round(audio_duration,4))} seconds for audio to finish playing...")
                # time.sleep(audio_duration)
            else:
                voice_lines.append((voice_line.strip(), self.conversation_manager.game_interface.active_character.name))
                await self.generate_voiceline(voice_line.strip(), sentence_queue, event)
            voice_line_sentences = 0
            voice_line = ''

        await sentence_queue.put(None) # Mark the end of the response for self.conversation_manager.game_interface.send_response() and self.conversation_manager.game_interface.send_response()

        full_reply = full_reply.strip()
        
        # if full_reply.endswith("*") and full_reply.count("*") == 1: # TODO: Figure out the reason I need this bandaid solution... if only one asterisk at the end, remove it.
        #     full_reply = full_reply[:-1].strip()
        # if typing_roleplay: # if the asterisk is open, then the narrator is speaking
        #     full_reply += self._prompt_style["roleplay_suffix"]
        logging.debug(f"Final Full Reply: {full_reply}")
        logging.debug(f"Voice Lines:", voice_lines)
        logging.debug(f"Raw Reply:", raw_reply)
        if self._prompt_style["roleplay_suffix"] in full_reply or self._prompt_style["roleplay_prefix"] in full_reply:
            # if they're the same symbol, make sure they're balanced
            if full_reply.count(self._prompt_style["roleplay_suffix"]) != full_reply.count(self._prompt_style["roleplay_prefix"]):
                logging.warning(f"Unbalanced roleplay symbols in full reply: {full_reply}")
                if full_reply.count(self._prompt_style["roleplay_suffix"]) > full_reply.count(self._prompt_style["roleplay_prefix"]):
                    full_reply = full_reply.replace(self._prompt_style["roleplay_suffix"], "")
                else:
                    full_reply = full_reply.replace(self._prompt_style["roleplay_prefix"], "")
                logging.warning(f"Fixed full reply: {full_reply}")
            if full_reply.strip() == "":
                logging.warning(f"Skipping empty full reply")
                return
        # try: 
        #     if sentence_behavior != None:
        #         full_reply = sentence_behavior.keyword + ": " + full_reply.strip() # add the keyword back to the sentence to reinforce to the that the keyword was used to trigger the bahavior
        # except:
        #     pass

        if next_author is not None and full_reply != '':
            full_reply = full_reply.replace("[s0]", "").replace("[s1]", "").replace("[s2]", "").replace("[s3]", "").replace("[ns-1]", "").replace("[ns0]", "").replace("[ns1]", "").replace("[ns2]", "").replace("[ns3]", "").replace("[ns4]", "").replace("[ns5]", "").replace("[ns6]", "").strip() # remove the sentence spacing tokens
            full_reply = full_reply.strip()
            if self.config.message_reformatting:
                logging.info(f"Using Full Reply with Reformatting")
                self.conversation_manager.new_message({"role": self.config.assistant_name, 'name':next_author, "content": full_reply})
            else:
                logging.info(f"Using Raw Reply without Reformatting")
                self.conversation_manager.new_message({"role": self.config.assistant_name, 'name':next_author, "content": raw_reply})
            # -- for each sentence for each character until the conversation ends or the max_response_sentences is reached or the player is speaking
            logging.info(f"Full response saved ({self.tokenizer.get_token_count(full_reply)} tokens): {full_reply}")
