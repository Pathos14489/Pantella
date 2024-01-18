import os
import logging
import json
import time
import src.utils as utils

class Character:
    def __init__(self, characters_manager, info, is_generic_npc):
        self.characters_manager = characters_manager
        self.info = info
        logging.info(f"Loading character: {self.info['name']}")
        for key, value in info.items():
            setattr(self, key, value) # set all character info as attributes of the character object to support arbitrary character info
        self.language = self.characters_manager.conversation_manager.language_info['language']
        self.is_generic_npc = is_generic_npc
        self.conversation_summary = ''
        self.conversation_summary_file = self.get_latest_conversation_summary_file_path()
        if "age" not in self.info:
            self.age = "Adult" # default age - This is to help communicate to the AI the age of the actor they're playing to help them stay in character
            if "Old" in self.voice_model:
                self.age = "Old"
            elif "Young" in self.voice_model:
                self.age = "Young"
            elif "Child" in self.voice_model:
                self.age = "Child"
            elif "Teen" in self.voice_model:
                self.age = "Teen"
        self.gendered_age = "" # default gendered age - This is also to help communicate to the AI the age of the actor they're playing to help them stay in character
        if self.gender == "Male":
            if self.age == "Child" or self.age == "Teen":
                self.gendered_age = "Boy"
            elif self.age == "Old":
                self.gendered_age = "Old Man"
            else:
                self.gendered_age = "Man"
        else:
            if self.age == "Child" or self.age == "Teen":
                self.gendered_age = "Girl"
            elif self.age == "Old":
                self.gendered_age = "Old Lady"
            else:
                self.gendered_age = "Woman"
        self.conversation_history_file = f"data/conversations/{self.characters_manager.conversation_manager.player_name}_{self.characters_manager.conversation_manager.player_gender}_{self.characters_manager.conversation_manager.player_race}/{self.name}/{self.name}.json"
        self.current_trust = 0

    @property
    def conversation_manager(self):
        return self.characters_manager.conversation_manager

    def get_latest_conversation_summary_file_path(self):
        """Get latest conversation summary by file name suffix"""

        conversation_root_dir = f"data/conversations/{self.characters_manager.conversation_manager.player_name}_{self.characters_manager.conversation_manager.player_gender}_{self.characters_manager.conversation_manager.player_race}/{self.name}/"
        # TODO: Somehow make this work with multiple characters of the same name, gender and race or even ideally with the same exact character
        # at different points (e.g. different saves = different conversations with the same character and the same player character)
        # Maybe commmunicate the save index to the user and use that to load the correct save somehow?

        if os.path.exists(conversation_root_dir):
            # get all files from the directory
            files = os.listdir(conversation_root_dir)
            # filter only .txt files
            txt_files = [f for f in files if f.endswith('.txt')]
            if len(txt_files) > 0:
                file_numbers = [int(os.path.splitext(f)[0].split('_')[-1]) for f in txt_files]
                latest_file_number = max(file_numbers)
            else:
                logging.info(f"{conversation_root_dir} does not exist. A new summary file will be created.")
                latest_file_number = 1
        else:
            logging.info(f"{conversation_root_dir} does not exist. A new summary file will be created.")
            latest_file_number = 1

        
        conversation_summary_file = f"{conversation_root_dir}/{self.name}_summary_{latest_file_number}.txt"
        logging.info(f"Loaded latest summary file: {conversation_summary_file}")
        return conversation_summary_file
    

    # def set_context(self, location, in_game_time, active_characters, token_limit, radiant_dialogue):
    #     # if conversation history exists, load it
    #     if os.path.exists(self.conversation_history_file):
    #         try:
    #             with open(self.conversation_history_file, 'r', encoding='utf-8') as f:
    #                 conversation_history = json.load(f)

    #             previous_conversations = []
    #             for conversation in conversation_history:
    #                 previous_conversations.extend(conversation)

    #             with open(self.conversation_summary_file, 'r', encoding='utf-8') as f:
    #                 previous_conversation_summaries = f.read()

    #             self.conversation_summary = previous_conversation_summaries

    #             context = self.create_context(location, in_game_time, active_characters, token_limit, radiant_dialogue, len(previous_conversations), previous_conversation_summaries)
    #         except Exception as e:
    #             logging.error(f"Failed to load conversation history for {self.name}.")
    #             logging.error(e)
    #             context = self.create_context(location, in_game_time, active_characters, token_limit, radiant_dialogue)
    #     else:
    #         context = self.create_context(location, in_game_time, active_characters, token_limit, radiant_dialogue)

    #     return context
    
    def get_perspective_player_identity(self):
        perspective_name = "a stranger" # Who the character thinks the player is
        if self.in_game_relationship_level == 0:
            if self.current_trust < 1:
                trust = 'stranger'
                perspective_name = "A stranger"
            elif self.current_trust < 10:
                trust = 'acquaintance'
                perspective_name = "An acquaintance"
            elif self.current_trust < 50:
                trust = 'friend'
                perspective_name = self.characters_manager.conversation_manager.player_name
            elif self.current_trust >= 50:
                trust = 'close friend'
                perspective_name = self.characters_manager.conversation_manager.player_name
        elif self.in_game_relationship_level == 4:
            trust = 'lover'
            perspective_name = self.characters_manager.conversation_manager.player_name
        elif self.in_game_relationship_level > 0:
            trust = 'friend'
            perspective_name = self.characters_manager.conversation_manager.player_name
        elif self.in_game_relationship_level < 0:
            trust = 'enemy'
            perspective_name = "An enemy"
        
        perspective_description = perspective_name + "(" +  self.characters_manager.conversation_manager.player_race + " " + self.characters_manager.conversation_manager.player_gender + ") " # A description of the player from the character's perspective TODO: Turn this into a config setting like message_format
        if trust == "stranger":
            perspective_description += f"({trust})"
        else:
            perspective_description += f"({self.name}'s {trust})"
        return perspective_name, perspective_description, trust
    
    @property
    def replacement_dict(self):
        perspective_name, perspective_description, trust = self.get_perspective_player_identity()
        try:
            with open(self.conversation_summary_file, 'r', encoding='utf-8') as f:
                previous_conversation_summaries = f.read()
        except:
            previous_conversation_summaries = ''

        self.conversation_summary = previous_conversation_summaries
        return {
            "name": self.name,
            "race": self.race,
            "gender": self.gender,
            "age": self.age,
            "gendered_age": self.gendered_age,
            "perspective_player_name": perspective_name,
            "perspective_player_description": perspective_description,
            "conversation_summary": self.conversation_summary,
            "bio": self.bio,
            "trust": trust,
        }   
    
    # def create_context(self, conversation_manager, location='Skyrim', time='12', active_characters=None, token_limit=4096, radiant_dialogue='false', trust_level=0, conversation_summary='', prompt_limit_pct=0.75):
    #     self.current_trust = trust_level
    #     perspective_name, perspective_description, trust = self.get_perspective_player_identity()

    #     keys = list(active_characters.keys())

    #     for key, value in self.info.items(): # add all character info to replacement dict
    #         replacement_dict[key] = value
    #     def rd_format(r_dict,s): # Uses the replacement dict to format the string
    #         # remove /r from all strings
    #         new_r_dict = {}
    #         for key, value in r_dict.items():
    #             if value != None:
    #                 new_r_dict[key] = str(value).replace("/r", "")
    #         r_dict = new_r_dict
    #         print(r_dict)
    #         return s.format(**r_dict)

    #     if len(keys) == 1: # Single NPC prompt
    #         rd = replacement_dict.copy()
    #         rd["conversation_summary"] = conversation_summary

    #         character_desc = rd_format(rd ,conversation_manager.config.single_npc_prompt)
    #     else: # Multi NPC prompt
    #         if radiant_dialogue == 'false': # mention player if multi NPC dialogue and not radiant dialogue
    #             keys_w_player = [perspective_name] + keys
    #         else: # don't mention player if radiant dialogue
    #             keys_w_player = keys
            
    #         # Join all but the last key with a comma, and add the last key with "and" in front
    #         character_names_list = ', '.join(keys[:-1]) + ' and ' + keys[-1]
    #         character_names_list_w_player = ', '.join(keys_w_player[:-1]) + ' and ' + keys_w_player[-1]

    #         bio_descriptions = []
    #         for character_name, character in active_characters.items():
    #             bio_descriptions.append(f"{character_name}: {character.bio}")

    #         formatted_bios = "\n".join(bio_descriptions)

    #         conversation_histories = []
    #         for character_name, character in active_characters.items():
    #             conversation_histories.append(f"{character_name}: {character.conversation_summary}")

    #         formatted_histories = "\n".join(conversation_histories)
            
    #         rd = replacement_dict.copy()
    #         rd["bios"] = formatted_bios
    #         rd["names"] = character_names_list
    #         rd["names_w_player"] = character_names_list_w_player
    #         rd["conversation_summary"] = formatted_histories

    #         character_desc = rd_format(rd, conversation_manager.config.single_npc_prompt)
        

    #         # Check if character prompt is too long
    #         prompt_num_tokens = conversation_manager.tokenizer.num_tokens_from_messages([{"role": "system", "content": character_desc}])
    #         prompt_token_limit = (round(token_limit*prompt_limit_pct,0))
    #         # If the full prompt is too long, exclude NPC memories from prompt
    #         if prompt_num_tokens > prompt_token_limit:
    #             rd["conversation_summaries"] = 'NPC memories not available.'
    #             # TODO: Fix this to trimming the memory summaries instead of cutting it entirely because I don't want dementia chatbots. Trim the the who spoke longest ago and isn't chatting next.

    #             character_desc = rd_format(rd, conversation_manager.config.single_npc_prompt)
                
    #             prompt_num_tokens = conversation_manager.tokenizer.num_tokens_from_messages([{"role": "system", "content": character_desc}])
    #             prompt_token_limit = (round(token_limit*prompt_limit_pct,0))
    #             # If the prompt with all bios included is too long, exclude NPC bios and just list the names of NPCs in the conversation
    #             if prompt_num_tokens > prompt_token_limit:
    #                 rd["bios"] = 'NPC backgrounds not available.'
    #                 # TODO: Fix this to trimming the bioses instead of cutting it entirely because I don't want dementia chatbots. Trim the the who spoke longest ago and isn't chatting next.
    #                 # Long Term Idea: Each character should have their own personal prompt, not one big multi NPC prompt. Not only will this prevent characters from having unreasonable knowledge about the characters they're chatting to, but it will also allow for more natural conversations.
    #                 # Short Term Idea: Add a second description to each character(see: generate it from the character's bio) that is used for multi NPC prompts. This description should be shorter than the bio and should be more focused on the character's appearance and general traits rather than their backstory
    #                 character_desc = conversation_manager.config.single_npc_prompt
    #                 for key, value in rd.items():
    #                     character_desc = character_desc.replace(f'{{{key}}}', value)
        
    #     logging.info(character_desc)
    #     context = [{"role": "system", "content": character_desc}]
    #     return context
        
    def say(self,string):
        audio_file = self.conversation_manager.synthesizer.synthesize(self, string) # say string
        self.conversation_manager.chat_manager.save_files_to_voice_folders([audio_file, string]) # save audio file to voice folder so it can be played in-game
        self.conversation_manager.messages.append({"role": self.name, "content": string}) # add string to ongoing conversation

    def save_conversation(self, summary=None, summary_limit_pct=0.45):
        if self.is_generic_npc:
            logging.info('A summary will not be saved for this generic NPC.')
            return None
        
        summary_limit = round(self.conversation_manager.tokens_available*summary_limit_pct,0) # How many tokens the summary can be before it is summarized

        # save conversation history
        
        if os.path.exists(self.conversation_history_file): # if this is not the first conversation load the previous conversation history from the conversation history file
            with open(self.conversation_history_file, 'r', encoding='utf-8') as f:
                conversation_history = json.load(f)

            # add new conversation to conversation history
            conversation_history.append(self.conversation_manager.messages) # append everything except the initial system prompt
        
        else: # if this is the first conversation initialize the conversation history file and set the previous conversation history to an every message except the initial system prompt
            directory = os.path.dirname(self.conversation_history_file)
            os.makedirs(directory, exist_ok=True)
            conversation_history = [self.conversation_manager.messages]
        
        with open(self.conversation_history_file, 'w', encoding='utf-8') as f: # save everything except the initial system prompt
            json.dump(conversation_history, f, indent=4)

        
        if os.path.exists(self.conversation_summary_file): # if this is not the first conversation load the previous conversation summaries from the conversation summary file
            with open(self.conversation_summary_file, 'r', encoding='utf-8') as f:
                previous_conversation_summaries = f.read()
        else: # if this is the first conversation, initialize the conversation summary file and set the previous conversation summaries to an empty string
            directory = os.path.dirname(self.conversation_summary_file)
            os.makedirs(directory, exist_ok=True)
            previous_conversation_summaries = ''

        # If summary has not already been generated for another character in a multi NPC conversation (multi NPC memory summaries are shared)
        if summary == None:
            while True:
                try:
                    new_conversation_summary = self.summarize_conversation()
                    break
                except Exception as e:
                    logging.error('Failed to summarize conversation...')
                    logging.error(e)
                    print(e)
                    input('Press enter to continue...')
                    exit()
        else:
            new_conversation_summary = summary
        conversation_summaries = previous_conversation_summaries + new_conversation_summary

        with open(self.conversation_summary_file, 'w', encoding='utf-8') as f:
            f.write(conversation_summaries)

        # if summaries token limit is reached, summarize the summaries
        if self.conversation_manager.tokenizer.get_token_count(conversation_summaries) > summary_limit:
            logging.info(f'Token limit of conversation summaries reached ({len(self.conversation_manager.tokenizer.encode(conversation_summaries))} / {summary_limit} tokens). Creating new summary file...')
            while True:
                try:
                    prompt = f"You are tasked with summarizing the conversation history between {self.name} and the player / other characters. These conversations take place in Skyrim. "\
                        f"Each paragraph represents a conversation at a new point in time. Please summarize these conversations into a single paragraph in {self.characters_manager.conversation_manager.language_info['language']}."
                    long_conversation_summary = self.summarize_conversation(prompt)
                    break
                except:
                    logging.error('Failed to summarize conversation. Retrying...')
                    time.sleep(5)
                    continue

            # Split the file path and increment the number by 1
            base_directory, filename = os.path.split(self.conversation_summary_file)
            file_prefix, old_number = filename.rsplit('_', 1)
            old_number = os.path.splitext(old_number)[0]
            new_number = int(old_number) + 1
            new_conversation_summary_file = os.path.join(base_directory, f"{file_prefix}_{new_number}.txt")

            with open(new_conversation_summary_file, 'w', encoding='utf-8') as f:
                f.write(long_conversation_summary)
        
        return new_conversation_summary
    

    def summarize_conversation(self, prompt=None):
        perspective_name, _, _ = self.get_perspective_player_identity()
        summary = ''
        if len(self.conversation_manager.get_context()) > 5:
            conversation = self.conversation_manager.get_context()[3:-2] # drop the context (0) hello (1,2) and "Goodbye." (-2, -1) lines
            assistant_name = self.conversation_manager.config.assistant_name[0].upper() + self.conversation_manager.config.assistant_name[1:].lower()
            if prompt == None: # If no summarization prompt is provided, use default
                prompt = f"{assistant_name} is tasked with summarizing the conversation between {self.name} and {perspective_name} / other characters. These conversations take place in Skyrim. It is not necessary to comment on any mixups in communication such as mishearings. Text contained within asterisks state in-game events. Please summarize the conversation into a single paragraph in {self.characters_manager.conversation_manager.language_info['language']}."
            context = [{"role": self.conversation_manager.config.system_name, "content": prompt}]
            history = ""
            for message in conversation:
                history += message["role"] + ": " + message["content"] + "\n"
            history = history.strip() # remove trailing newline
            summary, _ = self.conversation_manager.llm.chatgpt_api(history, context) # TODO: Change to use acreate instead of chatgpt_api, I don't think this works with the use of none "system", "user" and "assistant" roles being in the conversation history

            summary = summary.replace('The assistant', self.name)
            summary = summary.replace('the assistant', self.name)
            summary = summary.replace('an assistant', self.name)
            summary = summary.replace('an AI assistant', self.name)
            summary = summary.replace('The user', perspective_name)
            summary = summary.replace('The User', perspective_name)
            summary = summary.replace('the user', perspective_name)
            summary = summary.replace('The player', perspective_name)
            summary = summary.replace('The Player', perspective_name)
            summary = summary.replace('the player', perspective_name)
            summary += '\n\n'

            logging.info(f"Conversation summary saved.")
        else:
            logging.info(f"Conversation summary not saved. Not enough dialogue spoken.")

        return summary