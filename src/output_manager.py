from aiohttp import ClientSession
import asyncio
import os
import wave
import logging
import time
import shutil
import src.utils as utils

import unicodedata
import re
import sys

class ChatManager:
    def __init__(self, conversation_manager, config, tokenizer):
        self.conversation_manager = conversation_manager
        self.game_state_manager = conversation_manager.game_state_manager
        self.mod_folder = config.mod_path
        self.max_response_sentences = config.max_response_sentences
        self.llm = config.llm
        self.alternative_openai_api_base = config.alternative_openai_api_base
        self.temperature = config.temperature
        self.top_p = config.top_p
        self.stop = config.stop
        self.frequency_penalty = config.frequency_penalty
        self.max_tokens = config.max_tokens
        self.language = config.language
        self.tokenizer = tokenizer
        self.add_voicelines_to_all_voice_folders = config.add_voicelines_to_all_voice_folders
        self.offended_npc_response = config.offended_npc_response
        self.forgiven_npc_response = config.forgiven_npc_response
        self.follow_npc_response = config.follow_npc_response
        self.experimental_features = config.experimental_features
        self.wait_time_buffer = config.wait_time_buffer

        self.character_num = 0
        self.active_character = None

        self.wav_file = f'MantellaDi_MantellaDialogu_00001D8B_1.wav'
        self.lip_file = f'MantellaDi_MantellaDialogu_00001D8B_1.lip'

        self.end_of_sentence_chars = ['.', '?', '!']
        self.end_of_sentence_chars = [unicodedata.normalize('NFKC', char) for char in self.end_of_sentence_chars]
        self.banned_chars = ['*', '(', ')', '[', ']', '{', '}', "\"" ]


    async def get_audio_duration(self, audio_file):
        """Check if the external software has finished playing the audio file"""

        with wave.open(audio_file, 'r') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()

        # wait `buffer` seconds longer to let processes finish running correctly
        duration = frames / float(rate) + self.wait_time_buffer
        return duration
    

    def setup_voiceline_save_location(self, in_game_voice_folder):
        """Save voice model folder to Mantella Spell if it does not already exist"""
        self.in_game_voice_model = in_game_voice_folder

        in_game_voice_folder_path = f"{self.mod_folder}/{in_game_voice_folder}/"
        if not os.path.exists(in_game_voice_folder_path):
            os.mkdir(in_game_voice_folder_path)

            # copy voicelines from one voice folder to this new voice folder
            # this step is needed for Skyrim to acknowledge the folder
            example_folder = f"{self.mod_folder}/MaleNord/"
            for file_name in os.listdir(example_folder):
                source_file_path = os.path.join(example_folder, file_name)

                if os.path.isfile(source_file_path):
                    shutil.copy(source_file_path, in_game_voice_folder_path)

            self.game_state_manager.write_game_info('_mantella_status', 'Error with Mantella.exe. Please check MantellaSoftware/logging.log')
            logging.warn("Unknown NPC detected. This NPC will be able to speak once you restart Skyrim. To learn how to add memory, a background, and a voice model of your choosing to this NPC, see here: https://github.com/art-from-the-machine/Mantella#adding-modded-npcs")
            input('\nPress any key to exit...')
            sys.exit(0)


    @utils.time_it
    def save_files_to_voice_folders(self, queue_output):
        """Save voicelines and subtitles to the correct game folders"""

        audio_file, subtitle = queue_output
        if audio_file is None or subtitle is None or audio_file == '' or subtitle == '':
            logging.error(f"Error saving voiceline to voice folders. Audio file: {audio_file}, subtitle: {subtitle}")
            return
        if self.add_voicelines_to_all_voice_folders == '1':
            for sub_folder in os.scandir(self.mod_folder):
                if sub_folder.is_dir():
                    shutil.copyfile(audio_file, f"{sub_folder.path}/{self.wav_file}")
                    shutil.copyfile(audio_file.replace(".wav", ".lip"), f"{sub_folder.path}/{self.lip_file}")
        else:
            shutil.copyfile(audio_file, f"{self.mod_folder}/{self.active_character.in_game_voice_model}/{self.wav_file}")
            shutil.copyfile(audio_file.replace(".wav", ".lip"), f"{self.mod_folder}/{self.active_character.in_game_voice_model}/{self.lip_file}")

        logging.info(f"{self.active_character.name} should speak")
        if self.character_num == 0:
            self.game_state_manager.write_game_info('_mantella_say_line', subtitle.strip())
        else:
            say_line_file = '_mantella_say_line_'+str(self.character_num+1)
            self.game_state_manager.write_game_info(say_line_file, subtitle.strip())

    @utils.time_it
    def remove_files_from_voice_folders(self):
        for sub_folder in os.listdir(self.mod_folder):
            try:
                os.remove(f"{self.mod_folder}/{sub_folder}/{self.wav_file}")
                os.remove(f"{self.mod_folder}/{sub_folder}/{self.lip_file}")
            except:
                continue


    async def send_audio_to_external_software(self, queue_output):
        logging.info(f"Dialogue to play: {queue_output[0]}")
        self.save_files_to_voice_folders(queue_output)
        
        
        # Remove the played audio file
        #os.remove(audio_file)

        # Remove the played audio file
        #os.remove(audio_file)

    async def send_response(self, sentence_queue, event):
        """Send response from sentence queue generated by `process_response()`"""

        while True:
            queue_output = await sentence_queue.get()
            if queue_output is None:
                logging.info('End of sentences')
                break

            # send the audio file to the external software and wait for it to finish playing
            await self.send_audio_to_external_software(queue_output)
            event.set()

            audio_duration = await self.get_audio_duration(queue_output[0])
            # wait for the audio playback to complete before getting the next file
            logging.info(f"Waiting {int(round(audio_duration,4))} seconds...")
            await asyncio.sleep(audio_duration)

    def clean_sentence(self, sentence):
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
                    logging.info(f"Removed response containing single bracket: {sentence}")
                    sentence = ''

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

        return sentence


    async def process_response(self, player_name, config, sentence_queue, input_text, messages, synthesizer, characters, radiant_dialogue, event):
        """Stream response from LLM one sentence at a time"""

        messages.append({"role": player_name, "content": input_text})
        player_identity = player_name

        full_reply = '' # used to store the full reply
        next_author = None # used to determine who is speaking next in a conversation
        possible_players = [
            "A stranger",
            "A traveler",
            "a stranger",
            "a traveler",
            "Stranger",
            "stranger",
            "Traveler",
            "traveler",
        ]
        sentence = '' # used to store the current sentence being generated
        num_sentences = 0 # used to keep track of how many sentences have been generated
        retries = 5
        print("Signifier: ", config.message_signifier)
        print("Format: ", config.message_format)
        while retries >= 0: # keep trying to connect to the API until it works
            try:
                start_time = time.time()
                for chunk in self.conversation_manager.llm.acreate(messages):
                    content = chunk.choices[0].text
                    if content is not None and content != '':
                        print(chunk.model_dump_json())
                        sentence += content

                        if next_author is None: # if next_author is None, then extract it from the start of the generation
                            if config.message_signifier in sentence:
                                next_author = sentence.split(config.message_signifier)[0] # extract the next author from the start of the generation
                                sentence = sentence[len(next_author)+len(config.message_signifier):] # remove the author from the sentence
                                logging.info(f"Next author is {next_author}")
                            
                        if next_author == player_identity or next_author == config.user_name or next_author in possible_players: # if the next author is the player, then the player is speaking and generation should stop
                            logging.info(f"Player is speaking. Stopping generation.")
                            break

                        if next_author == config.system_name or next_author == config.assistant_name: # if the next author is the system, then the LLM is generating a response to the player
                            retries += 1 # Not a real retry, just a way to skip the sentence
                            raise Exception('Invalid author')

                        content_edit = unicodedata.normalize('NFKC', content) # normalize unicode characters
                        # check if content marks the end of a sentence
                        if (any(char in content_edit for char in self.end_of_sentence_chars)) or (any(char in content for char in self.banned_chars)): # if the content contains any of the end of sentence characters, then the sentence is complete
                            if next_author is None: # if next_author is None after generating a sentence, then there was an error generating the output. The LLM didn't choose a character to speak next.
                                logging.info(f"Next author is None. Failed to extract author from: {sentence}")
                                input('Press enter to continue...')
                                exit()

                            sentence = self.clean_sentence(sentence) # clean the sentence
                            if sentence == '': # if the sentence is empty after cleaning, then skip it
                                logging.info(f"Skipping empty sentence")
                                break
                                
                            if (next_author in characters.active_characters): # if the next author is a real character that's active in this conversation, then switch to that character
                                #TODO: or (any(key.split(' ')[0] == keyword_extraction for key in characters.active_characters))
                                logging.info(f"Switched to {next_author}")
                                self.active_character = characters.active_characters[next_author]
                                # characters are mapped to say_line based on order of selection
                                # taking the order of the dictionary to find which say_line to use, but it is bad practice to use dictionaries in this way
                                self.character_num = list(characters.active_characters.keys()).index(next_author) # Assigns a number to the character based on the order they were selected for use in the _mantella_say_line_# filename
                            else: # if the next author is not a real character, then assume the player is speaking and generation should stop
                                for character in characters.active_characters.values(): # check if the next author is a partial match to any of the active characters
                                    if next_author in character.name.split(" "):
                                        logging.info(f"Switched to {character.name} (WARNING: Partial match!)")
                                        self.active_character = character
                                        self.character_num = list(characters.active_characters.keys()).index(character.name)
                                        break
                                else: # if the next author is not a real character, then assume the player is speaking and generation should stop
                                    logging.info(f"Next author is not a real character: {next_author}")
                                    logging.info(f"Waiting for player input instead...")
                                    break

                            if not config.assist_check: # if remote, check if the response contains the word assist for some reason. Probably some OpenAI nonsense.
                                if ('assist' in sentence) and (num_sentences>0): # Causes problems if asking a follower if you should "assist" someone, if they try to say something along the lines of "Yes, we should assist them." it will cut off the sentence and basically ignore the player. TODO: fix this with a more robust solution
                                    logging.info(f"'assist' keyword found. Ignoring sentence which begins with: {sentence}") 
                                    break # stop generating response

                            # if config.strip_smalls and len(sentence.strip()) < config.small_size:
                            #     logging.info(f'Skipping voiceline that is too short: {sentence}')
                            #     break

                            logging.info(f"LLM returned sentence took {time.time() - start_time} seconds to execute")

                            if ":" in sentence: # if a colon is in the sentence, then the NPC is calling a keyword function in addition to speaking. Pass the keyword to the behavior manager to see if it matches any real keywords
                                keyword_extraction = sentence.split(':')[0]
                                # if LLM is switching character
                                if self.experimental_features:
                                    behavior = self.conversation_manager.behavior_manager.evaluate(keyword_extraction, self, characters, messages)
                                    if behavior == None:
                                        logging.warn(f"Keyword '{keyword_extraction}' not found in behavior_manager. Disgarding from response.")
                                else:
                                    logging.info(f"Experimental features disabled. Please set experimental_features = 1 in config.ini to enable Behaviors.")
                                sentence = sentence.split(':')[1]
                            
                            # Generate the audio and return the audio file path
                            try:
                                audio_file = synthesizer.synthesize(self.active_character, ' ' + sentence + ' ')
                            except Exception as e:
                                logging.error(f"xVASynth Error: {e}")
                                print(e)
                                input('Press enter to continue...')
                                exit()

                            # Put the audio file path in the sentence_queue
                            await sentence_queue.put([audio_file, sentence])

                            full_reply += sentence
                            num_sentences += 1
                            sentence = ''

                            # clear the event for the next iteration
                            event.clear()
                            # wait for the event to be set before generating the next line
                            await event.wait()

                            end_conversation = self.game_state_manager.load_conversation_ended()
                            radiant_dialogue_update = self.game_state_manager.load_radiant_dialogue()
                            # stop processing LLM response if:
                            # max_response_sentences reached (and the conversation isn't radiant)
                            # conversation has switched from radiant to multi NPC (this allows the player to "interrupt" radiant dialogue and include themselves in the conversation)
                            # the conversation has ended
                            if ((num_sentences >= self.max_response_sentences) and not radiant_dialogue) or (radiant_dialogue and not radiant_dialogue_update) or end_conversation: # if the conversation has ended, stop generating responses
                                break
                break
            except Exception as e:
                if retries == 0:
                    logging.error(f"Could not connect to LLM API\nError: {e}")
                    input('Press enter to continue...')
                    exit()
                logging.error(f"LLM API Error: {e}")
                error_response = "I can't find the right words at the moment."
                audio_file = synthesizer.synthesize(self.active_character, error_response)
                self.save_files_to_voice_folders([audio_file, error_response])
                logging.info('Retrying connection to API...')
                retries -= 1
                time.sleep(5)

        # Mark the end of the response
        await sentence_queue.put(None)

        messages.append({"role": next_author, "content": full_reply})
        
        logging.info(f"Full response saved ({self.tokenizer.get_token_count(full_reply)} tokens): {full_reply}")
        return messages