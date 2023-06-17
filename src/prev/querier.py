#!/usr/bin/env python3
# -*- coding=utf-8 -*-
import logging
from typing import List, Optional

from spacy.matcher import DependencyMatcher
from spacy.tokens import Doc as Doc_spacy
from spacy.tokens.span import Span


class Querier:
    def __init__(self, n_matching_process: int = 3, custom_pattern_path: Optional[str] = None):
        self.n_matching_process = n_matching_process
        # fmt: off
        preps = ["about", "across", "against", "as", "for", "into", "of", "over", "through", "under", "with"]
        # fmt: on
        self.patterns = self.generate_patterns(preps, custom_pattern_path)
        self.is_use_custom_patterns = False

    # {{{
    def generate_patterns(
        self, preps: List[str], custom_pattern_path: Optional[str] = None
    ) -> List[List[dict]]:
        patterns = [
            [  # {{{
                {
                    "RIGHT_ID": "verb",
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB"}},
                },
                {
                    "LEFT_ID": "verb",
                    "REL_OP": ">+",
                    # B is a right immediate child of A, i.e., A > B and A.i == B.i -1
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"ORTH": {"IN": preps}, "DEP": "prep"},
                },
            ],  # }}}
            [  # {{{
                # 1. POS=ADP and DEP=prt,
                #    e.g., His face lit up with pleasure. (Francis et al., 1996: 347)
                # 2. POS=ADV and DEP=advmod,
                #    e.g., The long-range goal must be to do away[advmod] with nuclear weapons altogether.
                #    (Francis et al., 1996: 144)
                {
                    "RIGHT_ID": "verb",
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB"}},
                },
                {
                    "LEFT_ID": "verb",
                    "REL_OP": ">",
                    # A is the immediate head of B.
                    "RIGHT_ID": "prt-or-advmod",
                    "RIGHT_ATTRS": {
                        "POS": {"IN": ["ADP", "ADV"]},
                        "DEP": {"IN": ["prt", "advmod"]},
                    },
                },
                {
                    "LEFT_ID": "prt-or-advmod",
                    # B is a right immediate sibling of A,
                    # i.e., A and B have the same parent and A.i == B.i - 1.
                    "REL_OP": "$+",
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"ORTH": {"IN": preps}, "DEP": "prep"},
                },
            ],  # }}}
            [  # {{{
                {
                    "RIGHT_ID": "verb",
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB"}},
                },
                {
                    "LEFT_ID": "verb",
                    "REL_OP": ".",
                    "RIGHT_ID": "advmod",
                    "RIGHT_ATTRS": {
                        "DEP": "advmod",
                    },
                },
                {
                    "LEFT_ID": "advmod",
                    "REL_OP": "<+",
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"ORTH": {"IN": preps}, "DEP": "prep"},
                },
            ],  # }}}
            [  # {{{
                # 1. I rummaged in my suitcase for a tie. (Francis et al., 1996: 234)
                {
                    "RIGHT_ID": "verb",
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB"}},
                },
                {
                    "LEFT_ID": "verb",
                    "REL_OP": ">+",
                    "RIGHT_ID": "intervening-prep",
                    "RIGHT_ATTRS": {"DEP": "prep"},
                },
                {
                    "LEFT_ID": "intervening-prep",
                    "REL_OP": "$++",
                    # A is a left sibling of B
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"ORTH": {"IN": preps}, "DEP": "prep"},
                },
            ],  # }}}
            [  # {{{
                # 1. Jones and his accomplice posed as police officers to gain entry to
                #    the house. (Francis et al., 1996: 208)
                # 2. She got up from her desk and motioned for Wade to follow her.
                #    (Francis et al., 1996: 238)
                # 3. They are pressing for the government to implement the electoral
                #    promises of job creation and land reform as a first priority.
                #    (Francis et al., 1996: 238)
                # 4. All the women will be dying for you to make a mistake.
                #    (Francis et al., 1996: 239)
                # 5. He longed for the winter to be over. (Francis et al., 1996: 239)
                # 6. I'll arrange for it to be sent direct to the properly when it is
                #    unloaded. (Francis et al., 1996: 239)
                {
                    "RIGHT_ID": "verb",
                    "RIGHT_ATTRS": {"TAG": {"REGEX": "^VB"}},
                },
                {
                    "LEFT_ID": "verb",
                    # A immediately precedes B,
                    # i.e., A.i == B.i - 1, and both are within the same dependency tree.
                    "REL_OP": ".",
                    "RIGHT_ID": "prep",
                    "RIGHT_ATTRS": {"ORTH": {"IN": preps}, "DEP": "mark"},
                },
                {
                    "LEFT_ID": "prep",
                    # B is a right sibling of A, i.e., A and B have the same parent and A.i < B.i.
                    "REL_OP": "$++",
                    "RIGHT_ID": "infinitive-to",
                    "RIGHT_ATTRS": {"ORTH": "to"},
                },
            ],  # }}}
        ]
        if custom_pattern_path is not None:
            try:
                with open(custom_pattern_path, "r", encoding="utf-8") as f:
                    config = {}
                    exec(f.read(), config)
                if config["patterns"] and isinstance(config["patterns"], list):
                    patterns = config["patterns"]
                    self.is_use_custom_patterns = True
            except FileNotFoundError:
                logging.warning(f"{custom_pattern_path} does not exist. Using default patterns.")
        return patterns

    # }}}

    def check_passive(self, verb_id: int, sent_spacy: Span) -> bool:
        # https://universaldependencies.org/en/feat/Voice.html#voice-voice
        is_passive = False

        if sent_spacy[verb_id].tag_ == "VBN":
            for child in sent_spacy[verb_id].lefts:
                if child.dep_ == "auxpass":
                    is_passive = True
                    break
        return is_passive

    def parse_matches(self, matches: List[tuple], pattern: List[dict], sent_spacy: Span) -> str:
        # matches: [(match_id, [token_id1, token_id2, token_id3, token_id4]), ...]
        # each token_id corresponds to one pattern dict
        result = ""

        for match in matches:
            _, token_ids = match
            verb_id = token_ids[0]

            if not self.is_use_custom_patterns and self.check_passive(verb_id, sent_spacy):
                continue

            for i in range(len(token_ids)):
                right_id = pattern[i]["RIGHT_ID"]
                node = sent_spacy[token_ids[i]]
                result += f"{right_id}: {node.text}_{node.lemma_}, "
            result += "\n"
        return result

    def match_sent(self, sent_spacy: Span):
        result = ""

        for pattern in self.patterns:
            if self.matcher.get("preps") is not None:
                self.matcher.remove("preps")
            self.matcher.add("preps", [pattern])

            matches = self.matcher(sent_spacy)
            result += self.parse_matches(matches, pattern, sent_spacy)

        result = result.strip()
        if self.print_what == "matched" and result:
            result = f"{sent_spacy.text}\n{result}\n\n"
        elif self.print_what == "unmatched" and not result:
            result = f"{sent_spacy.text}\n"

        return result

    def match(self, doc_spacy: Doc_spacy, print_what: str):
        assert print_what in ("matched", "unmatched"), f"Unexpected print_what: {print_what}"

        self.matcher = DependencyMatcher(doc_spacy.vocab)
        self.print_what = print_what

        array_head = doc_spacy._get_array_attrs()
        array = doc_spacy.to_array(array_head)
        sents = [
            sent_spacy.as_doc(array_head=array_head, array=array)
            for sent_spacy in doc_spacy.sents
        ]

        logging.info("Matching...")
        result = "".join(map(self.match_sent, sents))

        return result
