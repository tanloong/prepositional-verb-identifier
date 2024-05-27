#!/usr/bin/env python3

import logging
import os.path as os_path
import sys
from typing import Callable, List

from .nlp import NLP_Spacy
from .util import Prev_Procedure_Result


class Tokenize_Runner:
    def __init__(
        self,
        is_refresh: bool,
        is_stdout: bool,
        is_pretokenized: bool,
        n_process: int = 3,
    ) -> None:
        self.is_refresh = is_refresh
        self.is_stdout = is_stdout
        self.is_pretokenized = is_pretokenized

    def ensure_spacy_initialized(func: Callable):  # type:ignore
        def wrapper(self, *args, **kwargs):
            if not self.is_spacy_initialized:
                logging.debug("Initializing spaCy...")
                import spacy

                self.nlp_spacy = spacy.load(self.model, exclude=["ner"])
                self.is_spacy_initialized = True

            return func(self, *args, **kwargs)  # type:ignore

        return wrapper

    def run_on_text(self, text: str, ifile="cmdline_text", ofile=None) -> Prev_Procedure_Result:
        doc_spacy = NLP_Spacy.tokenize(
            text, ifile, is_pretokenized=self.is_pretokenized, is_refresh=self.is_refresh
        )
        result: str = (
            "\n".join(" ".join(w.text for w in sent) for sent in doc_spacy.sents if sent.text.strip()) + "\n"
        )
        if not self.is_stdout:
            if ofile is None:
                ofile = "cmdline_text.tok"
                logging.info(f"Done. Results have been written in {ofile}.")
            with open(ofile, "w", encoding="utf-8") as f:
                f.write(result)
        else:
            sys.stdout.write(result)
        return True, None

    def run_on_file(self, ifile: str) -> Prev_Procedure_Result:
        dir_name, file_name = os_path.split(ifile)
        name, _ = os_path.splitext(file_name)
        ofile = os_path.join(dir_name, name + "_tok.txt")

        logging.info(f"Matching against {ifile}...")
        with open(ifile, encoding="utf-8") as f:
            text = f.read()
        return self.run_on_text(text, ifile, ofile)

    def run_on_file_list(self, ifiles: List[str]) -> Prev_Procedure_Result:
        i = 1
        total = len(ifiles)
        for ifile in ifiles:
            logging.info(f"Depparsing {ifile}...({i}/{total})")
            self.run_on_file(ifile)
            i += 1

        logging.info("Done. Results have been saved as *.matched, under the same directory as input files.")
        return True, None

    def interact(self) -> Prev_Procedure_Result:
        import readline

        while True:
            try:
                text = input(">>> ")
            except (KeyboardInterrupt, EOFError):
                logging.warning("\npreV existing...")
                break

            if len(text) == 0:
                logging.warning("Empty input!")
            else:
                self.run_on_text(text)
        return True, None
