#!/usr/bin/env python3

# https://spacy.io/usage/rule-based-matching
# https://spacy.io/api/data-formats
# https://universaldependencies.org/u/pos/index.html
# https://universaldependencies.org/format.html#morphological-annotation
# https://universaldependencies.org/en/dep/

# spacy's POS tagging is less accurate than stanza:
# "The tanned skin of his arms and face glistened (spacy: VBN, stanza: VBD) with sweat."
# "The decision to free him rests (spacy:NOUN, stanza:VBZ) with the Belgian Justice Minister."

# The package takes plain English text as input and outputs instances of "verb + preposition + noun groups" where the verb dominates the preposition.

# For example, it will find "goes over" in "She goes over the question". However, it does not identify "goes over" in the sentence "Someone goes over there" because the "goes over" here is not used as a phrasal verb but in the literal meaning.

import argparse
import glob
import logging
import os
import sys
from typing import List

from .about import __version__
from .depmatch_runner import Depmatch_Runner
from .tokenize_runner import Tokenize_Runner
from .util import Prev_Procedure_Result


class PREVUI:
    def __init__(self) -> None:
        self.args_parser: argparse.ArgumentParser = self.create_args_parser()
        self.options: argparse.Namespace = argparse.Namespace()

    def __add_log_levels(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--quiet",
            dest="is_quiet",
            action="store_true",
            default=False,
            help="disable all loggings",
        )
        parser.add_argument(
            "--verbose",
            dest="is_verbose",
            action="store_true",
            default=False,
            help="enable verbose loggings",
        )

    def create_args_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="prev")
        parser.add_argument(
            "--version",
            action="store_true",
            default=False,
            help="Show version and exit.",
        )
        self.__add_log_levels(parser)
        subparsers: argparse._SubParsersAction = parser.add_subparsers(title="commands", dest="command")
        self.depmatch_parser = self.create_depmatch_parser(subparsers)
        self.tokenize_parser = self.create_tokenize_parser(subparsers)

        # self.annotate_parser = self.create_annotate_parser(subparsers)
        return parser

    def create_tokenize_parser(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        tokenize_parser = subparsers.add_parser("tokenize", help="tokenize")
        tokenize_parser.add_argument(
            "--input-file",
            dest="input_file",
            default=None,
            help="Specify a file containing a list of input filenames.",
        )
        tokenize_parser.add_argument(
            "--refresh",
            dest="is_refresh",
            action="store_true",
            default=False,
            help="Don't use cache files even if they exist. (*.json).",
        )
        tokenize_parser.add_argument(
            "--text",
            "-t",
            default=None,
            help=(
                "Pass text through the command line. If not specified, the program will read"
                " input from input files."
            ),
        )
        tokenize_parser.add_argument(
            "--stdout",
            dest="is_stdout",
            action="store_true",
            default=False,
            help="Output to the standard out instead of saving it to a file.",
        )
        tokenize_parser.add_argument(
            "--interact",
            "-I",
            dest="is_interact",
            action="store_true",
            default=False,
            help="Run in interactive mode",
        )
        tokenize_parser.add_argument(
            "--pretokenized",
            dest="is_pretokenized",
            action="store_true",
            default=False,
            help=(
                "Specify that input texts have already been tokenized to newline-separated"
                " sentences. This option by default is False."
            ),
        )
        tokenize_parser.add_argument(
            "--n-process",
            dest="n_process",
            default=3,
            type=int,
            help="Specify the number of parallel processes.",
        )
        self.__add_log_levels(tokenize_parser)
        tokenize_parser.set_defaults(func=self.parse_tokenize_args, cls=Tokenize_Runner)
        return tokenize_parser

    def create_depmatch_parser(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        depmatch_parser = subparsers.add_parser("depmatch", help="dependency match")
        depmatch_parser.add_argument(
            "--pattern-file",
            "-c",
            dest="pattern_file",
            default=None,
            help=(
                "Specify file path of the config .py file where you can customize dependency"
                ' patterns to search. A non-empty "pattern" variable assigning to a list in the'
                " config file will override the default dependency patterns."
            ),
        )
        depmatch_parser.add_argument(
            "--input-file",
            dest="input_file",
            default=None,
            help="Specify a file containing a list of input filenames.",
        )
        depmatch_parser.add_argument(
            "--visualize",
            dest="is_visualize",
            action="store_true",
            default=False,
            help="Visualize parse trees.",
        )
        depmatch_parser.add_argument(
            "--refresh",
            dest="is_refresh",
            action="store_true",
            default=False,
            help="Don't use cache files even if they exist. (*.json).",
        )
        depmatch_parser.add_argument(
            "--no-query",
            dest="is_no_query",
            action="store_true",
            default=False,
            help="Just parse texts and exit.",
        )
        depmatch_parser.add_argument(
            "--text",
            "-t",
            default=None,
            help=(
                "Pass text through the command line. If not specified, the program will read"
                " input from input files."
            ),
        )
        depmatch_parser.add_argument(
            "--print",
            "-p",
            dest="print_what",
            choices=["matched", "unmatched"],
            default="matched",
            help=(
                "Specify whether to print matched or unmatched sentences. By default, this"
                ' option is set to "matched".'
            ),
        )
        depmatch_parser.add_argument(
            "--stdout",
            dest="is_stdout",
            action="store_true",
            default=False,
            help="Output to the standard out instead of saving it to a file.",
        )
        depmatch_parser.add_argument(
            "--interact",
            "-I",
            dest="is_interact",
            action="store_true",
            default=False,
            help="Run in interactive mode",
        )
        depmatch_parser.add_argument(
            "--pretokenized",
            dest="is_pretokenized",
            action="store_true",
            default=False,
            help=(
                "Specify that input texts have already been tokenized to newline-separated"
                " sentences. This option by default is False."
            ),
        )
        depmatch_parser.add_argument(
            "--n-process",
            dest="n_process",
            default=3,
            type=int,
            help="Specify the number of parallel processes.",
        )
        self.__add_log_levels(depmatch_parser)
        depmatch_parser.set_defaults(func=self.parse_depmatch_args, cls=Depmatch_Runner)
        return depmatch_parser

    def parse_tokenize_args(self, options: argparse.Namespace, ifiles: list[str]) -> Prev_Procedure_Result:
        logging.debug("Parsing 'tokenize' options...")
        if options.input_file is not None:
            if not os.path.exists(options.input_file):
                return False, f"No such file as \n\n{options.input_file}"
            with open(options.input_file, encoding="utf-8") as f:
                ifiles += [ifile.strip() for ifile in f.readlines() if ifile.strip()]
        self.verified_ifiles = None
        if options.text is None:
            verified_ifiles = []
            for f in ifiles:
                if os.path.isfile(f):
                    verified_ifiles.append(f)
                elif glob.glob(f):
                    verified_ifiles.extend(glob.glob(f))
                else:
                    return (False, f"No such file as \n\n{f}")
            if verified_ifiles:
                self.verified_ifiles = verified_ifiles
        else:
            options.is_refresh = True

        self.init_kwargs = {
            "is_refresh": options.is_refresh,
            "is_stdout": options.is_stdout,
            "is_pretokenized": options.is_pretokenized,
            "n_process": options.n_process,
        }
        self.options = options
        return True, None

    def parse_depmatch_args(self, options: argparse.Namespace, ifiles: list[str]) -> Prev_Procedure_Result:
        logging.debug("Parsing 'depmatch' options...")
        if options.input_file is not None:
            if not os.path.exists(options.input_file):
                return False, f"No such file as \n\n{options.input_file}"
            with open(options.input_file, encoding="utf-8") as f:
                ifiles += [ifile.strip() for ifile in f.readlines() if ifile.strip()]
        self.verified_ifiles = None
        if options.text is None:
            verified_ifiles = []
            for f in ifiles:
                if os.path.isfile(f):
                    verified_ifiles.append(f)
                elif glob.glob(f):
                    verified_ifiles.extend(glob.glob(f))
                else:
                    return (False, f"No such file as \n\n{f}")
            if verified_ifiles:
                self.verified_ifiles = verified_ifiles
        else:
            options.is_refresh = True

        self.init_kwargs = {
            "is_refresh": options.is_refresh,
            "is_no_query": options.is_no_query,
            "is_visualize": options.is_visualize,
            "is_stdout": options.is_stdout,
            "is_pretokenized": options.is_pretokenized,
            "print_what": options.print_what,
            "n_process": options.n_process,
            "pattern_file": options.pattern_file,
        }
        self.options = options
        return True, None

    def parse_args(self, argv: List[str]) -> Prev_Procedure_Result:
        options, ifile_list = self.args_parser.parse_known_args(argv[1:])
        if getattr(options, "is_interact", False):
            options.is_stdout = True
            options.is_refresh = True
            if not options.is_verbose:
                # Be quiet unless user asks to be verbose
                options.is_quiet = True

        assert not (
            options.is_quiet and options.is_verbose
        ), "logging cannot be quiet and verbose at the same time"

        if options.is_quiet:
            logging.basicConfig(format="%(message)s", level=logging.WARNING)
        elif options.is_verbose:
            logging.basicConfig(format="%(message)s", level=logging.DEBUG)
        else:
            logging.basicConfig(format="%(message)s", level=logging.INFO)

        if (func := getattr(options, "func", None)) is not None:
            func(options, ifile_list)

        self.options = options
        return True, None

    def run_on_input(self) -> Prev_Procedure_Result:
        runner = self.options.cls(**self.init_kwargs)

        if self.options.text is not None:
            runner.run_on_text(self.options.text)

        file_paths: list[str] = []
        for attr in ("verified_ifiles",):
            if (paths := getattr(self, attr, None)) is not None:
                file_paths.extend(paths)
        if file_paths:
            runner.run_on_file_list(file_paths)

        return True, None

    def run_interact(self) -> Prev_Procedure_Result:
        runner = self.options.cls(**self.init_kwargs)
        return runner.interact()

    def run(self) -> Prev_Procedure_Result:
        if self.options.version:
            return self.show_version()
        elif getattr(self.options, "is_interact", False):
            return self.run_interact()
        elif (
            getattr(self, "verified_ifiles", None) is not None
            or getattr(self.options, "text", None) is not None
        ):
            return self.run_on_input()
        else:
            if (sub_parser := getattr(self, f"{self.options.command}_parser", None)) is not None:
                sub_parser.print_help()
            else:
                self.args_parser.print_help()
            return True, None

    def show_version(self) -> Prev_Procedure_Result:
        print(__version__)
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
