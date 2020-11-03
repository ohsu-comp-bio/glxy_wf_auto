#!/usr/bin/env python

import json
import argparse
import string
import random
import os
import sys
import bioblend.galaxy

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proj_dir', help='Project directory to process.', required=True)
    parser.add_argument('--api_key', default='.galaxy/api_key',
                        help='Name of API key config file.')
    parser.add_argument('--patient')
    parser.add_argument('--workflow')
    parser.add_argument('--history_name')
    args = parser.parse_args()
    return args

def retrieve_api_key(filename):
    with open(filename, 'r') as api:
        api_key = api.readlines()[0]
    return api_key

def main():
    args = get_args()
    api_key = retrieve_api_key(os.path.join(os.environ['HOME'],args.api_key))
    galaxy_url = 'https://galaxy.ohsu.edu/galaxy/'
    gi = bioblend.galaxy.GalaxyInstance(url=galaxy_url, key=api_key)

    # Check workflow exists
    workflows = ["cancer_exome", "tatlow_piccolo_kallisto", "cnvkit", "star_fusion", "truseq_rna_exome"]
    if args.workflow not in workflows:
        sys.exit("Error: %s is not a valid workflow. Please check the workflow name." % (args.workflow))
        
    # Find history
    try:
        histories = gi.histories.get_histories(name=args.history_name)
        history_id = histories[0]['id']
        history_contents = gi.histories.show_history(history_id,contents=True)
        print("History found")
    except IndexError as e:
        print(args.history_name)
        print("Error: %s. Please check the history name is correct." % (e))

    # Make output directory
    date = history_contents[0]['create_time'].split("T")[0].replace("-","")
    history_name = histories[0]['name'].replace(" ","_")
    output_dir = "_".join([date,history_name])
    output_path = os.path.join(args.proj_dir,args.patient,args.workflow,output_dir)
    print("Creating directory %s" % (output_dir))
    os.makedirs(output_path)

    # Copy datasets for each step to output directory
    meta = open(os.path.join(output_path,"galaxy_history_metadata.json"),"w")
    meta.write(json.dumps(history_contents))
    meta.close()
    for step in history_contents: 
        if step['type'] == "file" and step['state'] == "ok":
            dataset_id = step['id']
            name=step['name'].replace(" ","_")
            print("Downloading data from step named %s" % (step['name']))
            #print(json.dumps(step))
            gi.datasets.download_dataset(dataset_id, file_path=os.path.join(output_path,name), use_default_filename=False,wait_for_completion=True)

if __name__ == "__main__":
    main()
