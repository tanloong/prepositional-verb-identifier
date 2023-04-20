#!/usr/bin/env python3
# -*- coding=utf-8 -*-
from typing import List
from spacy.tokens.span import Span
from spacy.matcher import DependencyMatcher

class Querier:
    def __init__(self):
        ...

    def check_passive(self, verb_id: int, sent_spacy: Span) -> bool:
        is_passive = False
        for child in sent_spacy[verb_id].lefts:
            if child.dep_ == "auxpass":
                is_passive = True
                break
        return is_passive

    def parse_matches(self, matches: List[tuple], pattern: List[dict], sent_spacy: Span) -> str:
        result_sent = ""
        # matches: [(<match_id>, [<token_id1>, <token_id2>, <token_id3>, <token_id4>])]
        # each token_id corresponds to one pattern dict
        for match in matches:
            _, token_ids = match
            verb_id = token_ids[0]
            if self.check_passive(verb_id, sent_spacy):
                continue
            for i in range(len(token_ids)):
                right_id = pattern[i]["RIGHT_ID"]
                node = sent_spacy[token_ids[i]]
                result_sent += f"{right_id}: {node.text}_{node.lemma_}, "
            result_sent += "\n"
        return result_sent.strip()

    def match(self, patterns: List[List[dict]], sent_spacy: Span):
        matcher = DependencyMatcher(sent_spacy.vocab)
        match_id = "preps"
        for pattern in patterns:
            if matcher.get(match_id) is not None:
                matcher.remove(match_id)
            matcher.add(match_id, [pattern])
            matches = matcher(sent_spacy)
            yield self.parse_matches(matches, pattern, sent_spacy)
