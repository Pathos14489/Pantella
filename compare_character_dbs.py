
import csv
import json
import os
import argparse

import src.config_loader as config_loader
import src.character_db as character_db

parser = argparse.ArgumentParser(description='Compare two character dbs')
if __name__ == '__main__':
    print("Loading config...")
    parser.add_argument('path1', type=str, help='path to first character db')
    parser.add_argument('path2', type=str, help='path to second character db')
    parser.add_argument('--output', type=str, help='path to output file')
    config1 = config_loader.ConfigLoader("./config.ini")
    config1.character_df_file = parser.parse_args().path1
    config2 = config_loader.ConfigLoader("./config.ini")
    config2.character_df_file = parser.parse_args().path2
    print("Comparing " + config1.character_df_file + " to " + config2.character_df_file)
    print("Loading character dbs...")
    db1 = character_db.CharacterDB(config1)
    db2 = character_db.CharacterDB(config2)
    diff = db1.compare(db2)
    print("Total differences: " + str(len(diff)))
    print("Differences: " + str(diff))
    if parser.parse_args().output:
        with open(parser.parse_args().output, 'w') as f:
            json.dump(diff, f)
