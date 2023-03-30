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
import os
import sys
from typing import List

from .util import PREVProcedureResult


class PREVUI:
    def __init__(self) -> None:
        self.args_parser: argparse.ArgumentParser = self.create_args_parser()
        self.options: argparse.Namespace = argparse.Namespace()

    def create_args_parser(self) -> argparse.ArgumentParser:
        args_parser = argparse.ArgumentParser(prog="prev")
        args_parser.add_argument(
            "--pretokenized",
            dest="is_pretokenized",
            action="store_true",
            default=False,
            help="Specify that input texts have already been tokenized to newline-separated sentences. This option by default is False.",
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
            help="Ignore existing svg files and intermediate annotated files (*.pkl).",
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
        return args_parser

    def parse_args(self, argv: List[str]) -> PREVProcedureResult:
        options, ifile_list = self.args_parser.parse_known_args(argv[1:])
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
        self.init_kwargs = {
            "is_pretokenized":options.is_pretokenized,
            "is_refresh":options.is_refresh,
            "is_visualize": options.is_visualize,
            "print_what": options.print_what,
        }
        self.options = options
        return True, None

    def check_python(self) -> PREVProcedureResult:
        v_info = sys.version_info
        if (v_info.minor >= 6 and v_info.minor <= 9) and v_info.major == 3:
            return True, None
        else:
            return (
                False,
                f"Error: Python {v_info.major}.{v_info.minor} is not supported."
                " VerbPrepExtractor only supports Python 3.6 -- 3.9, because the master branch"
                " of Stanza"
                " (https://github.com/stanfordnlp/stanza/issues/951#issuecomment-1035616707)"
                " only supports up to 3.9. You can install a 3.9 verion"
                " (https://www.python.org/downloads/) and run VerbPrepExtractor in a virtual"
                " environment with `virtualenv`"
                " (https://virtualenv.pypa.io/en/latest/index.html).",
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

    def run(self) -> PREVProcedureResult:
        if self.options.text is not None:
            return self.run_on_text()
        elif self.verified_ifile_list is not None:
            return self.run_on_ifiles()
        else:
            self.args_parser.print_help()
            return True, None


def main() -> None:
    ui = PREVUI()
    success, err_msg = ui.parse_args(sys.argv)
    if not success:
        print(err_msg)
        sys.exit(1)
    success, err_msg = ui.run()
    if not success:
        print(err_msg)
        sys.exit(1)
