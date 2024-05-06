#!/usr/bin/env python3
"""
The purpose of this file is to define a thin CLI interface for your app

DO NOT CHANGE the name of the file
"""

import argparse
import sys

import app
from mmif import Mmif
from clams import AppMetadata


def metadata_to_argparser(app_metadata: AppMetadata) -> argparse.ArgumentParser:
    """
    Automatically generate an argparse.ArgumentParser from parameters specified in the app metadata (metadata.py).
    """

    parser = argparse.ArgumentParser(description="CLI for CLAMS app")

    # parse cli args from app parameters
    for parameter in app_metadata.parameters:
        a = parser.add_argument(
            f"--{parameter.name}",
            help=parameter.description,
            nargs=1,
            action="store",
            type=str)
        if parameter.choices is not None:
            a.choices = parameter.choices
        if parameter.default is not None:
            a.help += f" (default: {parameter.default})"
            # then we don't have to add default values to the arg_parser
            # since that's handled by the app._refined_params() method.
        if parameter.multivalued:
            a.nargs = '+'
        if parameter.type == "boolean":
            a.nargs = '?'
            a.action = "store_true"
    parser.add_argument('IN_MMIF_FILE', nargs='?', type=argparse.FileType('r'),
                        # will check if stdin is a keyboard, and return None if it is
                        default=None if sys.stdin.isatty() else sys.stdin)
    parser.add_argument('OUT_MMIF_FILE', nargs='?', type=argparse.FileType('w'), default=sys.stdout)
    return parser


if __name__ == "__main__":
    clamsapp = app.get_app()
    arg_parser = metadata_to_argparser(app_metadata=clamsapp.metadata)
    args = arg_parser.parse_args()
    if args.IN_MMIF_FILE:
        in_data = Mmif(args.IN_MMIF_FILE.read())
        # since flask webapp interface will pass parameters as "unflattened" dict to handle multivalued parameters
        # (https://werkzeug.palletsprojects.com/en/latest/datastructures/#werkzeug.datastructures.MultiDict.to_dict)
        # we need to convert arg_parsers results into a similar structure, which is the dict values are wrapped in lists
        params = {}
        for pname, pvalue in vars(args).items():
            if pvalue is None or pname in ['IN_MMIF_FILE', 'OUT_MMIF_FILE']:
                continue
            elif isinstance(pvalue, list):
                params[pname] = pvalue
            else:
                params[pname] = [pvalue]
        args.OUT_MMIF_FILE.write(clamsapp.annotate(in_data, **params))
    else:
        arg_parser.print_help()
        sys.exit(1)