# conert ./data/skyrim_characters.csv to ./data/skyrim_characters/{id}_{name}.json

import csv
import json
import os

def csv2json(csv_file, json_directory):
    # make sure dir exists
    os.makedirs(json_directory, exist_ok=True)
    with open(csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # print(row)
            json_file = os.path.join(json_directory, '_' + row['name'] + '.json')
            with open(json_file, 'w') as outfile:
                json.dump(row, outfile, indent=4)
                print(f'wrote {json_file}')

if __name__ == '__main__':
    csv2json('./data/skyrim_characters.csv', './data/skyrim_characters')