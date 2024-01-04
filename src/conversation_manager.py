import src.tts as tts
import src.stt as stt
import src.utils as utils
import sys
import os
import asyncio
import src.output_manager as output_manager
import src.game_manager as game_manager
import src.character_manager as character_manager
import src.characters_manager as characters_manager
import src.setup as setup
import logging

class conversation_manager():
    def __init__(self, config_file, logging_file, secret_key_file, language_file):
        self.config, self.character_df, self.language_info, self.llm, self.tokenizer, self.token_limit, self.synthesizer = setup.initialise(
            config_file=config_file,
            logging_file=logging_file, 
            secret_key_file=secret_key_file, 
            language_file=language_file
        )
        # self.config
        # self.character_df
        # self.language_info
        # self.llm
        # self.tokenizer
        # self.token_limit
        self.mantella_version = '0.11-p'
        
        logging.info(f'\nMantella v{self.mantella_version}')
        
        self.game_state_manager = game_manager.GameStateManager(self.config.game_path)
        self.chat_manager = output_manager.ChatManager(self, self.config, self.tokenizer)
        self.transcriber = stt.Transcriber(self.game_state_manager, self.config)
        self.active_characters = None # Initialised at start of every conversation in await_and_setup_conversation()
        self.check_mcm_mic_status()
        self.in_conversation = False # Whether or not the player is in a conversation
        self.tokens_available = 0 # Initialised at start of every conversation in await_and_setup_conversation()
        
    async def get_response(self, player_name, input_text, messages, synthesizer, characters, radiant_dialogue):
        sentence_queue = asyncio.Queue()
        event = asyncio.Event()
        event.set()

        results = await asyncio.gather(
            self.chat_manager.process_response(player_name, self.config, sentence_queue, input_text, messages, synthesizer, characters, radiant_dialogue, event), 
            self.chat_manager.send_response(sentence_queue, event)
        )
        messages, _ = results

        return messages

    def check_mcm_mic_status(self):
        # Check if the mic setting has been configured in MCM
        # If it has, use this instead of the config.ini setting, otherwise take the config.ini value
        # TODO: Convert to game_state_manager await and load game data method
        if os.path.exists(f'{self.config.game_path}/_mantella_microphone_enabled.txt'):
            with open(f'{self.config.game_path}/_mantella_microphone_enabled.txt', 'r', encoding='utf-8') as f:
                mcm_mic_enabled = f.readline().strip()
            self.config.mic_enabled = '1' if mcm_mic_enabled == 'TRUE' else '0'

    def await_and_setup_conversation(self): # wait for player to select an NPC and setup the conversation when outside of conversation
        self.check_mcm_mic_status()
        self.game_state_manager.reset_game_info() # clear _mantella_ files in Skyrim folder

        self.active_characters = characters_manager.Characters() # Manage active characters in conversation
        self.transcriber.call_count = 0 # reset radiant back and forth count

        logging.info('\nConversations not starting when you select an NPC? Post an issue on the GitHub page: https://github.com/art-from-the-machine/Mantella')
        logging.info('\nWaiting for player to select an NPC...')
        try: # load character info, location and other gamestate data when data is available - Starts watching the _mantella_ files in the Skyrim folder and waits for the player to select an NPC
            character_info, location, in_game_time, is_generic_npc, player_name, player_race, player_gender, radiant_dialogue = self.game_state_manager.load_game_state(self.config, self.character_df)
        except game_manager.CharacterDoesNotExist as e:
            self.game_state_manager.write_game_info('_mantella_end_conversation', 'True') # End the conversation in game
            logging.info('Restarting...')
            logging.error(f"Error: {e}")
        self.player_name = player_name
        self.player_race = player_race
        self.player_gender = player_gender
        
        # setup the character that the player has selected
        character = character_manager.Character(character_info, self.language_info['language'], is_generic_npc, player_name, player_race, player_gender)
        self.synthesizer.change_voice(character.voice_model)
        self.chat_manager.active_character = character
        self.chat_manager.character_num = 0
        self.active_characters.active_characters[character.name] = character
        self.chat_manager.setup_voiceline_save_location(character_info['in_game_voice_model'])# if the NPC is from a mod, create the NPC's voice folder and exit Mantella if there isn't already a folder for the NPC
        
        self.game_state_manager.write_game_info('_mantella_character_selection', 'True') # write to _mantella_character_selection.txt to indicate that the character has been selected to the game

        context = character.set_context(self, location, in_game_time, self.active_characters.active_characters, self.token_limit, radiant_dialogue) # set context for the conversation

        self.tokens_available = self.token_limit - self.tokenizer.num_tokens_from_messages(context) # calculate number of tokens available for the conversation
        
        self.messages = context.copy() # copy character prompt and their summary of their past to messages

        if not radiant_dialogue:
            # initiate conversation with character TODO: Make this more interesting, always having the character say hi like we aren't always with each other is bizzare imo
            try:
                self.messages = asyncio.run(self.get_response(player_name, f"{self.language_info['hello']} {character.name}.", context, self.synthesizer, self.active_characters, radiant_dialogue))
            except tts.VoiceModelNotFound as e:
                self.game_state_manager.write_game_info('_mantella_end_conversation', 'True')
                logging.error(f"Error: {e}")
                # if debugging and character name not found, exit here to avoid endless loop
                if (self.config.debug_mode == '1') & (self.config.debug_character_name != 'None'):
                    sys.exit(0)

        # debugging variable
        self.say_goodbye = False
        self.in_conversation = True

    def get_if_new_character_joined(self):
        # check if new character has been added to conversation and switch to Single Prompt Multi-NPC conversation if so
        num_characters_selected = self.game_state_manager.load_ingame_actor_count()
        if num_characters_selected > self.active_characters.active_character_count():
            return True
        else:
            return False

    def step(self): # process player input and NPC response until conversation ends at each step of the conversation
        if self.in_conversation == False:
            logging.info('Cannot step through conversation when not in conversation')
            return
        
        conversation_ended = self.game_state_manager.load_conversation_ended() # wait for the game to indicate that the conversation has ended or not
        new_character_joined = self.get_if_new_character_joined() # check if new character has been added to conversation and switch to Single Prompt Multi-NPC conversation if so
        
        radiant_dialogue = self.game_state_manager.load_radiant_dialogue() # check if radiant dialogue is being used
        conversation_started_radiant = radiant_dialogue # to check later on if conversation started as radiant dialogue

        if new_character_joined: # check if new character has been added to conversation and switch to Single Prompt Multi-NPC conversation if so
            try: # load character info, location and other gamestate data when data is available - Starts watching the _mantella_ files in the Skyrim folder and waits for the player to select an NPC
                character_info, location, in_game_time, is_generic_npc, player_name, player_race, player_gender, radiant_dialogue = self.game_state_manager.load_game_state(self.config, self.character_df)
            except game_manager.CharacterDoesNotExist as e:
                self.game_state_manager.write_game_info('_mantella_end_conversation', 'True') # End the conversation in game
                logging.info('Restarting...')
                logging.error(f"Error: {e}")

            
            messages_wo_system_prompt = self.messages[1:] # remove single character prompt from messages
            # add character name before each response to be consistent with the multi-NPC format

            # last_assistant_idx = None 
            # for idx, message in enumerate(messages_wo_system_prompt):
            #     if message['role'] == 'assistant':
            #         last_assistant_idx = idx
            #         if active_characters.active_character_count() == 1:
            #             message['content'] = character.name+': '+message['content']

            character = character_manager.Character(character_info, self.language_info['language'], is_generic_npc, player_name, player_race, player_gender)
            self.active_characters.active_characters[character.name] = character
            
            self.chat_manager.setup_voiceline_save_location(character_info['in_game_voice_model']) # if the NPC is from a mod, create the NPC's voice folder and exit Mantella

            
            if not radiant_dialogue: # if not radiant dialogue format
                # add greeting from newly added NPC to help the LLM understand that this NPC has joined the conversation
                messages_wo_system_prompt[self.last_assistant_idx]['content'] += f"\n{character.name}: self.{self.language_info['hello']}."
            
            new_context = character.set_context(self, location, in_game_time, self.active_characters.active_characters, self.token_limit, radiant_dialogue)

            if not radiant_dialogue: # if not radiant dialogue format
                new_context.extend(messages_wo_system_prompt)
                new_context = character.set_context(self, location, in_game_time, self.active_characters.active_characters, self.token_limit, radiant_dialogue)

            self.messages = new_context.copy() 
            self.game_state_manager.write_game_info('_mantella_character_selection', 'True') # write to _mantella_character_selection.txt to indicate that the character has been successfully selected to the game
        
        # if there are still active characters in the conversation or not radiant dialogue, continue conversation
        if (self.active_characters.active_character_count() > 1) or (not radiant_dialogue):
            # if the conversation was initially radiant but now the player is jumping in, reset the system prompt to include player
            if (not radiant_dialogue) and conversation_started_radiant:
                conversation_started_radiant = False
                messages_wo_system_prompt = messages[1:]

            # check if radiant dialogue has switched to multi NPC
            radiant_dialogue = self.game_state_manager.load_radiant_dialogue()
            
            transcript_cleaned = ''
            transcribed_text = None
            if not conversation_ended: # check if conversation has ended, if not, get next player input
                transcribed_text, say_goodbye = self.transcriber.get_player_response(radiant_dialogue) # say_goodbye removed

                self.game_state_manager.write_game_info('_mantella_player_input', transcribed_text)

                transcript_cleaned = utils.clean_text(transcribed_text)

                # if multi NPC conversation, add "Player:" to beginning of output to clarify to the LLM who is speaking
                if (self.active_characters.active_character_count() > 1) and not radiant_dialogue:
                    transcribed_text = 'Player: ' + transcribed_text
                # add in-game events to player's response
                transcribed_text = self.game_state_manager.update_game_events(transcribed_text) # TODO: Switch to using system messages to update ingame events that are generic, and link all ingame events that relate to a character to the character's messages
                logging.info(f"Text passed to NPC: {transcribed_text}")

            # check if conversation has ended again after player input
            with open(f'{self.config.game_path}/_mantella_end_conversation.txt', 'r', encoding='utf-8') as f:
                conversation_ended = f.readline().strip()

            # check if user is ending conversation
            if (self.transcriber.activation_name_exists(transcript_cleaned, self.config.end_conversation_keyword.lower())) or (self.transcriber.activation_name_exists(transcript_cleaned, 'good bye')) or (conversation_ended.lower() == 'true'):
                self.game_state_manager.end_conversation(conversation_ended, self, self.tokenizer, self.synthesizer, self.chat_manager, messages, self.active_characters.active_characters, self.tokens_available, character)
                self.in_conversation = False
                return

            # Let the player know that they were heard
            #audio_file = synthesizer.synthesize(character.info['voice_model'], character.info['skyrim_voice_folder'], 'Beep boop. Let me think.')
            #chat_manager.save_files_to_voice_folders([audio_file, 'Beep boop. Let me think.'])

            # get character's response
            if transcribed_text:
                self.messages = asyncio.run(self.get_response(player_name, transcribed_text, messages, self.synthesizer, self.active_characters, radiant_dialogue))

            # if the conversation is becoming too long, save the conversation to memory and reload
            current_conversation_limit_pct = self.config.conversation_limit_pct # TODO: Come up with a smarter way of deciding when to reload a conversation
            if self.tokenizer.num_tokens_from_messages(messages[1:]) > (round(self.tokens_available*current_conversation_limit_pct,0)): 
                _, context, messages = self.game_state_manager.reload_conversation(self, self.tokenizer, self.synthesizer, self.chat_manager, messages, self.active_characters.active_characters, self.tokens_available, self.token_limit, location, in_game_time)
                # continue conversation
                self.messages = asyncio.run(self.get_response(player_name, f"{character.name}?", context, self.synthesizer, self.active_characters, radiant_dialogue))