print("Importing base_LLM.py")
from src.logging import logging, time
import src.utils as utils
import re
import unicodedata
import time
import random
logging.info("Imported required libraries in base_LLM.py")

inference_engine_name = "base_LLM"
tokenizer_slug = "tiktoken" # default to tiktoken for now (Not always correct, but it's the fastest tokenizer and it works for openai's models, which a lot of users will be relying on probably)
class base_LLM():
    def __init__(self, conversation_manager):
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config
        self.tokenizer = None
        
        self.inference_engine_name = inference_engine_name
        self.tokenizer_slug = tokenizer_slug

        self.max_response_sentences = self.config.max_response_sentences
        self.end_of_sentence_chars = self.config.end_of_sentence_chars
        self.end_of_sentence_chars = [unicodedata.normalize('NFKC', char) for char in self.end_of_sentence_chars]
        self.banned_chars = self.config.banned_chars
        self.banned_chars.append(self.config.message_separator)
        self.banned_chars.append(self.config.EOS_token)
        self.banned_chars.append(self.config.BOS_token)
        if not self.config.allow_npc_roleplay:
            self.banned_chars.append("*") # prevent NPCs from using custom game events via asterisk RP actions
        self.banned_chars = [char for char in self.banned_chars if char != '']
        self.end_of_sentence_chars = [char for char in self.end_of_sentence_chars if char != '']

        self.prompt_style = "normal"
        self.type = "normal"
        self.is_local = True
    
    @property
    def behavior_style(self):
        return self.config._behavior_style

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

    def acreate(self, messages, message_prefix="", force_speaker=None, banned_chars=[]): # Creates a completion stream for the messages provided to generate a speaker and their response
        """Generate a streameed response from the LLM using the messages provided"""
        logging.info(f"Warning: Using base_LLM.acreate() instead of a child class, this is probably not what you want to do. Please override this method in your child class!")
        input("Press enter to continue...")
        raise NotImplementedError("Please override this method in your child class!")
    
    def clean_sentence(self, sentence, eos=False):
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

            # if '(' in sentence or ')' in sentence:
            #     # Check if sentence contains two brackets
            #     bracket_check = re.search(r"\(.*\)", sentence)
            #     if bracket_check:
            #         logging.info(f"Removed brackets text from response: {sentence}")
            #         # Remove text between brackets
            #         sentence = re.sub(r"\(.*?\)", "", sentence)
            #     else:
            #         logging.info(f"Removed response containing single brackets: {sentence}")
            #         sentence = ''

            return sentence
        
        if 'Well, well, well' in sentence:
            sentence = sentence.replace('Well, well, well', 'Well well well')

        if self.config.as_a_check:
            sentence = remove_as_a(sentence)
        sentence = sentence.replace('"','')
        # if not eos:
        #     sentence = sentence.replace("<", "")
        #     sentence = sentence.replace(">", "")
        # models sometimes get the idea in their head to use double asterisks **like this** in sentences instead of single
        # this converts double asterisks to single so that they can be filtered out or included appropriately
        while "**" in sentence:
            sentence = sentence.replace('**','*')
        if not self.config.allow_npc_roleplay:
            sentence = parse_asterisks_brackets(sentence)
        sentence = unicodedata.normalize('NFKC', sentence)
        sentence = sentence.strip()
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
                        'name': msg['name'] if "name" in msg else self.player_name,
                        'content': msg['content'],
                    }
                    if msg["name"] == "[player]":
                        formatted_msg["name"] = self.player_name
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
                        'name': msg['name'] if "name" in msg else perspective_player_name,
                        'content': msg['content'],
                    }
                    if msg["name"] == "[player]":
                        formatted_msg["name"] = perspective_player_name
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
    
    def generate_response(self, message_prefix="", force_speaker=None, banned_chars=[]):
        """Generate response from LLM one text chunk at a time"""
        for chunk in self.acreate(self.get_context(), message_prefix=message_prefix, force_speaker=force_speaker, banned_chars=banned_chars):
            yield chunk
        
    def format_content(self, chunk):
        # TODO: This is a temporary fix. The LLM class should be returning a string only, but some inference engines don't currently. This will be fixed in the future.
        if type(chunk) == dict:
            logging.info(chunk)
            content = chunk['choices'][0]['text']
        elif type(chunk) == str:
            logging.info(chunk)
            content = chunk
        else:
            logging.info(chunk.model_dump_json())
            content = None
            try:
                content = chunk.choices[0].text
            except:
                pass
            try:
                content = chunk.choices[0].delta.content
            except:
                pass
        return content
    
    def split_and_preverse_strings_on_end_of_sentence(self, sentence, next_sentence=""):
        has_grammer_ending = False
        for char in self.end_of_sentence_chars:
            if char in sentence:
                has_grammer_ending = char
                break
        if has_grammer_ending != False:
            logging.info(f"Splitting sentence at: {has_grammer_ending}")
            if "..." in sentence:
                has_grammer_ending = "..."
            sentence_parts = sentence.split(has_grammer_ending, 1)
            sentence = sentence_parts[0]
            next_sentence += sentence_parts[1]
            sentence += has_grammer_ending
        sentence = sentence.strip()
        next_sentence = next_sentence.strip()
        if len(next_sentence) > 2:
            if self.config.assure_grammar and not has_grammer_ending:
                logging.info(f"Assuring grammar by adding period to the end of the sentence")
                sentence += "." # add a period to the end of the sentence if it doesn't already have one
        return sentence, next_sentence

    async def process_response(self, sentence_queue, event, force_speaker=None):
        """Stream response from LLM one sentence at a time"""
        logging.info(f"Processing response...")
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
        possible_players = list(set(possible_players)) # remove duplicates
        logging.info("Possible Player Aliases:",possible_players)
        
        proposed_next_author = '' # used to store the proposed next author
        raw_reply = '' # used to store the raw reply
        full_reply = '' # used to store the full reply

        voice_line = '' # used to store the current voice line being generated
        sentence = '' # used to store the current sentence being generated
        next_sentence = '' # used to store the next sentence being generated
        next_speaker_sentence = '' # used to store the next speaker's sentence
        
        num_sentences = 0 # used to keep track of how many sentences have been generated total
        voice_line_sentences = 0 # used to keep track of how many sentences have been generated for the current voice line
        send_voiceline = False # used to determine if the current sentence should be sent early
        
        retries = 5
        bad_author_retries = 5
        system_loop = 3
        
        logging.info(f"Signifier: {self.config.message_signifier}")
        logging.info(f"Format: {self.config.message_format}")

        symbol_insert=""
        if self.config.first_message_hidden_quote:
            symbol_insert = "\""
        elif self.config.first_message_hidden_asterisk:
            symbol_insert = "*"
        elif self.config.first_message_hidden_quote and self.config.first_message_hidden_asterisk:
            symbol_insert = random.choice(["\"","*"])
        logging.info(f"Symbol Insert: {symbol_insert}")
        asterisk_open = False # If asterisk is open, then end the voiceline early and start a new one for the narrator. This is used to allow the narrator to speak in the middle of a sentence.
        if symbol_insert == "*":
            asterisk_open = True
        if force_speaker is not None:
            logging.info(f"Forcing speaker to: {force_speaker.name}")
            next_author = force_speaker.name
            proposed_next_author = next_author
            verified_author = True
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
                beginning_of_sentence_time = time.time()
                last_chunk = None
                same_chunk_count = 0
                logging.info(f"Starting response generation...")
                for chunk in self.generate_response(message_prefix=symbol_insert, force_speaker=force_speaker, banned_chars=self.banned_chars):
                    eos = False 
                    content = self.format_content(chunk)
                    logging.info(f"Content: {content}")

                    if content is not last_chunk: # if the content is not the same as the last chunk, then the LLM is not stuck in a loop and the generation should continue
                        last_chunk = content
                        same_chunk_count = 0
                    else: # if the content is the same as the last chunk, then the LLM is probably stuck in a loop and the generation should stop
                        same_chunk_count += 1
                        if same_chunk_count > self.config.same_output_limit:
                            logging.info(f"Same chunk returned {same_chunk_count} times in a row. Stopping generation.")
                            break

                    if content is None:
                        continue
                    if self.EOS_token.lower() in raw_reply.lower():
                        logging.info(f"Sentence contains EOS token. Stopping generation.")
                        eos = True
                    
                    raw_reply += content
                    if next_author is None: # if next_author is None after generating a chunk of content, then the LLM didn't choose a character to speak next yet.
                        proposed_next_author += content
                        sentence, next_author, verified_author, retries, bad_author_retries, system_loop = self.check_author(proposed_next_author, next_author, verified_author, possible_players, retries, bad_author_retries, system_loop)
                    else:
                        sentence += content # add the content to the sentence in progress
                    
                    new_speaker = False
                    if "*" in content: # if the content contains an asterisk, then either the narrator has started speaking or the narrator has stopped speaking and the NPC is speaking
                        sentences = sentence.split("*", 1)
                        if len(sentences) == 2:
                            sentence, next_speaker_sentence = sentences[0], sentences[1]
                        else:
                            sentence = sentences[0]
                            new_sentence = ""
                        new_speaker = True

                    if eos:
                        sentence = sentence.split(self.EOS_token)[0]
                        raw_reply = raw_reply.split(self.EOS_token)[0]

                    if (any(char in unicodedata.normalize('NFKC', content) for char in self.end_of_sentence_chars)) or (any(char in content for char in self.banned_chars)) or eos or new_speaker: # check if content marks the end of a sentence
                        # if sentence.strip() == '':
                        #     if num_sentences == 0:
                        #         logging.info(f"Empty response. Retrying...")
                        #         retries += 1
                        #         raise Exception('Empty response')
                        #     else:
                        #         logging.info(f"Empty response. Stopping generation.")
                        #         break
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
                            
                        sentence, next_sentence = self.split_and_preverse_strings_on_end_of_sentence(sentence, next_sentence)
                            
                        if self.EOS_token in sentence or self.EOS_token in sentence.lower():
                            sentence = sentence.split(self.EOS_token)[0]
                            logging.info(f"EOS token found in sentence. Trimming last sentence to: {sentence}")
                            eos = True
                            
                        # grammarless_stripped_sentence = sentence.replace(".", "").replace("?", "").replace("!", "").replace(",", "").strip()
                        # if grammarless_stripped_sentence == '' and sentence != "...": # if the sentence is empty after cleaning, then skip it - unless it's an ellipsis
                        #     logging.info(f"Skipping empty sentence")
                        #     if num_sentences<1:
                        #         retries += 1
                        #         logging.info(f"Retrying due to empty response")
                        #         raise Exception('Empty sentence')
                        #     break

                        if self.config.assist_check: # if remote, check if the response contains the word assist for some reason. Probably some OpenAI nonsense.
                            if ('assist' in sentence) and (num_sentences>0): # Causes problems if asking a follower if you should "assist" someone, if they try to say something along the lines of "Yes, we should assist them." it will cut off the sentence and basically ignore the player. TODO: fix this with a more robust solution
                                logging.info(f"'assist' keyword found. Ignoring sentence which begins with: {sentence}") 
                                break # stop generating response

                        logging.info(f"LLM took {time.time() - beginning_of_sentence_time} seconds to generate sentence")


                        logging.info(f"Checking for behaviors using behavior style: {self.behavior_style}")
                        found_behaviors = []
                        if self.behavior_style["prefix"] in sentence:
                            sentence_words = sentence.split(" ")
                            new_sentence = ""
                            for word in sentence_words:
                                if self.behavior_style["prefix"] in word and self.behavior_style["suffix"] in word:
                                    new_behaviors = self.conversation_manager.behavior_manager.evaluate(word, self.conversation_manager.game_interface.active_character, sentence) # check if the sentence contains any behavior keywords for NPCs
                                    if len(new_behaviors) > 0:
                                        found_behaviors.extend(new_behaviors)
                                        logging.info(f"Behaviors triggered: {new_behaviors}")
                                elif self.behavior_style["prefix"] in word and not self.behavior_style["suffix"] in word: # if the word contains the prefix but not the suffix, then the suffix is probably in the next word, which is likely a format break.
                                    break
                                new_sentence += word + " "
                            sentence = new_sentence
                        if len(found_behaviors) == 0:
                            logging.warn(f"No behaviors triggered by sentence: {sentence}")
                        else:
                            for behavior in found_behaviors:
                                logging.info(f"Behavior triggered: {behavior.keyword}")
                                
                        for char in self.banned_chars:
                            if char in sentence:
                                eos = True
                                sentence = sentence.split(char)[0]
                        sentence = self.clean_sentence(sentence, eos) # clean the sentence

                        voice_line = voice_line.strip() + " " + sentence.strip() # add the sentence to the voice line in progress
                        if len(full_reply) > 0 and full_reply[-1] != "*": # if the full reply is not empty and the last character is not an asterisk, then add a space before the sentence
                            full_reply = full_reply.strip() + " " + sentence.strip() # add the sentence to the full reply
                        else:
                            full_reply = full_reply.strip() + sentence.strip()
                        if new_speaker: # if the content contains an asterisk, then either the narrator has started speaking or the narrator has stopped speaking and the NPC is speaking
                            if asterisk_open:
                                full_reply = full_reply.strip() + "* "
                            else:
                                full_reply = full_reply.strip() + " *"
                        num_sentences += 1 # increment the total number of sentences generated
                        voice_line_sentences += 1 # increment the number of sentences generated for the current voice line
                        
                        if new_speaker: # if the content contains an asterisk, then either the narrator has started speaking or the narrator has stopped speaking and the NPC is speaking
                            send_voiceline = True
                        
                        self.conversation_manager.behavior_manager.pre_sentence_evaluate(self.conversation_manager.game_interface.active_character, sentence,) # check if the sentence contains any behavior keywords for NPCs
                        if voice_line_sentences == self.config.sentences_per_voiceline: # if the voice line is ready, then generate the audio for the voice line
                            send_voiceline = True
                        grammarless_stripped_voice_line = voice_line.replace(".", "").replace("?", "").replace("!", "").replace(",", "").replace("-", "").strip()
                        if grammarless_stripped_voice_line == '': # if the voice line is empty, then the narrator is speaking
                            send_voiceline = False
                        if send_voiceline and asterisk_open and self.config.break_on_time_announcements:
                            if "*The time is now" in voice_line:
                                voice_line = voice_line.split("*The time is now")[0]
                                logging.info(f"Breaking on time announcement")
                                break
                        if send_voiceline: # if the voice line is ready, then generate the audio for the voice line
                            logging.info(f"Generating voiceline: \"{voice_line.strip()}\" for {self.conversation_manager.game_interface.active_character.name}.")
                            if self.config.strip_smalls and len(voice_line.strip()) < self.config.small_size:
                                logging.info(f"Skipping small voice line: {voice_line}")
                                break
                            voice_line = voice_line.replace('[', '(')
                            voice_line = voice_line.replace(']', ')')
                            voice_line = voice_line.replace('{', '(')
                            voice_line = voice_line.replace('}', ')')
                            # remove any parentheses groups from the voiceline.
                            voice_line = re.sub(r'\([^)]*\)', '', voice_line)
                            if asterisk_open: # if the asterisk is open, then the narrator is speaking
                                time.sleep(self.config.narrator_delay)
                                self.conversation_manager.synthesizer._say(voice_line.strip(), self.config.narrator_voice, self.config.narrator_volume)
                            else:
                                await self.generate_voiceline(voice_line.strip(), sentence_queue, event)
                            voice_line_sentences = 0 # reset the number of sentences generated for the current voice line
                            voice_line = '' # reset the voice line for the next iteration
                        self.conversation_manager.behavior_manager.post_sentence_evaluate(self.conversation_manager.game_interface.active_character, sentence) # check if the sentence contains any behavior keywords for NPCs

                        if new_speaker: # if the content contains an asterisk, then either the narrator has started speaking or the narrator has stopped speaking and the NPC is speaking
                            grammarless_stripped_next_speaker_sentence = next_speaker_sentence.replace(".", "").replace("?", "").replace("!", "").replace(",", "").strip()
                            if grammarless_stripped_next_speaker_sentence != '': # if there is a next speaker's sentence, then set the current sentence to the next speaker's sentence
                                sentence = next_speaker_sentence
                                next_speaker_sentence = ''
                            else:
                                sentence = '' # reset the sentence for the next iteration
                            next_sentence = '' # reset the next sentence for the next iteration
                            asterisk_open = not asterisk_open
                        else:
                            grammarless_stripped_next_sentence = next_sentence.replace(".", "").replace("?", "").replace("!", "").replace(",", "").strip()
                            if grammarless_stripped_next_sentence != '': # if there is a next sentence, then set the current sentence to the next sentence
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
                        new_speaker = False
                        send_voiceline = False
                        if ((num_sentences >= self.max_response_sentences) and not self.conversation_manager.radiant_dialogue) or (self.conversation_manager.radiant_dialogue and not radiant_dialogue_update) or self.conversation_manager.game_interface.is_conversation_ended() or eos: # if the conversation has ended, stop generating responses
                            logging.info(f"Response generation complete. Stopping generation.")
                            break
                logging.info(f"LLM response took {time.time() - start_time} seconds to execute")
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

            if num_sentences == 0: # if no sentences were generated, then the LLM failed to generate a response
                logging.error(f"LLM failed to generate a response or a valid Author. Retrying...")
                retries += 1
                continue

        if voice_line_sentences > 0: # if the voice line is not empty, then generate the audio for the voice line
            logging.info(f"Generating voiceline: \"{voice_line.strip()}\" for {self.conversation_manager.game_interface.active_character.name}.")
            if asterisk_open: # if the asterisk is open, then the narrator is speaking
                time.sleep(self.config.narrator_delay)
                self.conversation_manager.synthesizer._say(voice_line.strip(), self.config.narrator_voice, self.config.narrator_volume)
            else:
                await self.generate_voiceline(voice_line.strip(), sentence_queue, event)
            voice_line_sentences = 0
            voice_line = ''

        await sentence_queue.put(None) # Mark the end of the response for self.conversation_manager.game_interface.send_response() and self.conversation_manager.game_interface.send_response()

        full_reply = full_reply.strip()
        # try: 
        #     if sentence_behavior != None:
        #         full_reply = sentence_behavior.keyword + ": " + full_reply.strip() # add the keyword back to the sentence to reinforce to the that the keyword was used to trigger the bahavior
        # except:
        #     pass

        if next_author is not None and full_reply != '':
            self.conversation_manager.new_message({"role": self.config.assistant_name, 'name':next_author, "content": full_reply})
            # -- for each sentence for each character until the conversation ends or the max_response_sentences is reached or the player is speaking
            logging.info(f"Full response saved ({self.tokenizer.get_token_count(full_reply)} tokens): {full_reply}")

    def check_author(self, proposed_next_author, next_author, verified_author, possible_players, retries, bad_author_retries, system_loop):
        """Check the author of the next sentence"""
        sentence = ''
        if next_author is None:
            if self.config.message_signifier in proposed_next_author:
                logging.info(f"Message signifier detected in sentence: {proposed_next_author}")
                next_author = proposed_next_author.split(self.config.message_signifier)[0]
                logging.info(f"next_author possibly detected as: {next_author}")

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
                sentence = proposed_next_author[len(next_author)+len(self.config.message_signifier):]
                logging.info(f"next_author detected as: {next_author}")
                if verified_author == False:
                    player_author = False
                    possible_NPCs = list(self.conversation_manager.character_manager.active_characters.keys())
                    for possible_player in possible_players:
                        if (next_author.strip() in possible_player or next_author.lower().strip() in possible_player) and (next_author.strip() not in possible_NPCs and next_author.lower().strip() not in possible_NPCs):
                            player_author = True
                            break
                    if player_author:
                        if self.conversation_manager.radiant_dialogue:
                            logging.info(f"Player detected, but not allowed to speak in radiant dialogue. Retrying...")
                            retries += 1
                            raise Exception('Invalid author')
                        else:
                            logging.info(f"Player is speaking. Stopping generation.")
                            return next_author, verified_author, retries, bad_author_retries, system_loop
                    if next_author.lower() == self.config.system_name.lower() and system_loop > 0:
                        logging.info(f"System detected. Retrying...")
                        system_loop -= 1
                        retries += 1
                        raise Exception('Invalid author')
                    elif (next_author == self.config.system_name or next_author.lower() == self.config.system_name.lower()) and system_loop == 0:
                        logging.info(f"System Loop detected. Please report to #dev channel in the Pantella Discord. Stopping generation.")
                        return next_author, verified_author, retries, bad_author_retries, system_loop

                    logging.info(f"Candidate next author: {next_author}")
                    if (next_author in self.conversation_manager.character_manager.active_characters):
                        logging.info(f"Switched to {next_author}")
                        self.conversation_manager.game_interface.active_character = self.conversation_manager.character_manager.active_characters[next_author]
                        self.conversation_manager.game_interface.character_num = list(self.conversation_manager.character_manager.active_characters.keys()).index(next_author)
                        verified_author = True
                        bad_author_retries = 5
                        logging.info(f"Active Character: {self.conversation_manager.game_interface.active_character.name}")
                    else:
                        partial_match = False
                        for character in self.conversation_manager.character_manager.active_characters.values():
                            if next_author in character.name.split(" "):
                                partial_match = character
                                break
                        if partial_match != False:
                            logging.info(f"Switched to {partial_match.name} (WARNING: Partial match!)")
                            self.conversation_manager.game_interface.active_character = partial_match
                            self.conversation_manager.game_interface.character_num = list(self.conversation_manager.character_manager.active_characters.keys()).index(partial_match.name)
                            verified_author = True
                            bad_author_retries = 5
                            logging.info(f"Active Character: {self.conversation_manager.game_interface.active_character.name}")
                        else:
                            logging.info(f"Next author is not a real character: {next_author}")
                            logging.info(f"Retrying...")
                            retries += 1
                            raise Exception('Invalid author')
        return sentence, next_author, verified_author, retries, bad_author_retries, system_loop

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