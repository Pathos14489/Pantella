print("Importing utils.py")
from src.logging import logging, time
import re
import string
import sys
import os
from shutil import rmtree
from charset_normalizer import detect
logging.info("Imported required libraries in utils.py")

def time_it(func):
    """Decorator to time a function's execution time"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logging.info(f"Function {func.__name__} took {round(end - start, 5)} seconds to execute")
        return result
    return wrapper


def clean_text(text):
    """Clean up text by removing punctuation and extra whitespace"""
    # Remove all punctuation from the sentence
    text_cleaned = text.translate(str.maketrans('', '', string.punctuation))
    # Remove any extra whitespace
    text_cleaned = re.sub('\s+', ' ', text_cleaned).strip()
    text_cleaned = text_cleaned.lower()

    return text_cleaned


def resolve_path():
    """Resolve the path to the executable or the script directory"""
    if getattr(sys, 'frozen', False):
        resolved_path = os.path.dirname(sys.executable)
    else:
        resolved_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return resolved_path


def get_file_encoding(file_path):
    """Get the encoding of a file using charset_normalizer"""
    with open(file_path,'rb') as f:
        data = f.read()
    encoding = detect(data).get("encoding")
    return encoding

def activation_name_exists(transcript_cleaned, activation_name):
    """Identifies keyword in the input transcript"""
    keyword_found = False
    if activation_name in transcript_cleaned:
        keyword_found = True
    if activation_name in transcript_cleaned.lower():
        keyword_found = True
    if activation_name.lower() in transcript_cleaned:
        keyword_found = True
    if activation_name.lower() in transcript_cleaned.lower():
        keyword_found = True
    return keyword_found

def cleanup_mei(remove_mei_folders):
    """
    Rudimentary workaround for https://github.com/pyinstaller/pyinstaller/issues/2379
    """
    mei_bundle = getattr(sys, "_MEIPASS", False)

    if mei_bundle:
        dir_mei, current_mei = mei_bundle.split("_MEI")
        mei_files = []
        for file in os.listdir(dir_mei):
            if file.startswith("_MEI") and not file.endswith(current_mei):
                mei_files.append(file)
        
        if (len(mei_files) > 0):
            if remove_mei_folders:
                file_removed = 0
                for file in mei_files:
                    try:
                        rmtree(os.path.join(dir_mei, file))
                        file_removed += 1
                    except PermissionError:  # mainly to allow simultaneous pyinstaller instances
                        pass
                logging.info(f'{file_removed} previous runtime folder(s) cleaned up from PantellaSoftware/data/tmp')
            else:
                logging.warn(f"Warning: {len(mei_files)} previous Pantella.exe runtime folder(s) found in PantellaSoftware/data/tmp. See PantellaSoftware/config.json's remove_mei_folders setting for more information.")
        
def get_time_group(in_game_time):
    """Get the time group based on the in-game time"""
    in_game_time = int(in_game_time)

    if in_game_time <= 4:
        time_group = 'at night'
    elif in_game_time <= 7:
        # NPCs wake up between 6 and 8
        time_group = 'in the early morning'
    elif in_game_time <= 11:
        # shops open at 8
        time_group = 'in the morning'
    elif in_game_time <= 14:
        time_group = 'in the afternoon'
    elif in_game_time <= 19:
        time_group = 'in the early evening'
    elif in_game_time <= 21:
        # shops shut at 8
        time_group = 'in the late evening'
    elif in_game_time <= 24:
        # NPCs sleep between 8 and 10
        time_group = 'at night'
    
    return time_group