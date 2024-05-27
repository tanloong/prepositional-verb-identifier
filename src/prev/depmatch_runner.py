#!/usr/bin/env python3

import logging
import os
import os.path as os_path
import sys
from typing import List, Optional

from .nlp import NLP_Spacy
from .querier import Querier
from .util import Prev_Procedure_Result


class Depmatch_Runner:
    def __init__(
        self,
        is_pretokenized: bool,
        is_refresh: bool,
        is_no_query: bool,
        is_visualize: bool,
        is_stdout: bool,
        print_what: str,
        n_process: int = 3,
        pattern_file: Optional[str] = None,
    ) -> None:
        self.is_pretokenized = is_pretokenized
        self.is_refresh = is_refresh
        self.is_no_query = is_no_query
        self.is_visualize = is_visualize
        self.is_stdout = is_stdout
        self.print_what = print_what

        self.querier = Querier(n_process, pattern_file)

    def draw_tree(self, sent_spacy, ifile: str) -> None:
        from spacy import displacy

        trees_dir = ifile.replace(".tokenized", "").replace(".txt", "") + "_trees"
        svg_file = (
            trees_dir
            + os_path.sep
            + "-".join([w.text for w in sent_spacy if (w.is_alpha or w.is_digit)])[:100]
            + ".svg"
        )
        if os_path.exists(svg_file) and not self.is_refresh:
            logging.info(f"{svg_file} already exists. Visualizing skipped.")
        else:
            logging.info(f"Visualizing: {sent_spacy.text}")
            svg = displacy.render(sent_spacy)
            if not os_path.exists(trees_dir):
                os.makedirs(trees_dir)
            with open(svg_file, "w", encoding="utf-8") as f:
                f.write(svg)

    def run_on_text(self, text: str, ifile="cmdline_text", ofile=None) -> Prev_Procedure_Result:
        doc_spacy = NLP_Spacy.depparse(
            text, ifile, is_pretokenized=self.is_pretokenized, is_refresh=self.is_refresh
        )
        if self.is_visualize:
            for sent in doc_spacy.sents:
                self.draw_tree(sent, ifile)
        if not self.is_no_query:
            try:
                result = self.querier.match(doc_spacy, self.print_what)
            except KeyboardInterrupt:
                return False, "KeyboardInterrupt"

            if not self.is_stdout:
                if ofile is None:
                    ofile = f"cmdline_text.{self.print_what}"
                    logging.info(f"Done. Results have been written in {ofile}.")
                with open(ofile, "w", encoding="utf-8") as f:
                    f.write(result)
            else:
                sys.stdout.write(result)
        return True, None

    def run_on_file(self, ifile: str) -> Prev_Procedure_Result:
        dir_name, file_name = os_path.split(ifile)
        name, _ = os_path.splitext(file_name)
        ofile = os_path.join(dir_name, name + f"_{self.print_what}.txt")

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
