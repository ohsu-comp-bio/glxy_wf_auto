from __future__ import print_function

import logging
import os
import sys
import json
import random
import string

import bioblend.galaxy
import dotenv
import dynamic_yaml

import glxy_wf.galaxy_fs as galaxy_fs

def fail(error, *args):
    logging.error(error, *args)
    sys.exit(1)

def dump_config():
    path = os.path.join(os.path.dirname(__file__), "config.yml")
    print(open(path).read())

def collect_inputs(config_path):
    # Load YAML config file.
    config_fh = open(config_path)
    logging.info("Config path: %s",(config_path))
    config = dynamic_yaml.load(config_fh)
    logging.info("Config: %s",(config))

    galaxy_api_key = os.getenv("GALAXY_API_KEY")
    if not galaxy_api_key:
        fail("missing GALAXY_API_KEY; set this in the environment or .env file")


    def require_config(key):
        v = config.get(key)
        if not v:
            fail('missing "%s" in the config', key)
        return v


    # Load config
    galaxy_url = require_config("galaxy_url")
    common_inputs = require_config("common_inputs")
    workflow_name = require_config("workflow")
    library_folder_name = require_config("library_folder")
    sample_conf = require_config("sample")
    workflow_params_config = config.get("workflow_params", {})
    replacement_params = config.get("replacement_params", {})

    # Create galaxy object and get workflow descsription
    gi = bioblend.galaxy.GalaxyInstance(url=galaxy_url, key=galaxy_api_key)
    wfdesc = get_workflow_description(gi, workflow_name)

    # Create History
    sample = sample_conf["name"]
    alphanum = string.ascii_lowercase + string.digits
    rand = ''.join(random.choice(alphanum) for x in range(8))
    history_name = workflow_name + " " + sample + " " + rand

    logging.info("Creating history: %s", history_name)
    history = get_or_create_history(gi, history_name)
    history_id = history["id"]

    # Find files on filesystem
    logging.info("Collecting files from filesystem")
    sample_files = sample_conf["files"]

    # Upload files to Data Library
    logging.info("Uploading sample data")
    file_type = sample_conf["filetype"]
    sample_ids = []
    for sf in sample_files:
        sample_ids.append(upload_dataset(gi, sf, file_type, library_folder_name)["id"])

    # Create collection list in history
    logging.info("Populating sample data in history")
    sample_data = create_dataset_or_collection_in_history(gi, sample, history_id, sample_ids)
    logging.info("sample collection data: %s", sample_data)

    logging.info("Preparing to invoke workflow")
    common_inputs_library_ids = {}
    for k, v in common_inputs.items():
        logging.info('''Collecting common inputs from Galaxy: "%s" "%s"''', k, v)
        f = galaxy_fs.get_path(gi, v)
        common_inputs_library_ids[k] = f["id"]

    steps_by_label = {}
    inputs = {}
    for step in wfdesc["steps"].values():
        label = step.get("label")
        uuid = step.get("uuid")
        steps_by_label[label] = step
        if label in common_inputs_library_ids:
            lib_id = common_inputs_library_ids[label]
            inputs[uuid] = {
                "id": lib_id,
                "src": "ld",
            }

        if label == "INPUT":
            inputs[uuid] = {
                "id": sample_data["id"],
                "src": sample_data["src"],
            }


    params = {}
    if workflow_params_config:
        for step_label, step_params in workflow_params_config.items():
            if step_label not in steps_by_label:
                fail('configuring workflow params, missing step with label {}', step_label)
            step_id = steps_by_label[step_label]['id']
            if steps_by_label[step_label]['type'] == 'subworkflow':
               sub_dict = {}
               for sub_label, sub_params in step_params.items():
                   sub_wfdesc = get_workflow_description(gi, steps_by_label[step_label]['name'])
                   sub_wf_step = [v for k,v in sub_wfdesc['steps'].items() if v['label'] == sub_label][0]
                   param_key, param_value = list(sub_params.items())[0]
                   sub_id = "|".join([str(sub_wf_step['id']),param_key])
                   sub_dict[sub_id] = param_value
               params[step_id] = sub_dict
            else:
                step_dict = {}
                for step_k, step_v in step_params.items():
                     step_dict[step_k] = step_v
                
                params[step_id] = step_dict

    # Replacement params
    replace_dict = {}
    for k, v in replacement_params.items():
       logging.info("Collecting Replacement params: %s %s", k, v) 
       replace_dict[k] = v

    # Invoke workflow
    logging.info("Invoking workflow")
    workflow_id = wfdesc["uuid"]
    logging.info("Replacement params: %s", replace_dict)
    logging.info("Workflow params: %s", params)
    logging.info("Inputs: %s", inputs)

    res = gi.workflows.invoke_workflow(workflow_id, inputs, history_id=history_id,
        params=params, import_inputs_to_history=False, replacement_params=replace_dict)
    print(json.dumps(res, indent=2))

def get_or_create_history(gi, name):
    histories = gi.histories.get_histories(name=name)
    if len(histories) > 1:
        raise Exception("multiple histories found named {}".format(name))

    if len(histories) == 0:
        return gi.histories.create_history(name)

    return histories[0]

def get_workflow_description(gi, workflow_name):
    logging.info("Getting workflow description from Galaxy")
    wf = gi.workflows.get_workflows(name=workflow_name)
    if not wf:
        fail('''can't find workflow named "%s"''', workflow_name)
    if len(wf) > 1:
        fail('found multiple workflows named "%s"', workflow_name)

    wfid = wf[0]["id"]
    wfdesc = gi.workflows.export_workflow_dict(wfid)
    return wfdesc


def get_library_folder(gi, library_folder_name):
    galaxy_fs.make_path(gi.libraries, library_folder_name)
    data_folder = galaxy_fs.get_path(gi, library_folder_name)
    data_folder_id = data_folder["id"]

    lib_name = library_folder_name.split("/")[0]
    libs = gi.libraries.get_libraries(name=lib_name)
    if len(libs) == 0:
        fail('''couldn't find library named "%s"''', lib_name)

    lib = libs[0]
    lib_id = lib["id"]
    return lib_id, data_folder_id

def upload_dataset(gi, data_path, file_type, folder_name):
    lib_id, folder_id = get_library_folder(gi, folder_name)
    data_name = os.path.basename(data_path)
    galaxy_dataset = folder_name + "/" + data_name
    galaxy_path = galaxy_fs.get_path(gi, galaxy_dataset)
    if not galaxy_path:
        logging.info("Uploading: %s", galaxy_dataset)
        logging.info("File type: %s", file_type)
        logging.info("File path: %s", data_path)
        galaxy_path = gi.libraries.upload_from_galaxy_filesystem(
            lib_id, data_path, folder_id, link_data_only="link_to_files", file_type=file_type)[0]
    else:
        logging.info('''Skipping upload, file exists at "{}"'''.format(galaxy_path))

    dataset = {"id": galaxy_path["id"], "name": data_name, "src": "ld"}

    return dataset

def create_dataset_or_collection_in_history(gi, name, history_id, ids):
    elements = []
    logging.info("Adding sample datasets to history")
    for i, f in enumerate(ids):
        fh = gi.histories.upload_dataset_from_library(history_id, f)
        elements.append({
            "id": fh["id"],
            "src": "hda",
            "name": os.path.basename(fh["name"]).rstrip("."+fh["extension"])
        })

    if len(elements) > 1:
        logging.info("Creating collection")
        collection = gi.histories.create_dataset_collection(history_id, {
            "collection_type": "list",
            "name": name,
            "element_identifiers": elements
        })
        collection['src'] = "hdca"
    else:
        collection = elements[0]

    return collection

