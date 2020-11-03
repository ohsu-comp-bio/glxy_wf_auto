from __future__ import print_function

import argparse
import logging
import os
import sys

import bioblend.galaxy
import coloredlogs
import dotenv

import glxy_wf.collect_inputs
import glxy_wf.collect_outputs
import glxy_wf.galaxy_fs

coloredlogs.install(level=logging.INFO, fmt="%(levelname)s: %(message)s")

# Load ".env" file, where galaxy api key may be stored.
dotenv.load_dotenv(dotenv.find_dotenv())

parser = argparse.ArgumentParser(description="Utilities for interacting with data and Galaxy.")
sub = parser.add_subparsers()

def default(args):
    parser.print_help()
    sys.exit(1)

parser.set_defaults(func=default)

def fail(error, *args):
    logging.error(error, *args)
    sys.exit(1)

def do_collect_inputs(args):
    glxy_wf.collect_inputs.collect_inputs(args.config)

collect_inputs = sub.add_parser("collect_inputs", help="Collect workflow input files and generate inputs config.")
collect_inputs.set_defaults(func=do_collect_inputs)
collect_inputs.add_argument("config", help="config file describing where to find input files")

def do_collect_inputs_config(args):
    glxy_wf.collect_inputs.dump_config()

collect_inputs_config = sub.add_parser("collect_inputs_config", help="Dump the config template for collect_inputs")
collect_inputs_config.set_defaults(func=do_collect_inputs_config)

def do_make_path(args):
    galaxy_api_key = os.getenv("GALAXY_API_KEY")
    if not galaxy_api_key:
        fail("missing GALAXY_API_KEY; set this in the environment or .env file")

    gi = bioblend.galaxy.GalaxyInstance(url=args.url, key=galaxy_api_key)
    glxy_wf.galaxy_fs.make_path(gi.libraries, args.path)

make_path = sub.add_parser("make_path", help="Create a data library + folder path in Galaxy.")
make_path.set_defaults(func=do_make_path)
make_path.add_argument("url", help="URL of Galaxy instance.")
make_path.add_argument("path", help="Path to create, e.g. My library/folder/subfolder")

def main():
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
