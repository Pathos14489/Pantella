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
    def __init__(self, conversation_manager):
        self.conversation_manager = conversation_manager
        self.game_state_manager = self.conversation_manager.game_state_manager
        self.config = self.conversation_manager.config
        self.game = self.config.game_id
        self.mod_folder = self.config.mod_path
        self.add_voicelines_to_all_voice_folders = self.config.add_voicelines_to_all_voice_folders
        self.wait_time_buffer = self.config.wait_time_buffer
        self.root_mod_folter = self.config.game_path

        self.character_num = 0 
        self.active_character = None

        self.wav_file = f'MantellaDi_MantellaDialogu_00001D8B_1.wav'
        self.lip_file = f'MantellaDi_MantellaDialogu_00001D8B_1.lip'
        
        self.f4_use_wav_file1 = True
        self.f4_wav_file1 = f'MutantellaOutput1.wav'
        self.f4_wav_file2 = f'MutantellaOutput2.wav'
        self.f4_lip_file = f'00001ED2_1.lip'

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
        # The if block below checks if it's Fallout 4, if that's the case it will add the wav file in the mod_folder\Sound\Voice\Mantella.esp\ 
        # and alternate between two wavs to prevent access denied issues if Mantella.exe is trying to access a wav currently loaded in Fallout4
        if self.game == "fallout4":
            if self.f4_use_wav_file1:
                wav_file_to_use = self.f4_wav_file1
                subtitle += " Mantella1"
                self.f4_use_wav_file1 = False
            else:
                wav_file_to_use = self.f4_wav_file2
                subtitle += " Mantella2"
                self.f4_use_wav_file1 = True
            wav_file_path = f"{self.mod_folder}/{wav_file_to_use}"
            if os.path.exists(wav_file_path):
                os.remove(wav_file_path)
            shutil.copyfile(audio_file, wav_file_path)


        if audio_file is None or subtitle is None or audio_file == '' or subtitle == '':
            logging.error(f"Error saving voiceline to voice folders. Audio file: {audio_file}, subtitle: {subtitle}")
            return
        if self.add_voicelines_to_all_voice_folders == '1':
            for sub_folder in os.scandir(self.mod_folder):
                if sub_folder.is_dir():
                    #copy both the wav file and lip file if the game isn't Fallout4
                    if self.game !="fallout4":
                        shutil.copyfile(audio_file, f"{sub_folder.path}/{self.wav_file}")
                    shutil.copyfile(audio_file.replace(".wav", ".lip"), f"{sub_folder.path}/{self.f4_lip_file}")
        else:
            if self.game !="fallout4":
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
                if self.game != "fallout4": # delete both the wav file and lip file if the game isn't Fallout4
                    os.remove(f"{self.mod_folder}/{sub_folder}/{self.wav_file}")
                    os.remove(f"{self.mod_folder}/{sub_folder}/{self.lip_file}")
                else: #if the game is Fallout 4 only delete the lip file
                    os.remove(f"{self.mod_folder}/{sub_folder}/{self.f4_lip_file}")
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

        while True: # keep getting audio files from the queue until the queue is empty
            queue_output = await sentence_queue.get() # get the next audio file from the queue
            if queue_output is None:
                logging.info('End of sentences')
                break # stop getting audio files from the queue if the queue is empty

            await self.send_audio_to_external_software(queue_output) # send the audio file to the external software and start playing it.
            event.set() # set the event to let the process_response() function know that it can generate the next sentence while the last sentence's audio is playing

            audio_duration = await self.get_audio_duration(queue_output[0]) # get the duration of the next audio file
            logging.info(f"Waiting {int(round(audio_duration,4))} seconds...")
            await asyncio.sleep(audio_duration) # wait for the audio playback to complete before getting the next file
            
            #if Fallout4 is running the audio will be sync by checking if say line is set to false because the game can internally check if an audio file has finished playing
            # wait for the audio playback to complete before getting the next file
            if self.game == "fallout4":
                with open(f'{self.root_mod_folter}/_mantella_actor_count.txt', 'r', encoding='utf-8') as f:
                    mantellaactorcount = f.read().strip() 
                # Outer loop to continuously check the files
                while True:
                    all_false = True  # Flag to check if all files have 'false'

                    # Iterate through the number of files indicated by mantellaactorcount
                    for i in range(1, int(mantellaactorcount) + 1):
                        file_name = f'{self.root_mod_folter}/_mantella_say_line'
                        if i != 1:
                            file_name += f'_{i}'  # Append the file number for files 2 and above
                        file_name += '.txt'
                        with open(file_name, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if content.lower() != 'false':
                                all_false = False  # Set the flag to False if any file is not 'false'
                                break  # Break the for loop and continue the while loop
                    if all_false:
                        break  # Break the outer loop if all files are 'false'
                    await asyncio.sleep(0.1)  # Adjust the sleep duration as needed
            else: # if Skyrim's running then estimate audio duration to sync lip files
                audio_duration = await self.get_audio_duration(queue_output[0])
                # wait for the audio playback to complete before getting the next file
                logging.info(f"Waiting {int(round(audio_duration,4))} seconds...")
                await asyncio.sleep(audio_duration)
