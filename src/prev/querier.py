#!/usr/bin/env python3
# -*- coding=utf-8 -*-
from typing import List
from spacy.tokens.span import Span
from spacy.tokens import Doc as Doc_spacy
from spacy.matcher import DependencyMatcher

class Querier:
    def __init__(self):
        # fmt: off
        preps = ["about", "across", "against", "as", "for", "into", "of", "over", "through", "under", "with"]
        # fmt: on
        self.patterns = self.generate_patterns(preps)

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
    def check_passive(self, verb_id: int, sent_spacy: Span) -> bool:
        # https://universaldependencies.org/en/feat/Voice.html#voice-voice
        is_passive = False
        if sent_spacy[verb_id].tag_ == "VBN":
            for child in sent_spacy[verb_id].lefts:
                if child.dep_ == "auxpass":
                    is_passive = True
                    break
        return is_passive

    def parse_matches(self, matches: List[tuple], pattern: List[dict], sent_spacy:Span) -> str:
        # matches: [(match_id, [token_id1, token_id2, token_id3, token_id4]), ...]
        # each token_id corresponds to one pattern dict
        result = ""
        for match in matches:
            _, token_ids = match
            verb_id = token_ids[0]
            if self.check_passive(verb_id, sent_spacy):
                continue
            for i in range(len(token_ids)):
                right_id = pattern[i]["RIGHT_ID"]
                node = sent_spacy[token_ids[i]]
                result += f"{right_id}: {node.text}_{node.lemma_}, "
            result += "\n"
        if result:
            result = f"{sent_spacy.text}\n{result}"
        return result.strip()

    def match_sent(self, sent_spacy:Span, matcher:DependencyMatcher):
        result = ""
        for pattern in self.patterns:
            if matcher.get("preps") is not None:
                matcher.remove("preps")
            matcher.add("preps", [pattern])
            matches = matcher(sent_spacy)
            result += self.parse_matches(matches, pattern, sent_spacy)
        return result

    def match(self, doc_spacy:Doc_spacy, print_what:str):
        assert print_what in ("matched", "unmatched"), f"Unexpected print_what: {print_what}"
        matcher = DependencyMatcher(doc_spacy.vocab)
        result = ""
        for sent_spacy in doc_spacy.sents:
            result_per_sent = self.match_sent(sent_spacy, matcher)
            if print_what == "matched" and result_per_sent:
                result += result_per_sent + "\n\n"
            elif print_what == "unmatched" and not result_per_sent:
                result += sent_spacy.text + "\n"
        return result
