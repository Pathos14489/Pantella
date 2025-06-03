from src.logging import logging, time
import src.utils as utils
from src.stt import create_Transcriber
import asyncio
import wave
import sys

valid_games = []
interface_slug = "base_game_interface"

class BaseGameInterface:
    def __init__(self, conversation_manager, valid_games=valid_games, interface_slug=interface_slug):
        logging.info(f"Initializing Basic Game Interface...")
        self.conversation_manager = conversation_manager
        self.config = self.conversation_manager.config
        self.wait_time_buffer = self.config.wait_time_buffer
        self.game_id = self.config.game_id
        self.valid_games = valid_games
        self.interface_slug = interface_slug
        if self.interface_slug == "base_game_interface":
            logging.error(f"Interface slug not implemented for interface {self.__class__.__name__}")
            raise NotImplementedError
        if self.game_id not in self.valid_games:
            logging.error(f"Game '{self.game_id}' not supported by interface {self.interface_slug}")
            return
        self.new_game_events = []
        self.active_character = None
        self.audio_supported = False
        self.text_supported = True
        self.transcriber = None
        self.prev_game_time = ''
        if self.config.stt_enabled:
            self.transcriber = create_Transcriber(self)
        logging.info(f"Loaded Basic Game Interface...")

    def display_status(self, status):
        """Display the status of the game interface"""
        logging.info(f"Game Interface Status: {status}")
        
    def get_current_location(self, presume = ''):
        """Return the current location"""
        return 'Skyrim'
    
    def new_time(self, in_game_time=None):
        """Check if the in-game time has changed since the last check"""
        if in_game_time == None:
            in_game_time = self.get_current_game_time()
        if in_game_time['hour24'] != self.prev_game_time:
            self.prev_game_time = in_game_time['hour24']
            return True
        return False
    
    def get_player_response(self, possible_names_list):
        """Get the player's response from the game"""
        logging.info(f"Getting player response...")
        try:
            if self.audio_supported and self.check_mic_status() and "transcriber" in locals(): # listen for response
                logging.info('Listening for player response...')
                if "transcriber" in locals() and not self.transcriber.initialized:
                    logging.info('Microphone requested but not initialized. Initializing...')
                    self.transcriber.initialize()
                transcribed_text = self.transcriber.recognize_input(possible_names_list)
                logging.info(f'Player said: {transcribed_text}')
            else: # use text input
                logging.info('Awaiting text input...')
                if self.text_supported:
                    if "transcriber" in locals() and self.transcriber.initialized:
                        logging.info('Microphone not requested but was already initialized. Unloading transcriber until it\'s needed...')
                        self.transcriber.unload()
                    transcribed_text = self.get_text_input()
                logging.info(f'Player wrote: {transcribed_text}')
        except Exception as e:
            logging.error(f"There was a problem getting the player's response: {e}") 
            input("Press Enter to continue...")
            raise e
        return transcribed_text

    def get_text_input(self):
        print("Awaiting text input from the game...\n\n---\n")
        return input(self.conversation_manager.player_name + ": ")
        
    def update_game_events(self):
        logging.info(f"Updating game events...")
        new_game_events = []
        for game_event in self.new_game_events:
            new_game_events.append(self.conversation_manager.character_manager.render_game_event(game_event))
        self.new_game_events = []
        logging.info("New Game Events:", new_game_events)

        # append the time to player's response
        in_game_time = self.get_current_game_time() # Current in-game time
        logging.info(f"Current in-game time: {in_game_time['time24']}")
        # only pass the in-game time if it has changed by at least an hour
        if self.new_time(in_game_time):
            time_group = utils.get_time_group(in_game_time['hour24'])

            time_string = self.conversation_manager.character_manager.language["game_events"]["time_update"].format(
                time_group=time_group,
                time12=in_game_time['time24'],
                time24=in_game_time['time24'],
                ampm=in_game_time['ampm'],
            )
            new_game_events.append(time_string)
            logging.info(time_string)
            
        in_game_events = ' '.join(new_game_events)
        in_game_events = in_game_events.strip()
        if len(in_game_events.strip()) > 0:
            in_game_events = "*" + in_game_events + "*"
            if len(in_game_events) > 0:
                logging.info(f'In-game events since previous exchange:\n{in_game_events}')
            if len(self.conversation_manager.messages) == 0: # if there are no messages in the conversation yet, add in-game events to the first message from the system
                self.conversation_manager.new_message({
                    "role": "system",
                    "content": in_game_events,
                    "type": "game_event",
                })
            else: # if there are messages in the conversation, add in-game events to the last message from the system
                last_message = self.conversation_manager.messages[-1]
                if last_message['role'] == "system" and last_message['type'] == 'game_event': # if last message was from the system and was an in-game event, append new in-game events to the last message
                    self.conversation_manager.messages[-1]['content'] += "\n" + in_game_events
                else: # if last message was from the NPC, add in-game events to the ongoing conversation as a new message from the system
                    self.conversation_manager.new_message({
                        "role": "system",
                        "content": in_game_events,
                        "type": "game_event",
                    }) # add in-game events to current ongoing conversation
        return new_game_events
        
    def setup_character(self, character):
        """Setup the character in the game"""
        logging.info(f"Setting up character in the game...")
        self.active_character = character
        self.character_num = 0

    def enable_character_selection(self):
        """Enable character selection in the game"""
        logging.info(f"Enabling character selection...")
        raise NotImplementedError
    
    @property
    def game_path(self):
        return self.config.game_path
    
    @property
    def mod_path(self):
        return self.config.mod_path
    
    @property
    def mod_voice_dir(self):
        if self.config.linux_mode:
            return "./data/output/voice"
        else:
            return ".\\data\\output\\voice"
    
    async def get_audio_duration(self, audio_file):
        """Check if the external software has finished playing the audio file"""
        logging.info(f"Getting audio duration for {audio_file}...")
        try:
            with wave.open(audio_file, 'r') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
        except Exception as e:
            logging.error(f"Error getting audio duration: {e}")
            frames = 0
            rate = 0
        if rate == 0:
            logging.error(f"Error getting audio duration: rate is 0")
            return 0
        # wait `buffer` seconds longer to let processes finish running correctly
        duration = frames / float(rate) + self.wait_time_buffer
        return duration

    async def send_audio_to_external_software(self, queue_output):
        """Send audio file to external software e.g. Skyrim, Fallout 4, etc."""
        logging.info(f"Dialogue to play: {queue_output[0]}")
        logging.error(f"send_audio_to_external_software not implemented for game_interface {self.__class__.__name__}")
        raise NotImplementedError

    async def send_response(self, sentence_queue, event):
        """Send response from sentence queue generated by `process_response()`"""
        while True: # keep getting audio files from the queue until the queue is empty
            queue_output = await sentence_queue.get() # get the next audio file from the queue
            if queue_output is None:
                logging.info('End of sentences')
                break # stop getting audio files from the queue if the queue is empty
            
            try:
                await self.send_audio_to_external_software(queue_output) # send the audio file to the external software and start playing it.
            except Exception as e:
                logging.error(f"Error sending audio to external software: {e}")
                if not self.config.continue_on_failure_to_send_audio_to_game_interface:
                    input("Press Enter to continue...")
                    raise e
            event.set() # set the event to let the process_response() function know that it can generate the next sentence while the last sentence's audio is playing
            
            # wait for the audio playback to complete before getting the next file
            audio_duration = await self.get_audio_duration(queue_output[0])
            # wait for the audio playback to complete before getting the next file
            logging.info(f"Waiting {int(round(audio_duration,4))} seconds for audio to finish playing...")
            await asyncio.sleep(audio_duration)

    def is_conversation_ended(self):
        """Returns True if the conversation has ended, False otherwise."""
        raise NotImplementedError
    
    def is_radiant_dialogue(self):
        """Returns True if the current dialogue is a radiant dialogue, False otherwise. - Radiant dialogues are dialogues that are initiated by the AI, not the player."""
        return False
    
    def get_current_context_string(self):
        """Returns the current context string set by the player. Or an empty string if no context is set."""
        return ""
    
    def check_mic_status(self):
        return False
    
    def get_dummy_game_time(self):
        """Return the current time as a dictionary."""
        current_time = time.localtime()
        hour24 = current_time.tm_hour
        hour12 = hour24 % 12
        minute = current_time.tm_min
        time24 = f"{hour24:02}:{minute:02}"
        time12 = f"{hour12:02}:{minute:02} {'AM' if hour24 < 12 else 'PM'}"
        ampm = 'AM' if hour24 < 12 else 'PM'
        return {
            'year': time.localtime().tm_year,
            'month': time.localtime().tm_mon,
            'day': time.localtime().tm_mday,
            "hour24": hour24,
            "hour12": hour12,
            "minute": minute,
            "time24": time24,
            "time12": time12,
            "ampm": ampm,
        }
        
    def get_current_game_time(self):
        return self.get_dummy_game_time()
    
    
    def queue_actor_method(self, actor_character, method_name, *args):
        """Queue an arbitrary method to be run on the actor in game via the game interface."""
        raise NotImplementedError

    def end_conversation(self):
        """End the conversation in game."""
        raise NotImplementedError
    
    def remove_from_conversation(self, character):
        """Remove the character from the conversation in game."""
        raise NotImplementedError
    
    @utils.time_it
    def load_game_state(self):
        """Load game variables from _pantella_ files in Skyrim folder (data passed by the Pantella spell)"""
        raise NotImplementedError