#!/usr/bin/env python3
# -*- coding=utf-8 -*-
import logging
import os
import sys
from typing import List, Optional

from spacy import displacy
from spacy.tokens.span import Span

from .parser import DependencyParser
from .querier import Querier
from .util import PREVProcedureResult


class PREV:
    def __init__(
        self,
        is_pretokenized: bool,
        is_refresh: bool,
        is_no_query: bool,
        is_visualize: bool,
        is_stdout: bool,
        is_interactive: bool,
        print_what: str,
        n_matching_process: int = 3,
        config_file: Optional[str] = None,
    ) -> None:
        self.is_pretokenized = is_pretokenized
        self.is_refresh = is_refresh
        self.is_no_query = is_no_query
        self.is_visualize = is_visualize
        self.is_stdout = is_stdout
        self.is_interactive = is_interactive
        self.print_what = print_what

        self.depparser = DependencyParser(is_pretokenized=self.is_pretokenized, is_refresh=self.is_refresh)
        self.querier = Querier(n_matching_process, config_file)

    def draw_tree(self, sent_spacy: Span, ifile: str) -> None:
        trees_dir = ifile.replace(".tokenized", "").replace(".txt", "") + "_trees"
        svg_file = (
            trees_dir
            + os.path.sep
            + "-".join([w.text for w in sent_spacy if (w.is_alpha or w.is_digit)])[:100]
            + ".svg"
        )
        if os.path.exists(svg_file) and not self.is_refresh:
            logging.info(f"{svg_file} already exists. Visualizing skipped.")
        else:
            logging.info(f"Visualizing: {sent_spacy.text}")
            svg = displacy.render(sent_spacy)
            if not os.path.exists(trees_dir):
                os.makedirs(trees_dir)
            with open(svg_file, "w", encoding="utf-8") as f:
                f.write(svg)

    def run_on_text(self, text: str, ifile="cmdline_text", ofile=None) -> PREVProcedureResult:
        doc_spacy = self.depparser.depparse(text, ifile)
        if self.is_visualize:
            for sent in doc_spacy.sents:
                self.draw_tree(sent, ifile)
        if not self.is_no_query:
            try:
                result = self.querier.match(doc_spacy, self.print_what)
            except KeyboardInterrupt:
                return False, "KeyboardInterrupt"
            else:
                if not self.is_stdout:
                    if ofile is None:
                        ofile = f"cmdline_text.{self.print_what}"
                        logging.info(f"Done. Results have been written in {ofile}.")
                    with open(ofile, "w", encoding="utf-8") as f:
                        f.write(result)
                else:
                    sys.stdout.write(result)
        return True, None

    def run_on_ifile(self, ifile: str) -> PREVProcedureResult:
        ofile = ifile.replace(".tokenized", "").replace(".txt", "") + "." + self.print_what
        # if not self.is_refresh and os.path.exists(ofile):
        #     logging.info(f"{ofile} already exists, skipped.")
        #     return True, None
        logging.info(f"Matching against {ifile}...")
        with open(ifile, "r", encoding="utf-8") as f:
            text = f.read()
        return self.run_on_text(text, ifile, ofile)

    def run_on_ifiles(self, ifiles: List[str]) -> PREVProcedureResult:
        i = 1
        total = len(ifiles)
        for ifile in ifiles:
            logging.info(f"Depparsing {ifile}...({i}/{total})")
            self.run_on_ifile(ifile)
            i += 1

        logging.info(f"Done. Results have been saved as *.matched, under the same directory as input files.")
        return True, None

    def run_interactive(self) -> PREVProcedureResult:
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
