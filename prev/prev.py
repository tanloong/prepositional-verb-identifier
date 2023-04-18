#!/usr/bin/env python3
# -*- coding=utf-8 -*-
import json
import logging
import os
import sys
from typing import List

from spacy import displacy
from spacy.matcher import DependencyMatcher
from spacy.tokens import Doc as Doc_spacy
from spacy.tokens.span import Span
from stanza.models.common.doc import Document as Doc_stanza

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

        # fmt: off
        preps = ["about", "across", "against", "as", "for", "into", "of", "over", "through", "under", "with"]
        # fmt: on
        self.patterns = self.generate_patterns(preps)
        self.is_stanza_initialized = False
        self.is_spacy_initialized = False

    def ensure_stanza_initialized(self):
        if not self.is_stanza_initialized:
            logging.info("Initializing Stanza...")
            import stanza
            self.nlp_stanza = stanza.Pipeline(
                lang="en",
                dir="/home/tan/software/stanza_resources",
                processors="tokenize,pos",
                use_gpu=False,
                tokenize_pretokenized=self.is_pretokenized,
                download_method=None,  # type:ignore
            )
            self.is_stanza_initialized = True

    def ensure_spacy_initialized(self):
        if not self.is_spacy_initialized:
            logging.info("Initializing spaCy...")
            import spacy
            self.nlp_spacy = spacy.load("en_core_web_sm", exclude=["ner", "attribute_ruler", "tagger"])
            self.is_spacy_initialized = True

    def build_doc_stanza(self, text: str, ifile: str):
        json_file = ifile.replace(".tokenized", "").replace(".txt", "") + "_pos-parsed.json"
        if os.path.exists(json_file) and not self.is_refresh:
            logging.info(f"{json_file} already exists. POS tagging skipped.")
            with open(json_file, "r") as f:
                doc_stanza = Doc_stanza(json.load(f))
        else:
            self.ensure_stanza_initialized()
            logging.info(f"POS tagging {ifile}...")
            doc_stanza = self.nlp_stanza(text)
            logging.info(f"Saving POS tagged file in {json_file}.")
            with open(json_file, "w") as f:
                f.write(json.dumps(doc_stanza.to_dict()))  # type:ignore
        return doc_stanza

    def stanza2spacy(self, doc_stanza):
        logging.info("Converting doc_stanza to doc_spacy...")
        words_stanza = list(doc_stanza.iter_words())  # type:ignore
        sent_start_ids = []
        current_id = 0
        for sentence in doc_stanza.sentences:  # type:ignore
            sent_start_ids.append(current_id)
            current_id += len(sentence.words)
        is_sent_start = [False for _ in words_stanza]
        for sent_start_id in sent_start_ids:
            is_sent_start[sent_start_id] = True
        doc_spacy = Doc_spacy(
            self.nlp_spacy.vocab,
            words=[word.text for word in words_stanza],
            pos=[word.pos for word in words_stanza],
            tags=[word.xpos for word in words_stanza],
            spaces=[w.end_char!=n.start_char for w,n in zip(words_stanza[:-1], words_stanza[1:])]+[False],
            sent_starts=is_sent_start,  # type:ignore
        )
        return doc_spacy

    def build_doc_spacy(self, text: str, ifile: str):
        """assign POS tags by doc_stanza to doc_spacy"""
        json_file = ifile.replace(".tokenized", "").replace(".txt", "") + "_dep-parsed.json"
        self.ensure_spacy_initialized()
        if os.path.exists(json_file) and not self.is_refresh:
            logging.info(f"{json_file} already exists. Dependency parsing skipped.")
            with open(json_file, "r") as f:
                doc_spacy = Doc_spacy(self.nlp_spacy.vocab).from_json(json.load(f))
        else:
            doc_stanza = self.build_doc_stanza(text, ifile)
            doc_spacy = self.stanza2spacy(doc_stanza)
            logging.info(f"Dependency parsing {ifile}...")
            doc_spacy = self.nlp_spacy(doc_spacy)
            logging.info(f"Saving parse trees in {json_file}.")
            with open(json_file, "w") as f:
                f.write(json.dumps(doc_spacy.to_json()))
        return doc_spacy

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

    def generate_patterns(self, preps: List[str]) -> List[List[dict]]:# {{{
        patterns = []
        patterns.append(
            [
                {
                    "RIGHT_ID": "verb",
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB[^N]?$"}},
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
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB[^N]?$"}},
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
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB[^N]?$"}},
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
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB[^N]?$"}},
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
        return patterns# }}}

    def match_prev(self, patterns: List[List[dict]], sent_spacy: Span):
        matcher = DependencyMatcher(sent_spacy.vocab)
        match_id = "preps"
        for pattern in patterns:
            if matcher.get(match_id) is not None:
                matcher.remove(match_id)
            matcher.add(match_id, [pattern])
            matches = matcher(sent_spacy)
            yield self.parse_matches(matches, pattern, sent_spacy)

    def parse_matches(self, matches: List[tuple], pattern: List[dict], sent_spacy: Span) -> str:
        result_sent = ""
        # matches: [(<match_id>, [<token_id1>, <token_id2>, <token_id3>, <token_id4>])]
        # each token_id corresponds to one pattern dict
        for match in matches:
            _, token_ids = match
            for i in range(len(token_ids)):
                right_id = pattern[i]["RIGHT_ID"]
                node = sent_spacy[token_ids[i]]
                result_sent += f"{right_id}: {node.text}_{node.lemma_}, "
            result_sent += "\n"
        return result_sent.strip()

    def run_on_text(self, text: str, ifile="cmdline_text", ofile=None) -> PREVProcedureResult:
        if ofile is None:
            ofile = f"cmdline_text.{self.print_what}"
        doc_spacy = self.build_doc_spacy(text, ifile)
        if self.is_visualize:
            for sent in doc_spacy.sents:
                self.draw_tree(sent, ifile)
        if not self.is_no_query:
            ofile_handler = open(ofile, "w", encoding="utf-8")
            try:
                for sent in doc_spacy.sents:
                    results = ""
                    for result in self.match_prev(self.patterns, sent):
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
                sys.exit(1)
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
