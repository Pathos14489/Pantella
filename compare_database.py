
import csv
import json
import os
import argparse

import src.conversation_manager as cm
import src.character_db as character_db

parser = argparse.ArgumentParser(description='Compare two character dbs')
if __name__ == '__main__':
    print("Loading config...")
    parser.add_argument('path', type=str, help='path to character db being compared against the current character db')
    parser.add_argument('--output', type=str, help='path to output patch file')
    
    conversation_manager = cm.conversation_manager(config_file='config.ini', initialize=False) # Partially load conversation manager
    conversation_manager2 = cm.conversation_manager(config_file='config.ini', initialize=False) # Partially load conversation manager TODO: a bit wasteful of compute since it technically double loads the main db but eh, doens't really matter tbh
    conversation_manager2.config.character_database_file = parser.parse_args().path
    
    print("Comparing " + conversation_manager.config.character_database_file + " to " + parser.parse_args().path)
    print("Loading character dbs...")
    other_db = character_db.CharacterDB(conversation_manager2)
    diff = conversation_manager.character_database.compare(other_db)
    if len(diff) < 100:
        print("Differences: " + str(diff))
    else:
        print("Too many differences to print to console, set --output to output to file")
    print("Total differences: " + str(len(diff)))
    if parser.parse_args().output:
        with open(parser.parse_args().output, 'w') as f:
            json.dump(diff, f)
