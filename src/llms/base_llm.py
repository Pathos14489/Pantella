print("Importing base_LLM.py")
from src.logging import logging, time
import src.utils as utils
import re
import unicodedata
import random
logging.info("Imported required libraries in base_LLM.py")

inference_engine_name = "base_LLM"
tokenizer_slug = "tiktoken" # default to tiktoken for now (Not always correct, but it's the fastest tokenizer and it works for openai's models, which a lot of users will be relying on probably)
class base_LLM():
    def __init__(self, conversation_manager):
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config
        self.tokenizer = None
        self.language_info = self.conversation_manager.language_info
        
        self.inference_engine_name = inference_engine_name
        self.tokenizer_slug = tokenizer_slug

        self.max_response_sentences = self.config.max_response_sentences
        self.end_of_sentence_chars = self.config.end_of_sentence_chars
        self.end_of_sentence_chars = [unicodedata.normalize('NFKC', char) for char in self.end_of_sentence_chars]
        self.banned_chars = self.config.banned_chars
        if not self.config.allow_npc_custom_game_events:
            self.banned_chars.append("*") # prevent NPCs from using custom game events via asterisk RP actions
            # self.banned_chars.append("(") # prevent NPCs from using custom game events via brackets RP actions
            # self.banned_chars.append(")") # prevent NPCs from using custom game events via brackets RP actions
            # self.banned_chars.append("[") # prevent NPCs from using custom game events via brackets RP actions
            # self.banned_chars.append("]") # prevent NPCs from using custom game events via brackets RP actions

        self.prompt_style = "normal"
        self.type = "normal"
        self.is_local = True

    @property
    def character_manager(self):
        return self.conversation_manager.character_manager

    @property
    def game_interface(self):
        return self.conversation_manager.game_interface

    @property
    def maximum_local_tokens(self):
        return self.config.maximum_local_tokens

    @property
    def player_name(self):
        return self.conversation_manager.player_name

    @property
    def EOS_token(self):
        return self.config.EOS_token
    
    @property
    def BOS_token(self):
        return self.config.BOS_token

    @property
    def max_tokens(self):
        return self.config.max_tokens
    
    @property
    def temperature(self):
        return self.config.temperature
    
    @property
    def top_k(self):
        return self.config.top_k
    
    @property
    def top_p(self):
        return self.config.top_p

    @property
    def min_p(self):
        return self.config.min_p

    @property
    def repeat_penalty(self):
        return self.config.repeat_penalty
    
    @property
    def tfs_z(self):
        return self.config.tfs_z

    @property
    def frequency_penalty(self):
        return self.config.frequency_penalty
    
    @property
    def presence_penalty(self):
        return self.config.presence_penalty
    
    @property
    def typical_p(self):
        return self.config.typical_p
    
    @property
    def mirostat_mode(self):
        return self.config.mirostat_mode
    
    @property
    def mirostat_eta(self):
        return self.config.mirostat_eta
    
    @property
    def mirostat_tau(self):
        return self.config.mirostat_tau
    
    @property
    def stop(self):
        return self.config.stop
    
    @property
    def transformers_model_slug(self):
        return self.config.transformers_model_slug
    
    @property
    def device_map(self):
        return self.config.device_map
    
    @property
    def trust_remote_code(self):
        return self.config.trust_remote_code
    
    @property
    def load_in_8bit(self):
        return self.config.load_in_8bit

    @property
    def messages(self):
        return self.conversation_manager.messages

    # the string printed when your print() this object
    def __str__(self):
        return f"{self.inference_engine_name} LLM"
    
    @utils.time_it
    def chatgpt_api(self, input_text, messages): # Creates a synchronouse completion for the messages provided to generate response for the assistant to the user. TODO: remove later
        """Generate a response from the LLM using the messages provided - Deprecated, use create() instead"""
        logging.info(f"ChatGPT API: {input_text}")
        logging.info(f"Messages: {messages}")
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
        """Generate a response from the LLM using the messages provided"""
        logging.info(f"Warning: Using base_LLM.create() instead of a child class, this is probably not what you want to do. Please override this method in your child class!")
        input("Press enter to continue...")
        raise NotImplementedError("Please override this method in your child class!")

    def acreate(self, messages): # Creates a completion stream for the messages provided to generate a speaker and their response
        """Generate a streameed response from the LLM using the messages provided"""
        logging.info(f"Warning: Using base_LLM.acreate() instead of a child class, this is probably not what you want to do. Please override this method in your child class!")
        input("Press enter to continue...")
        raise NotImplementedError("Please override this method in your child class!")
    
    def clean_sentence(self, sentence):
        """Clean the sentence by removing unwanted characters and formatting it properly"""
        logging.info(f"Cleaning sentence: {sentence}")
        def remove_as_a(sentence):
            """Remove 'As an XYZ,' from beginning of sentence"""
            if sentence.startswith('As a'):
                if ', ' in sentence:
                    logging.info(f"Removed '{sentence.split(', ')[0]} from response")
                    sentence = sentence.replace(sentence.split(', ')[0]+', ', '')
            return sentence
        
        def parse_asterisks_brackets(sentence):
            if '*' in sentence:
                # Check if sentence contains two asterisks
                asterisk_check = re.search(r"(?<!\*)\*(?!\*)[^*]*\*(?!\*)", sentence)
                if asterisk_check:
                    logging.info(f"Removed asterisks text from response: {sentence}")
                    # Remove text between two asterisks
                    sentence = re.sub(r"(?<!\*)\*(?!\*)[^*]*\*(?!\*)", "", sentence)
                else:
                    logging.info(f"Removed response containing single asterisks: {sentence}")
                    sentence = ''

            if '(' in sentence or ')' in sentence:
                # Check if sentence contains two brackets
                bracket_check = re.search(r"\(.*\)", sentence)
                if bracket_check:
                    logging.info(f"Removed brackets text from response: {sentence}")
                    # Remove text between brackets
                    sentence = re.sub(r"\(.*?\)", "", sentence)
                else:
                    logging.info(f"Removed response containing single brackets: {sentence}")
                    sentence = ''
                    
                
            # if doesn't end with sentence ender, use a period.
            if not any(char in sentence for char in self.end_of_sentence_chars):
                sentence += '.'

            return sentence
        
        if 'Well, well, well' in sentence:
            sentence = sentence.replace('Well, well, well', 'Well well well')

        sentence = remove_as_a(sentence)
        sentence = sentence.replace('"','')
        sentence = sentence.replace('[', '(')
        sentence = sentence.replace(']', ')')
        sentence = sentence.replace('{', '(')
        sentence = sentence.replace('}', ')')
        # local models sometimes get the idea in their head to use double asterisks **like this** in sentences instead of single
        # this converts double asterisks to single so that they can be filtered out appropriately
        sentence = sentence.replace('**','*')
        sentence = parse_asterisks_brackets(sentence)
        sentence = unicodedata.normalize('NFKC', sentence)

        logging.info(f"Cleaned sentence: {sentence}")
        return sentence

    def get_messages(self):
        """Get the messages from the conversation manager"""
        logging.info(f"Getting messages from conversation manager")
        system_prompt = self.character_manager.get_system_prompt() # get system prompt
        msgs = [{'role': self.config.system_name, 'content': system_prompt, "type":"prompt"}] # add system prompt to context
        msgs.extend(self.messages) # add messages to context

        memory_offset = self.character_manager.memory_offset
        memory_offset_direction = self.character_manager.memory_offset_direction
        memories = self.character_manager.get_memories()
        # insert memories into msgs based on memory_offset_direction "topdown" for from the beginning and "bottomup" for from the end, and insert it at memory_offset from the beginning or end
        if memory_offset == 0: # if memory offset is 0, then insert memories after the system prompt
            memory_offset = 1
        if memory_offset_direction == "topdown":
            msgs = msgs[:memory_offset] + memories + msgs[memory_offset:]
        elif memory_offset_direction == "bottomup":
            msgs = msgs[:-memory_offset] + memories + msgs[-memory_offset:]
        logging.info(f"Messages: {len(msgs)}")
        return msgs
    
        
    def get_context(self):
        """Get the correct set of messages to use with the LLM to generate the next response"""
        msgs = self.get_messages()
        formatted_messages = [] # format messages to be sent to LLM - Replace [player] with player name appropriate for the type of conversation
        for msg in msgs: # Add player name to messages based on the type of conversation
            if msg['role'] == self.config.user_name: # if the message is from the player
                if self.character_manager.active_character_count() > 1: # if multi NPC conversation use the player's actual name
                    formatted_msg = {
                        'role': self.config.user_name,
                        'name': self.player_name,
                        'content': msg['content'],
                    }
                    if "timestamp" in msg:
                        formatted_msg["timestamp"] = msg["timestamp"]
                    if "location" in msg:
                        formatted_msg["location"] = msg["location"]
                    if "type" in msg:
                        formatted_msg["type"] = msg["type"]
                else: # if single NPC conversation use the NPC's perspective player name
                    perspective_player_name, _ = self.game_interface.active_character.get_perspective_player_identity()
                    formatted_msg = {
                        'role': self.config.user_name,
                        'name': perspective_player_name,
                        'content': msg['content'],
                    }
                    if "timestamp" in msg:
                        formatted_msg["timestamp"] = msg["timestamp"]
                    if "location" in msg:
                        formatted_msg["location"] = msg["location"]
                    if "type" in msg:
                        formatted_msg["type"] = msg["type"]
            elif msg['role'] == self.config.system_name: # if the message is from the system
                    formatted_msg = {
                        'role': msg['role'],
                        'content': msg['content'],
                    }
                    if "timestamp" in msg:
                        formatted_msg["timestamp"] = msg["timestamp"]
                    if "location" in msg:
                        formatted_msg["location"] = msg["location"]
                    if "type" in msg:
                        formatted_msg["type"] = msg["type"]
            elif msg['role'] == self.config.assistant_name: # if the message is from an NPC
                if "name" not in msg: # support for role, content, and name messages
                    logging.info(f"Warning: Message from NPC does not contain name:",msg)
                formatted_msg = {
                    'role': self.config.assistant_name,
                    'name': msg['name'],
                    'content': msg['content'],
                }
                if "timestamp" in msg:
                    formatted_msg["timestamp"] = msg["timestamp"]
                if "location" in msg:
                    formatted_msg["location"] = msg["location"]
                if "type" in msg:
                    formatted_msg["type"] = msg["type"]
            else: # support for just role and content messages - depreciated
                formatted_msg = {
                    'role': msg['role'],
                    'content': msg['content'],
                }
                if "timestamp" in msg:
                    formatted_msg["timestamp"] = msg["timestamp"]
                if "location" in msg:
                    formatted_msg["location"] = msg["location"]
                if "type" in msg:
                    formatted_msg["type"] = msg["type"]

            formatted_messages.append(formatted_msg)
        return formatted_messages
    
    def generate_response(self):
        """Generate response from LLM one text chunk at a time"""
        for chunk in self.acreate(self.get_context()):
            yield chunk

    async def process_response(self, sentence_queue, event):
        """Stream response from LLM one sentence at a time"""

        next_author = None # used to determine who is speaking next in a conversation
        verified_author = False # used to determine if the next author has been verified
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
        logging.debug("Player Aliases:",possible_players)
        full_reply = '' # used to store the full reply
        sentence = '' # used to store the current sentence being generated
        next_sentence = '' # used to store the next sentence being generated
        voice_line = '' # used to store the current voice line being generated
        num_sentences = 0 # used to keep track of how many sentences have been generated
        voice_line_sentences = 0 # used to keep track of how many sentences have been generated for the current voice line
        retries = 5
        bad_author_retries = 5
        system_loop = 3
        logging.info(f"Signifier: {self.config.message_signifier}")
        logging.info(f"Format: {self.config.message_format}")
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
                start_time = time.time()
                last_chunk = None
                same_chunk_count = 0
                for chunk in self.generate_response():
                    # TODO: This is a temporary fix. The LLM class should be returning a string only, but some inference engines don't currently. This will be fixed in the future.
                    print(chunk)
                    print(type(chunk))
                    if type(chunk) == dict:
                        logging.info(chunk)
                        content = chunk['choices'][0]['text']
                    elif type(chunk) == str:
                        logging.info(chunk)
                        content = chunk
                    else:
                        logging.info(chunk.model_dump_json())
                        if "text" in chunk.choices[0]:
                            content = chunk.choices[0].text
                        else:
                            content = chunk.choices[0].delta.content

                    if content is not last_chunk: # if the content is not the same as the last chunk, then the LLM is not stuck in a loop and the generation should continue
                        last_chunk = content
                        same_chunk_count = 0
                    else: # if the content is the same as the last chunk, then the LLM is probably stuck in a loop and the generation should stop
                        same_chunk_count += 1
                        if same_chunk_count > self.config.same_output_limit:
                            logging.info(f"Same chunk returned {same_chunk_count} times in a row. Stopping generation.")
                            break
                    if content is not None and content != '':
                        sentence += content # add the content to the sentence in progress
                        if next_author is None: # if next_author is None, then extract it from the start of the generation
                            if self.config.message_signifier in sentence: # if the message signifier is in the sentence, then the next author is the first part of the sentence
                                next_author = sentence.split(self.config.message_signifier)[0] # extract the next author from the start of the generation

                                # Fix capitalization - First letter after spaces and dashes should be capitalized
                                next_author_parts = next_author.split(" ")
                                next_author_parts = [part.split("-") for part in next_author_parts]
                                new_next_author = ""
                                for part_list in next_author_parts:
                                    new_part_list = []
                                    for part in part_list:
                                        if part.lower() == "the":
                                            new_part_list.append(part.lower())
                                        else:
                                            new_part_list.append(part.capitalize())
                                    new_next_author += "-".join(new_part_list) + " "
                                
                                next_author = new_next_author.strip()

                                sentence = sentence[len(next_author)+len(self.config.message_signifier):] # remove the author from the sentence
                                logging.info(f"next_author detected as: {next_author}")
                        if  next_author is not None and verified_author == False: # if next_author is not None, then verify that the next author is correct
                            player_author = False
                            possible_NPCs = list(self.conversation_manager.character_manager.active_characters.keys())
                            for possible_player in possible_players:
                                if (next_author.strip() in possible_player or next_author.lower().strip() in possible_player) and (next_author.strip() not in possible_NPCs and next_author.lower().strip() not in possible_NPCs):
                                    player_author = True
                                    break
                            if player_author: # if the next author is the player, then the player is speaking and generation should stop, but only if the conversation is not radiant
                                if self.conversation_manager.radiant_dialogue:
                                    logging.info(f"Player detected, but not allowed to speak in radiant dialogue. Retrying...")
                                    retries += 1
                                    raise Exception('Invalid author')
                                else:
                                    logging.info(f"Player is speaking. Stopping generation.")
                                    break
                            if next_author.lower() == self.config.system_name.lower() and system_loop > 0: # if the next author is the system, then the system is speaking and generation should stop
                                logging.info(f"System detected. Retrying...")
                                system_loop -= 1
                                retries += 1
                                raise Exception('Invalid author')
                            elif (next_author == self.config.system_name or next_author.lower() == self.config.system_name.lower()) and system_loop == 0: # if the next author is the system, then the system is speaking and generation should stop
                                logging.info(f"System Loop detected. Please report to #dev channel in the Mantella Discord. Stopping generation.")
                                if len(self.conversation_manager.messages) == 0:
                                    logging.info(f"System Loop started at the first message.")
                                break
                            if (next_author in self.conversation_manager.character_manager.active_characters): # if the next author is a real character that's active in this conversation, then switch to that character
                                #TODO: or (any(key.split(' ')[0] == keyword_extraction for key in characters.active_characters))
                                logging.info(f"Switched to {next_author}")
                                self.conversation_manager.game_interface.active_character = self.conversation_manager.character_manager.active_characters[next_author]
                                # self.conversation_manager.game_interface.active_character.set_voice()
                                # characters are mapped to say_line based on order of selection
                                # taking the order of the dictionary to find which say_line to use, but it is bad practice to use dictionaries in this way
                                self.conversation_manager.game_interface.character_num = list(self.conversation_manager.character_manager.active_characters.keys()).index(next_author) # Assigns a number to the character based on the order they were selected for use in the _mantella_say_line_# filename
                                verified_author = True
                            else: # if the next author is not a real character, then assume the player is speaking and generation should stop
                                partial_match = False
                                for character in self.conversation_manager.character_manager.active_characters.values(): # check if the next author is a partial match to any of the active characters
                                    if next_author in character.name.split(" "):
                                        partial_match = character
                                        break
                                if partial_match != False: # if the next author is a partial match to an active character, then switch to that character
                                    logging.info(f"Switched to {partial_match.name} (WARNING: Partial match!)")
                                    self.conversation_manager.game_interface.active_character = partial_match
                                    self.conversation_manager.game_interface.character_num = list(self.conversation_manager.character_manager.active_characters.keys()).index(partial_match.name)
                                    verified_author = True
                                else: # if the next author is not a real character, then assume the player is speaking and generation should stop
                                    logging.info(f"Next author is not a real character: {next_author}")
                                    logging.info(f"Retrying...")
                                    retries += 1
                                    raise Exception('Invalid author')
                            
                        if next_author is not None and verified_author == True: # if next_author is not None and verified_author is True, then the next author is correct and generation should continue
                            bad_author_retries = 5

                        content_edit = unicodedata.normalize('NFKC', content) # normalize unicode characters
                        
                        if (any(char in content_edit for char in self.end_of_sentence_chars)) or (any(char in content for char in self.banned_chars)) or (self.EOS_token in sentence): # check if content marks the end of a sentence
                            if next_author is None: # if next_author is None after generating a sentence, then there was an error generating the output. The LLM didn't choose a character to speak next.
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
                            has_grammer_ending = False
                            for char in self.end_of_sentence_chars:
                                if char in content_edit:
                                    has_grammer_ending = char
                                    break
                            if has_grammer_ending != False:
                                sentence, next_sentence = sentence.split(has_grammer_ending, 1)
                                sentence = sentence + has_grammer_ending
                            sentence = self.clean_sentence(sentence) # clean the sentence
                            if sentence.replace(".", "").replace("?", "").replace("!", "").replace(",", "").strip() == '' and sentence != "...": # if the sentence is empty after cleaning, then skip it - unless it's an ellipsis
                                logging.info(f"Skipping empty sentence")
                                if full_reply.strip() == '':
                                    retries += 1
                                    logging.info(f"Retrying due to empty response")
                                    raise Exception('Empty sentence')
                                break

                            if self.config.assist_check: # if remote, check if the response contains the word assist for some reason. Probably some OpenAI nonsense.
                                if ('assist' in sentence) and (num_sentences>0): # Causes problems if asking a follower if you should "assist" someone, if they try to say something along the lines of "Yes, we should assist them." it will cut off the sentence and basically ignore the player. TODO: fix this with a more robust solution
                                    logging.info(f"'assist' keyword found. Ignoring sentence which begins with: {sentence}") 
                                    break # stop generating response

                            logging.info(f"LLM returned sentence took {time.time() - start_time} seconds to execute")

                            if ":" in sentence: # if a colon is in the sentence, then the NPC is calling a keyword function in addition to speaking. Pass the keyword to the behavior manager to see if it matches any real keywords
                                keyword_extraction = sentence.split(':')[0].strip()
                                sentence = sentence.split(':')[1]
                                # if LLM is switching character
                                sentence_behavior = self.conversation_manager.behavior_manager.evaluate(keyword_extraction, self.conversation_manager.game_interface.active_character, sentence) # check if the sentence contains any behavior keywords for NPCs
                                if sentence_behavior == None:
                                    logging.warn(f"Keyword '{keyword_extraction}' not found in behavior_manager. Disgarding from response.")
                                    
                            eos = False 
                            if self.EOS_token in sentence:
                                sentence = sentence.split(self.EOS_token)[0]
                                logging.info(f"EOS token found in sentence. Trimming last sentence to: {sentence}")
                                eos = True


                            voice_line = voice_line.strip() + " " + sentence.strip() # add the sentence to the voice line in progress
                            full_reply = full_reply.strip() + " " + sentence.strip() # add the sentence to the full reply
                            num_sentences += 1 # increment the total number of sentences generated
                            voice_line_sentences += 1 # increment the number of sentences generated for the current voice line


                            self.conversation_manager.behavior_manager.pre_sentence_evaluate(self.conversation_manager.game_interface.active_character, sentence,) # check if the sentence contains any behavior keywords for NPCs
                            if voice_line_sentences == self.config.sentences_per_voiceline: # if the voice line is ready, then generate the audio for the voice line
                                logging.info(f"Generating voiceline: \"{voice_line.strip()}\" for {self.conversation_manager.game_interface.active_character.name}.")
                                if self.config.strip_smalls and len(voice_line.strip()) < self.config.small_size:
                                    logging.info(f"Skipping small voice line: {voice_line}")
                                    break
                                await self.generate_voiceline(voice_line.strip(), sentence_queue, event)
                                voice_line_sentences = 0 # reset the number of sentences generated for the current voice line
                                voice_line = '' # reset the voice line for the next iteration
                            self.conversation_manager.behavior_manager.post_sentence_evaluate(self.conversation_manager.game_interface.active_character, sentence) # check if the sentence contains any behavior keywords for NPCs

                            if next_sentence != '': # if there is a next sentence, then set the current sentence to the next sentence
                                sentence = next_sentence
                                next_sentence = ''
                            else:
                                sentence = '' # reset the sentence for the next iteration
                                next_sentence = ''

                            radiant_dialogue_update = self.conversation_manager.game_interface.is_radiant_dialogue() # check if the conversation has switched from radiant to multi NPC
                            # stop processing LLM response if:
                            # max_response_sentences reached (and the conversation isn't radiant)
                            # conversation has switched from radiant to multi NPC (this allows the player to "interrupt" radiant dialogue and include themselves in the conversation)
                            # the conversation has ended
                            if ((num_sentences >= self.max_response_sentences) and not self.conversation_manager.radiant_dialogue) or (self.conversation_manager.radiant_dialogue and not radiant_dialogue_update) or self.conversation_manager.game_interface.is_conversation_ended() or eos: # if the conversation has ended, stop generating responses
                                break
                break
            except Exception as e:
                next_author = None
                verified_author = False
                sentence = ''
                voice_line = ''
                full_reply = ''
                if retries == 0:
                    logging.error(f"Could not connect to LLM API\nError:")
                    logging.error(e)
                    input('Press enter to continue...')
                    raise e
                logging.error(f"LLM API Error: {e}")
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

            if num_sentences == 0: # if no sentences were generated, then the LLM failed to generate a response
                logging.error(f"LLM failed to generate a response or a valid Author. Retrying...")
                retries += 1
                continue

        if voice_line_sentences > 0: # if the voice line is not empty, then generate the audio for the voice line
            logging.info(f"Generating voiceline: \"{voice_line.strip()}\" for {self.conversation_manager.game_interface.active_character.name}.")
            await self.generate_voiceline(voice_line, sentence_queue, event)
            voice_line_sentences = 0
            voice_line = ''

        await sentence_queue.put(None) # Mark the end of the response for self.conversation_manager.game_interface.send_response() and self.conversation_manager.game_interface.send_response()

        full_reply = full_reply.strip()
        try: 
            if sentence_behavior != None:
                full_reply = sentence_behavior.keyword + ": " + full_reply.strip() # add the keyword back to the sentence to reinforce to the that the keyword was used to trigger the bahavior
        except:
            pass

        if next_author is not None and full_reply != '':
            self.conversation_manager.new_message({"role": self.config.assistant_name, 'name':next_author, "content": full_reply})
            # -- for each sentence for each character until the conversation ends or the max_response_sentences is reached or the player is speaking
            logging.info(f"Full response saved ({self.tokenizer.get_token_count(full_reply)} tokens): {full_reply}")

    async def generate_voiceline(self, string, sentence_queue, event):
        """Generate audio for a voiceline"""
        # Generate the audio and return the audio file path
        try:
            audio_file = self.conversation_manager.synthesizer.synthesize(string, self.conversation_manager.game_interface.active_character)
        except Exception as e:
            logging.error(f"TTS Error: {e}")
            logging.info(e)
            input('Press enter to continue...')
            raise e

        await sentence_queue.put([audio_file, string]) # Put the audio file path in the sentence_queue
        event.clear() # clear the event for the next iteration
        await event.wait() # wait for the event to be set before generating the next line