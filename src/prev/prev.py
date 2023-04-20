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
    ) -> None:
        self.is_pretokenized = is_pretokenized
        self.is_refresh = is_refresh
        self.is_no_query = is_no_query
        self.is_visualize = is_visualize
        self.print_what = print_what

        self.depparser = DependencyParser(self.is_pretokenized, self.is_refresh)
        self.querier = Querier()

        # fmt: off
        preps = ["about", "across", "against", "as", "for", "into", "of", "over", "through", "under", "with"]
        # fmt: on
        self.patterns = self.generate_patterns(preps)

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

    def generate_patterns(self, preps: List[str]) -> List[List[dict]]:  # {{{
        patterns = []
        patterns.append(
            [
                {
                    "RIGHT_ID": "verb",
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB"}},
                },
                {
                    "LEFT_ID": "verb",
                    "REL_OP": ">",  # A is the immediate head of B.
                    "RIGHT_ID": "adverbial",
                    "RIGHT_ATTRS": {
                        "POS": {"IN": ["ADP", "ADV"]},
                        "DEP": {"IN": ["prt", "advmod"]},
                    },
                    # POS=ADP and DEP=prt, e.g., His face lit up with pleasure. (Francis et al., 1996: 347)
                    # POS=ADV and DEP=advmod, e.g., The long-range goal must be to do away[advmod] with nuclear weapons altogether. (Francis et al., 1996: 144)
                },
                {
                    "LEFT_ID": "adverbial",
                    # B is a right immediate sibling of A, i.e., A and B have the same parent and A.i == B.i - 1.
                    "REL_OP": "$+",
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"ORTH": {"IN": preps}, "DEP": "prep"},
                },
            ]
        )
        patterns.append(
            [
                {
                    "RIGHT_ID": "verb",
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB"}},
                },
                {
                    "LEFT_ID": "verb",
                    "REL_OP": ".",
                    "RIGHT_ID": "adverbial",
                    "RIGHT_ATTRS": {
                        "DEP": "advmod",
                    },
                },
                {
                    "LEFT_ID": "adverbial",
                    "REL_OP": "<+",
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"ORTH": {"IN": preps}, "DEP": "prep"},
                },
            ]
        )
        patterns.append(
            [
                {
                    "RIGHT_ID": "verb",
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB"}},
                },
                {
                    "LEFT_ID": "verb",
                    "REL_OP": (
                        ">+"
                    ),  # B is a right immediate child of A, i.e., A > B and A.i == B.i -1
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"ORTH": {"IN": preps}, "DEP": "prep"},
                },
            ]
        )
        patterns.append(
            [
                {
                    "RIGHT_ID": "verb",
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB"}},
                },
                {
                    "LEFT_ID": "verb",
                    # A immediately precedes B, i.e., A.i == B.i - 1, and both are within the same dependency tree.
                    "REL_OP": ".",
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"ORTH": {"IN": preps}, "DEP": "mark"},
                },
                {
                    "LEFT_ID": "prep",
                    # B is a right sibling of A, i.e., A and B have the same parent and A.i < B.i.
                    "REL_OP": "$++",
                    "RIGHT_ID": "to-inf",
                    "RIGHT_ATTRS": {"ORTH": "to"},
                },
            ]
        )
        # Jones and his accomplice posed as police officers to gain entry to the house. (Francis et al., 1996: 208)
        # She got up from her desk and motioned for Wade to follow her. (Francis et al., 1996: 238)
        # They are pressing for the government to implement the electoral promises of job creation and land reform as a first priority. (Francis et al., 1996: 238)
        # All the women will be dying for you to make a mistake. (Francis et al., 1996: 239)
        # He longed for the winter to be over. (Francis et al., 1996: 239)
        # I'll arrange for it to be sent direct to the properly when it is unloaded. (Francis et al., 1996: 239)
        return patterns  # }}}

    def run_on_text(self, text: str, ifile="cmdline_text", ofile=None) -> PREVProcedureResult:
        if ofile is None:
            ofile = f"cmdline_text.{self.print_what}"
        doc_spacy = self.depparser.parse(text, ifile)
        if self.is_visualize:
            for sent in doc_spacy.sents:
                self.draw_tree(sent, ifile)
        if not self.is_no_query:
            ofile_handler = open(ofile, "w", encoding="utf-8")
            try:
                for sent in doc_spacy.sents:
                    results = ""
                    for result in self.querier.match(self.patterns, sent):
                        if result:
                            results += result + "\n"
                    results = results.strip()
                    if self.print_what == "matched" and results:
                        ofile_handler.write(sent.text + "\n" + results + "\n\n")
                    elif self.print_what == "unmatched" and not results:
                        ofile_handler.write(sent.text + "\n")
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
