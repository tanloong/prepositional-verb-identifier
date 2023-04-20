#!/usr/bin/env python3
# -*- coding=utf-8 -*-
import logging
import json
from typing import Optional
import os
from spacy.tokens import Doc as Doc_spacy
from stanza.models.common.doc import Document as Doc_stanza


class DependencyParser:
    def __init__(self, is_pretokenized: bool = False, is_refresh: bool = False):
        self.is_pretokenized = is_pretokenized
        self.is_refresh = is_refresh
        self.is_stanza_initialized = False
        self.is_spacy_initialized = False

    def ensure_stanza_initialized(self):
        if not self.is_stanza_initialized:
            logging.info("Initializing Stanza...")
            import stanza

            self.nlp_stanza = stanza.Pipeline(
                lang="en",
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

            self.nlp_spacy = spacy.load(
                "en_core_web_sm", exclude=["ner", "attribute_ruler", "tagger"]
            )
            self.is_spacy_initialized = True

    def postag(self, text: str, ifile_prefix: str):
        ofile_postagged = ifile_prefix + "_pos-tagged.json"
        if os.path.exists(ofile_postagged) and not self.is_refresh:
            logging.info(f"{ofile_postagged} already exists. POS tagging skipped.")
            with open(ofile_postagged, "r") as f:
                doc_stanza = Doc_stanza(json.load(f))
        else:
            logging.info(f"POS tagging...")
            self.ensure_stanza_initialized()
            doc_stanza = self.nlp_stanza(text)
            logging.info(f"Saving POS tagged file in {ofile_postagged}.")
            with open(ofile_postagged, "w") as f:
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
            spaces=[
                w.end_char != n.start_char for w, n in zip(words_stanza[:-1], words_stanza[1:])
            ]
            + [False],
            sent_starts=is_sent_start,  # type:ignore
        )
        return doc_spacy

    def _parse(self, text: str, ifile_prefix: str):
        ofile_depparsed = ifile_prefix + "_dep-parsed.json"
        self.ensure_spacy_initialized()
        if os.path.exists(ofile_depparsed) and not self.is_refresh:
            logging.info(f"{ofile_depparsed} already exists. Dependency parsing skipped.")
            with open(ofile_depparsed, "r") as f:
                doc_spacy = Doc_spacy(self.nlp_spacy.vocab).from_json(json.load(f))
        else:
            doc_stanza = self.postag(text, ifile_prefix)  # type:ignore
            doc_spacy = self.stanza2spacy(doc_stanza)
            logging.info(f"Dependency parsing...")
            doc_spacy = self.nlp_spacy(doc_spacy)
            logging.info(f"Saving parse trees in {ofile_depparsed}.")
            with open(ofile_depparsed, "w") as f:
                f.write(json.dumps(doc_spacy.to_json()))
        return doc_spacy

    def parse(self, text: Optional[str] = None, ifile: Optional[str] = None):
        assert any((text, ifile)), "Neither text nor ifile is valid."
        if ifile is None:
            ifile = "cmdline_text"
        elif text is None:
            with open(ifile, "r", encoding="utf-8") as f:
                text = f.read()
        logging.info(f"Processing {ifile}...")
        ifile_prefix = ifile.split(".")[0]
        doc_spacy = self._parse(text, ifile_prefix)  # type:ignore
        return doc_spacy
