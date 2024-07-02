from src.logging import logging, time
import src.utils as utils
import asyncio
import wave

valid_games = []
interface_slug = "base_game_interface"

class BaseGameInterface:
    def __init__(self, conversation_manager, valid_games=valid_games, interface_slug=interface_slug):
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
        self.prev_game_time = ''
        logging.info(f"Loading Game Interface...")
        
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
        
    def update_game_events(self):
        new_game_events = []
        for even in self.new_game_events:
            new_game_events.append(even)
        self.new_game_events = []

        # encapsulate events in *asterisks* for emphasis
        formatted_in_game_events_lines = ['*{}*'.format(line.strip()) for line in new_game_events]
        in_game_events = '\n'.join(formatted_in_game_events_lines)

        if len(in_game_events) > 0:
            logging.info(f'In-game events since previous exchange:\n{in_game_events}')

        # append the time to player's response
        in_game_time = self.get_current_game_time() # Current in-game time
        print(in_game_time)
        # only pass the in-game time if it has changed by at least an hour
        if self.new_time(in_game_time):
            time_group = utils.get_time_group(in_game_time['hour24'])

            time_string = f"The time is now {in_game_time['time12']} {time_group}."
            logging.info(time_string)
            
            formatted_in_game_time = f"{time_string}\n"
            in_game_events = formatted_in_game_time + in_game_events
        
        if len(in_game_events.strip()) > 0:
            logging.info(f'In-game events since previous exchange:\n{in_game_events}')
            if len(self.conversation_manager.messages) == 0: # if there are no messages in the conversation yet, add in-game events to the first message from the system
                self.conversation_manager.new_message({
                    "role": self.conversation_manager.config.system_name,
                    "content": in_game_events,
                    "type": "game_event",
                })
            else: # if there are messages in the conversation, add in-game events to the last message from the system
                last_message = self.conversation_manager.messages[-1]
                if last_message['role'] == self.conversation_manager.config.system_name and last_message['type'] == 'game_event': # if last message was from the system and was an in-game event, append new in-game events to the last message
                    self.conversation_manager.messages[-1]['content'] += "\n" + in_game_events
                else: # if last message was from the NPC, add in-game events to the ongoing conversation as a new message from the system
                    self.conversation_manager.new_message({
                        "role": self.conversation_manager.config.system_name,
                        "content": in_game_events,
                        "type": "game_event",
                    }) # add in-game events to current ongoing conversation
        return new_game_events
        
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
        try:
            with wave.open(audio_file, 'r') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
        except Exception as e:
            logging.error(f"Error getting audio duration: {e}")
            frames = 0
            rate = 0
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
            
            await self.send_audio_to_external_software(queue_output) # send the audio file to the external software and start playing it.
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