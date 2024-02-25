from src.logging import logging, time
import src.utils as utils
import re
import unicodedata
import random

inference_engine_name = "base_LLM"
tokenizer_slug = "tiktoken" # default to tiktoken for now (Not always correct, but it's the fastest tokenizer and it works for openai's models, which a lot of users will be relying on probably)
class base_LLM():
    def __init__(self, conversation_manager):
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config
        self.tokenizer = None
        self.token_limit = self.conversation_manager.token_limit
        self.language_info = self.conversation_manager.language_info
        
        self.inference_engine_name = inference_engine_name
        self.tokenizer_slug = tokenizer_slug

        self.max_response_sentences = self.config.max_response_sentences
        self.end_of_sentence_chars = ['.', '?', '!']
        self.end_of_sentence_chars = [unicodedata.normalize('NFKC', char) for char in self.end_of_sentence_chars]
        self.banned_chars = ['*', '(', ')', '[', ']', '{', '}', "\"" ]

        self.prompt_style = "normal"

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

    # the string printed when your print() this object
    def __str__(self):
        return f"{self.inference_engine_name} LLM"
    
    @utils.time_it
    def chatgpt_api(self, input_text, messages): # Creates a synchronouse completion for the messages provided to generate response for the assistant to the user. TODO: remove later
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
        logging.info(f"Warning: Using base_LLM.create() instead of a child class, this is probably not what you want to do. Please override this method in your child class!")
        pass

    def acreate(self, messages): # Creates a completion stream for the messages provided to generate a speaker and their response
        logging.info(f"Warning: Using base_LLM.acreate() instead of a child class, this is probably not what you want to do. Please override this method in your child class!")
        pass
    
    def clean_sentence(self, sentence):
        logging.info(f"Cleaning sentence: {sentence}")
        def remove_as_a(sentence):
            """Remove 'As an XYZ,' from beginning of sentence"""
            if sentence.startswith('As a'):
                if ', ' in sentence:
                    logging.info(f"Removed '{sentence.split(', ')[0]} from response")
                    sentence = sentence.replace(sentence.split(', ')[0]+', ', '')
            return sentence
        
        def parse_asterisks_brackets(sentence):
            if ('*' in sentence):
                # Check if sentence contains two asterisks
                asterisk_check = re.search(r"(?<!\*)\*(?!\*)[^*]*\*(?!\*)", sentence)
                if asterisk_check:
                    logging.info(f"Removed asterisks text from response: {sentence}")
                    # Remove text between two asterisks
                    sentence = re.sub(r"(?<!\*)\*(?!\*)[^*]*\*(?!\*)", "", sentence)
                else:
                    logging.info(f"Removed response containing single asterisks: {sentence}")
                    sentence = ''

            if ('(' in sentence) or (')' in sentence):
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
        
        if ('Well, well, well' in sentence):
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

        logging.info(f"Cleaned sentence: {sentence}")
        return sentence

    def get_context(self):
        return self.conversation_manager.get_context()

    async def process_response(self, sentence_queue, event):
        """Stream response from LLM one sentence at a time"""

        full_reply = '' # used to store the full reply
        next_author = None # used to determine who is speaking next in a conversation
        verified_author = False # used to determine if the next author has been verified
        verified_author = False # used to determine if the next author has been verified
        possible_players = [
            "A stranger",
            "A traveler",
            "a stranger",
            "a Stranger",
            "A Stranger",
            "a traveler",
            "Stranger",
            "stranger",
            "Traveler",
            "traveler",
            self.conversation_manager.player_name,
            self.conversation_manager.player_name.lower(),
            self.conversation_manager.player_name.upper(),
        ]
        possible_players.extend(self.conversation_manager.player_name.split(" "))
        possible_players.extend(self.conversation_manager.player_name.lower().split(" "))
        possible_players.extend(self.conversation_manager.player_name.upper().split(" "))
        sentence = '' # used to store the current sentence being generated
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
            #     self.conversation_manager.messages.append({"role": next_author, "content": full_reply})
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
                for chunk in self.acreate(self.get_context()):

                    # TODO: This is a temporary fix. The LLM class should be returning a string only, but some inference engines don't currently. This will be fixed in the future.
                    if type(chunk) == dict:
                        logging.info(chunk)
                        content = chunk['choices'][0]['text']
                    elif type(chunk) == str:
                        logging.info(chunk)
                        content = chunk
                    else:
                        logging.info(chunk.model_dump_json())
                        content = chunk.choices[0].text

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
                            for possible_player in possible_players:
                                if next_author.strip() in possible_player:
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
                            elif next_author == self.config.system_name and system_loop == 0: # if the next author is the system, then the system is speaking and generation should stop
                                logging.info(f"System Loop detected. Please report to #dev channel in the Mantella Discord. Stopping generation.")
                                if len(self.conversation_manager.messages) == 0:
                                    logging.info(f"System Loop started at the first message.")
                                break
                            if (next_author in self.conversation_manager.character_manager.active_characters): # if the next author is a real character that's active in this conversation, then switch to that character
                                #TODO: or (any(key.split(' ')[0] == keyword_extraction for key in characters.active_characters))
                                logging.info(f"Switched to {next_author}")
                                self.conversation_manager.chat_manager.active_character = self.conversation_manager.character_manager.active_characters[next_author]
                                self.conversation_manager.chat_manager.active_character.set_voice()
                                # characters are mapped to say_line based on order of selection
                                # taking the order of the dictionary to find which say_line to use, but it is bad practice to use dictionaries in this way
                                self.conversation_manager.chat_manager.character_num = list(self.conversation_manager.character_manager.active_characters.keys()).index(next_author) # Assigns a number to the character based on the order they were selected for use in the _mantella_say_line_# filename
                                verified_author = True
                            else: # if the next author is not a real character, then assume the player is speaking and generation should stop
                                partial_match = False
                                for character in self.conversation_manager.character_manager.active_characters.values(): # check if the next author is a partial match to any of the active characters
                                    if next_author in character.name.split(" "):
                                        partial_match = character
                                        break
                                if partial_match != False: # if the next author is a partial match to an active character, then switch to that character
                                    logging.info(f"Switched to {partial_match.name} (WARNING: Partial match!)")
                                    self.conversation_manager.chat_manager.active_character = partial_match
                                    self.conversation_manager.chat_manager.character_num = list(self.conversation_manager.character_manager.active_characters.keys()).index(partial_match.name)
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

                            sentence = self.clean_sentence(sentence) # clean the sentence
                            if sentence.strip() == '': # if the sentence is empty after cleaning, then skip it
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

                            if self.config.strip_smalls and len(sentence.strip()) < self.config.small_size:
                                logging.info(f"Skipping small sentence: {sentence}")
                                break

                            logging.info(f"LLM returned sentence took {time.time() - start_time} seconds to execute")

                            if ":" in sentence: # if a colon is in the sentence, then the NPC is calling a keyword function in addition to speaking. Pass the keyword to the behavior manager to see if it matches any real keywords
                                keyword_extraction = sentence.split(':')[0]
                                sentence = sentence.split(':')[1]
                                # if LLM is switching character
                                behavior = self.conversation_manager.behavior_manager.evaluate(keyword_extraction, self.conversation_manager.chat_manager.active_character, sentence) # check if the sentence contains any behavior keywords for NPCs
                                if behavior == None:
                                    logging.warn(f"Keyword '{keyword_extraction}' not found in behavior_manager. Disgarding from response.")
                                    
                            eos = False
                            if self.EOS_token in sentence:
                                sentence = sentence.split(self.EOS_token)[0]
                                logging.info(f"EOS token found in sentence. Trimming last sentence to: {sentence}")
                                eos = True


                            voice_line += sentence # add the sentence to the voice line in progress
                            full_reply += sentence # add the sentence to the full reply
                            num_sentences += 1 # increment the total number of sentences generated
                            voice_line_sentences += 1 # increment the number of sentences generated for the current voice line


                            behavior = self.conversation_manager.behavior_manager.pre_sentence_evaluate(self.conversation_manager.chat_manager.active_character, sentence,) # check if the sentence contains any behavior keywords for NPCs
                            if voice_line_sentences == self.config.sentences_per_voiceline: # if the voice line is ready, then generate the audio for the voice line
                                await self.generate_voiceline(voice_line, sentence_queue, event)
                                voice_line_sentences = 0 # reset the number of sentences generated for the current voice line
                                voice_line = '' # reset the voice line for the next iteration
                            behavior = self.conversation_manager.behavior_manager.post_sentence_evaluate(self.conversation_manager.chat_manager.active_character, sentence) # check if the sentence contains any behavior keywords for NPCs

                            sentence = '' # reset the sentence for the next iteration

                            end_conversation = self.conversation_manager.game_state_manager.load_conversation_ended() # check if the conversation has ended
                            radiant_dialogue_update = self.conversation_manager.game_state_manager.load_radiant_dialogue() # check if the conversation has switched from radiant to multi NPC
                            # stop processing LLM response if:
                            # max_response_sentences reached (and the conversation isn't radiant)
                            # conversation has switched from radiant to multi NPC (this allows the player to "interrupt" radiant dialogue and include themselves in the conversation)
                            # the conversation has ended
                            if ((num_sentences >= self.max_response_sentences) and not self.conversation_manager.radiant_dialogue) or (self.conversation_manager.radiant_dialogue and not radiant_dialogue_update) or end_conversation or eos: # if the conversation has ended, stop generating responses
                                break
                break
            except Exception as e:
                next_author = None
                verified_author = False
                sentence = ''
                full_reply = ''
                if retries == 0:
                    logging.error(f"Could not connect to LLM API\nError:")
                    logging.error(e)
                    input('Press enter to continue...')
                    exit()
                logging.error(f"LLM API Error: {e}")
                if 'Invalid author' in str(e):
                    logging.info(f"Retrying without saying error voice line")
                    retries += 1
                    continue
                elif 'Voiceline too short' in str(e):
                    logging.info(f"Retrying without saying error voice line")
                    retries += 1
                    continue
                else:
                    error_response = "I can't find the right words at the moment."
                    self.conversation_manager.chat_manager.active_character.say(error_response)
                    logging.info('Retrying connection to API...')
                    retries -= 1
                    time.sleep(5)

        if voice_line_sentences > 0: # if the voice line is not empty, then generate the audio for the voice line
            await self.generate_voiceline(voice_line, sentence_queue, event)
            voice_line_sentences = 0
            voice_line = ''

        await sentence_queue.put(None) # Mark the end of the response for self.conversation_manager.chat_manager.send_response() and self.conversation_manager.chat_manager.send_response()

        if next_author is not None and full_reply.strip() != '':
            self.conversation_manager.messages.append({"role": next_author, "content": full_reply})
            # -- for each sentence for each character until the conversation ends or the max_response_sentences is reached or the player is speaking
            logging.info(f"Full response saved ({self.tokenizer.get_token_count(full_reply)} tokens): {full_reply}")

    async def generate_voiceline(self, string, sentence_queue, event):
        """Generate audio for a voiceline"""
        # Generate the audio and return the audio file path
        try:
            audio_file = self.conversation_manager.synthesizer.synthesize(self.conversation_manager.chat_manager.active_character, string)
        except Exception as e:
            logging.error(f"TTS Error: {e}")
            logging.info(e)
            input('Press enter to continue...')
            exit()

        await sentence_queue.put([audio_file, string]) # Put the audio file path in the sentence_queue
        event.clear() # clear the event for the next iteration
        await event.wait() # wait for the event to be set before generating the next line