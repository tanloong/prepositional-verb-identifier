#!/usr/bin/env python3
# -*- coding=utf-8 -*-

# https://spacy.io/usage/rule-based-matching
# https://spacy.io/api/data-formats
# https://universaldependencies.org/u/pos/index.html
# https://universaldependencies.org/format.html#morphological-annotation
# https://universaldependencies.org/en/dep/

# spacy's POS tagging is less accurate than stanza:
# "The tanned skin of his arms and face glistened (spacy: VBN, stanza: VBD) with sweat."
# "The decision to free him rests (spacy:NOUN, stanza:VBZ) with the Belgian Justice Minister."

# The package takes plain English text as input and outputs instances of "verb + preposition + noun groups" where the verb dominates the preposition.

# For example, it will find "goes over" in "She goes over the question". However, it may not identify "goes over" in the sentence "Someone goes over there" because the "goes over" here is not used as a phrasal verb but in the literal meaning.

import argparse
import glob
import logging
import os
import sys
from typing import List

from .about import __version__
from .util import PREVProcedureResult


class PREVUI:
    def __init__(self) -> None:
        self.args_parser: argparse.ArgumentParser = self.create_args_parser()
        self.options: argparse.Namespace = argparse.Namespace()

    def create_args_parser(self) -> argparse.ArgumentParser:
        args_parser = argparse.ArgumentParser(prog="prev")
        args_parser.add_argument(
            "--version",
            action="store_true",
            default=False,
            help="Show version and exit.",
        )
        args_parser.add_argument(
            "--input-file",
            dest="input_file",
            default=None,
            help="Specify a file containing a list of input filenames",
        )
        args_parser.add_argument(
            "--config-file",
            "-c",
            dest="config_file",
            default=None,
            help=(
                "Specify file path of the config .py file where you can customize dependency"
                ' patterns to search. A non-empty "pattern" variable assigning to a list in the'
                " config file will override the default dependency patterns."
            ),
        )
        args_parser.add_argument(
            "--expand-wildcards",
            dest="expand_wildcards",
            action="store_true",
            default=False,
            help=(
                "Print all files that match your wildcard pattern. This can help you ensure that"
                " your pattern matches all desired files and excludes any unwanted ones. Note"
                " that files that do not exist on the computer will not be included in the"
                " output, even if they match the specified pattern."
            ),
        )
        args_parser.add_argument(
            "--pretokenized",
            dest="is_pretokenized",
            action="store_true",
            default=False,
            help=(
                "Specify that input texts have already been tokenized to newline-separated"
                " sentences. This option by default is False."
            ),
        )
        args_parser.add_argument(
            "--visualize",
            dest="is_visualize",
            action="store_true",
            default=False,
            help="Visualize parse trees.",
        )
        args_parser.add_argument(
            "--refresh",
            dest="is_refresh",
            action="store_true",
            default=False,
            help="Ignore existing svg files and intermediate annotated files (*.json).",
        )
        args_parser.add_argument(
            "--no-query",
            dest="is_no_query",
            action="store_true",
            default=False,
            help="Just parse texts and exit.",
        )
        args_parser.add_argument(
            "-t",
            "--text",
            default=None,
            help=(
                "Pass text through the command line. If not specified, the program will read"
                " input from input files."
            ),
        )
        args_parser.add_argument(
            "-p",
            "--print",
            dest="print_what",
            choices=["matched", "unmatched"],
            default="matched",
            help=(
                "Specify whether to print matched or unmatched sentences. By default, this"
                ' option is set to "matched".'
            ),
        )
        args_parser.add_argument(
            "--quiet",
            dest="is_quiet",
            action="store_true",
            default=False,
            help="Suppress regular logging messages",
        )
        args_parser.add_argument(
            "--stdout",
            dest="is_stdout",
            action="store_true",
            default=False,
            help="Output to the standard out instead of saving it to a file.",
        )
        args_parser.add_argument(
            "--interactive",
            "-I",
            dest="is_interactive",
            action="store_true",
            default=False,
            help="Run in interactive mode",
        )
        args_parser.add_argument(
            "--matching-process",
            dest="n_matching_process",
            default=3,
            type=int,
            help="Specify the number of parallel processes for the matching procedure.",
        )
        return args_parser

    def parse_args(self, argv: List[str]) -> PREVProcedureResult:
        options, ifile_list = self.args_parser.parse_known_args(argv[1:])
        if options.input_file is not None:
            if not os.path.exists(options.input_file):
                return False, f"No such file as \n\n{options.input_file}"
            with open(options.input_file, "r", encoding="utf-8") as f:
                ifile_list += [ifile.strip() for ifile in f.readlines() if ifile.strip()]
        self.verified_ifile_list = None
        if options.text is None:
            verified_ifile_list = []
            for f in ifile_list:
                if os.path.isfile(f):
                    verified_ifile_list.append(f)
                elif glob.glob(f):
                    verified_ifile_list.extend(glob.glob(f))
                else:
                    return (False, f"No such file as \n\n{f}")
            if verified_ifile_list:
                self.verified_ifile_list = verified_ifile_list
        else:
            options.is_refresh = True

        if options.is_interactive:
            options.is_stdout = True
            options.is_refresh = True
            options.is_quiet = True

        if options.is_quiet:
            logging.basicConfig(format="%(message)s", level=logging.WARNING)
        else:
            logging.basicConfig(format="%(message)s", level=logging.INFO)

        self.init_kwargs = {
            "is_pretokenized": options.is_pretokenized,
            "is_refresh": options.is_refresh,
            "is_no_query": options.is_no_query,
            "is_visualize": options.is_visualize,
            "is_stdout": options.is_stdout,
            "is_interactive": options.is_interactive,
            "print_what": options.print_what,
            "n_matching_process": options.n_matching_process,
            "config_file": options.config_file,
        }
        self.options = options
        return True, None

    def check_python(self) -> PREVProcedureResult:
        v_info = sys.version_info
        if (v_info.minor >= 6 and v_info.minor <= 10) and v_info.major == 3:
            return True, None
        else:
            return (
                False,
                (
                    f"Error: Python {v_info.major}.{v_info.minor} is not supported."
                    " PREV only supports Python 3.6 -- 3.10, because the master branch"
                    " of Stanza"
                    " (https://github.com/stanfordnlp/stanza/issues/951#issuecomment-1035616707)"
                    " only supports up to 3.10. You can install a 3.10 verion"
                    " (https://www.python.org/downloads/) and run PREV in a virtual"
                    " environment with `virtualenv`"
                    " (https://virtualenv.pypa.io/en/latest/index.html)."
                ),
            )

    def run_tmpl(func):  # type: ignore
        def wrapper(self, *args, **kwargs):
            sucess, err_msg = self.check_python()
            if not sucess:
                return sucess, err_msg
            func(self, *args, **kwargs)  # type: ignore
            self.exit_routine()
            return True, None

        return wrapper

    def run_on_text(self) -> PREVProcedureResult:
        from .prev import PREV

        extractor = PREV(**self.init_kwargs)
        return extractor.run_on_text(self.options.text)

    def run_on_ifiles(self) -> PREVProcedureResult:
        from .prev import PREV

        extractor = PREV(**self.init_kwargs)
        return extractor.run_on_ifiles(self.verified_ifile_list)  # type:ignore

    def run_interactive(self) -> PREVProcedureResult:
        from .prev import PREV

        extractor = PREV(**self.init_kwargs)
        return extractor.run_interactive()

    def run(self) -> PREVProcedureResult:
        if self.options.version:
            return self.show_version()
        elif self.options.expand_wildcards:
            return self.expand_wildcards()
        elif self.options.text is not None:
            return self.run_on_text()
        elif self.verified_ifile_list is not None:
            return self.run_on_ifiles()
        elif self.options.is_interactive:
            return self.run_interactive()
        else:
            self.args_parser.print_help()
            return True, None

    def show_version(self) -> PREVProcedureResult:
        print(__version__)
        return True, None

    def expand_wildcards(self) -> PREVProcedureResult:
        if self.verified_ifile_list:
            print("Input files:")
            for ifile in sorted(self.verified_ifile_list):
                print(f" {ifile}")
        return True, None


def main() -> None:
    ui = PREVUI()
    success, err_msg = ui.parse_args(sys.argv)
    if not success:
        logging.critical(err_msg)
        sys.exit(1)
    success, err_msg = ui.run()
    if not success:
        logging.critical(err_msg)
        sys.exit(1)
