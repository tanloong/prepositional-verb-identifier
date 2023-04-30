#!/usr/bin/env python3
# -*- coding=utf-8 -*-
import logging
import os
from typing import List

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
        print_what: str,
        n_matching_process: int = 3,
    ) -> None:
        self.is_pretokenized = is_pretokenized
        self.is_refresh = is_refresh
        self.is_no_query = is_no_query
        self.is_visualize = is_visualize
        self.print_what = print_what

        self.depparser = DependencyParser(self.is_pretokenized, self.is_refresh)
        self.querier = Querier(n_matching_process)

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
        if ofile is None:
            ofile = f"cmdline_text.{self.print_what}"
        doc_spacy = self.depparser.depparse(text, ifile)
        if self.is_visualize:
            for sent in doc_spacy.sents:
                self.draw_tree(sent, ifile)
        if not self.is_no_query:
            ofile_handler = open(ofile, "w", encoding="utf-8")
            try:
                result = self.querier.match(doc_spacy, self.print_what)
                ofile_handler.write(result)
            except KeyboardInterrupt:
                ofile_handler.close()
                if os.path.exists(ofile):
                    os.remove(ofile)
                return False, "KeyboardInterrupt"
            ofile_handler.close()
        return True, None

    def run_on_ifile(self, ifile: str) -> PREVProcedureResult:
        ofile = ifile.replace(".tokenized", "").replace(".txt", "") + "." + self.print_what
        if not self.is_refresh and os.path.exists(ofile):
            logging.info(f"{ofile} already exists, skipped.")
            return True, None
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
        return True, None
