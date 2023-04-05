#!/usr/bin/env python3
# -*- coding=utf-8 -*-
import os
import pickle
from typing import List

import spacy
from spacy import displacy
from spacy.matcher import DependencyMatcher
from spacy.tokens import Doc
from spacy.tokens.span import Span
import stanza

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

        preps = [
            "about",
            "across",
            "against",
            "as",
            "for",
            "into",
            "of",
            "over",
            "through",
            "under",
            "with",
        ]
        self.patterns = self.generate_patterns(preps)
        self.nlp_stanza = stanza.Pipeline(
            lang="en",
            dir="/home/tan/software/stanza_resources",
            processors="tokenize,pos",
            tokenize_pretokenized=self.is_pretokenized,
            download_method=None,  # type:ignore
        )
        self.nlp_spacy = spacy.load("en_core_web_sm")

    def build_doc_stanza(self, text: str, ifile: str):
        pkl_file = ifile.replace(".tokenized", "").replace(".txt", "") + "_pos-parsed.pkl"
        if not self.is_refresh and os.path.exists(pkl_file):
            print(f"{pkl_file} already exists. POS tagging skipped.")
            with open(pkl_file, "rb") as f:
                doc_stanza = pickle.load(f)
        else:
            print(f"POS tagging {ifile}...")
            doc_stanza = self.nlp_stanza(text)
            with open(pkl_file, "wb") as f:
                pickle.dump(doc_stanza, f)
            print(f"POS tagged file saved in {pkl_file}.")
        return doc_stanza

    def build_doc_spacy(self, text: str, ifile: str):
        """assign POS tags by doc_stanza to doc_spacy"""
        pkl_file = ifile.replace(".tokenized", "").replace(".txt", "") + "_dep-parsed.pkl"
        if not self.is_refresh and os.path.exists(pkl_file):
            print(f"{pkl_file} already exists. Dependency parsing skipped.")
            with open(pkl_file, "rb") as f:
                doc_spacy = pickle.load(f)
        else:
            print(f"Dependency parsing {ifile}...")
            doc_stanza = self.build_doc_stanza(text, ifile)
            words_stanza = list(doc_stanza.iter_words())  # type:ignore
            sent_start_ids = []
            current_id = 0
            for sentence in doc_stanza.sentences:  # type:ignore
                sent_start_ids.append(current_id)
                current_id += len(sentence.words)
            is_sent_start = [False for _ in words_stanza]
            for sent_start_id in sent_start_ids:
                is_sent_start[sent_start_id] = True
            doc_spacy = Doc(
                self.nlp_spacy.vocab,
                words=[word.text for word in words_stanza],
                sent_starts=is_sent_start,  # type:ignore
            )
            for i, token in enumerate(doc_spacy):
                token.pos_ = words_stanza[i].pos
                token.tag_ = words_stanza[i].xpos
            doc_spacy = self.nlp_spacy(doc_spacy)
            with open(pkl_file, "wb") as f:
                pickle.dump(doc_spacy, f)
            print(f"Dependency parsed result saved in {pkl_file}.")
        return doc_spacy

    def draw_tree(self, sent_spacy: Span, ifile: str) -> None:
        print(f"Visualizing: {sent_spacy.text}")
        trees_dir = ifile.replace(".txt.tokenized", "") + "_trees"
        svg_file = (
            trees_dir
            + os.path.sep
            + "-".join([w.text for w in sent_spacy if (w.is_alpha or w.is_digit)])[:100]
            + ".svg"
        )
        if not self.is_refresh and os.path.exists(svg_file):
            print(f"{svg_file} already exists. Visualizing skipped.")
        else:
            svg = displacy.render(sent_spacy)
            if not os.path.exists(trees_dir):
                os.mkdir(trees_dir)
            with open(svg_file, "w", encoding="utf-8") as f:
                f.write(svg)

    def generate_patterns(self, preps: List[str]) -> List[List[dict]]:
        patterns = []
        for prep in preps:
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
                        # POS=ADP and DEP=prt, e.g., His face lit up with pleasure. (Hunston et al., 1996: 347)
                        # POS=ADV and DEP=advmod, e.g., The long-range goal must be to do away[advmod] with nuclear weapons altogether. (Hunston et al., 1996: 144)
                    },
                    {
                        "LEFT_ID": "adverbial",
                        # B is a right immediate sibling of A, i.e., A and B have the same parent and A.i == B.i - 1.
                        "REL_OP": "$+",
                        "RIGHT_ID": "prep",
                        "RIGHT_ATTRS": {"ORTH": prep, "DEP": "prep"},
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
                        "RIGHT_ATTRS": {"ORTH": prep, "DEP": "prep"},
                    },
                ]
            )
            # patterns.append(
            #    [
            #        {
            #            "RIGHT_ID": "verb",
            #            "RIGHT_ATTRS": {"TAG": {"REGEX":"^VB[^N]?$"}},
            #        },
            #        {
            #            "LEFT_ID": "verb",
            #            "REL_OP": ">+",
            #            "RIGHT_ID": "adjectival_complement",
            #            "RIGHT_ATTRS": {"DEP": "acomp"},
            #        },
            #        {
            #            "LEFT_ID": "adjectival_complement",
            #            "REL_OP": ">+",
            #            "RIGHT_ID": "prep",
            #            "RIGHT_ATTRS": {"ORTH": prep, "DEP": "prep"},
            #        },
            #    ]
            # )
            # He felt good about the show. (Hunston et al., 1996: 193)
            # Obviously one should feel depressed about being 60. (Hunston et al., 1996: 193)
            # NOTE: This should be excluded, it is not an instance of "verb prep noun"
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
                        "RIGHT_ATTRS": {"ORTH": prep, "DEP": "mark"},
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
            # Jones and his accomplice posed as police officers to gain entry to the house. (Hunston et al., 1996: 208)
            # She got up from her desk and motioned for Wade to follow her. (Hunston et al., 1996: 238)
            # They are pressing for the government to implement the electoral promises of job creation and land reform as a first priority. (Hunston et al., 1996: 238)
            # All the women will be dying for you to make a mistake. (Hunston et al., 1996: 239)
            # He longed for the winter to be over. (Hunston et al., 1996: 239)
            # I'll arrange for it to be sent direct to the properly when it is unloaded. (Hunston et al., 1996: 239)
        return patterns

    def match_verb_prep(self, patterns: List[List[dict]], sent_spacy: Span):
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
            # verb_id = token_ids[0]
            result_sent += (
                ", ".join(
                    pattern[i]["RIGHT_ID"] + ": " + sent_spacy[token_ids[i]].text
                    for i in range(len(token_ids))
                )
                + "\n"
            )
        return result_sent.strip()

    def run_on_text(self, text: str, ifile="cmdline_text") -> PREVProcedureResult:
        doc_spacy = self.build_doc_spacy(text, ifile)
        # matched_doc = []
        # unmatched_doc = []
        for sent in doc_spacy.sents:
            if self.is_visualize:
                self.draw_tree(sent, ifile)
            results_sent = ""
            if not self.is_no_query:
                for result_sent in self.match_verb_prep(self.patterns, sent):
                    if result_sent.strip():
                        results_sent += result_sent + "\n"
                results_sent = results_sent.strip()
                if self.print_what == "matched" and results_sent:
                    print(sent.text + "\n" + results_sent)
                    # matched_doc.append(sent.text + "\n" + results_sent)
                elif self.print_what == "unmatched" and not results_sent:
                    print(sent.text)
                    # unmatched_doc.append(sent.text)
        # if self.print_what == "matched":
        # print("\n\n".join(matched_doc))
        # else:
        # print("\n".join(unmatched_doc))
        return True, None

    def run_on_ifile(self, ifile: str) -> PREVProcedureResult:
        with open(ifile, "r", encoding="utf-8") as f:
            text = f.read()
        return self.run_on_text(text, ifile)

    def run_on_ifiles(self, ifiles: List[str]) -> PREVProcedureResult:
        i = 1
        total = len(ifiles)
        for ifile in ifiles:
            print(f"Depparsing {ifile}...({i}/{total})")
            self.run_on_ifile(ifile)
            i += 1
        return True, None
