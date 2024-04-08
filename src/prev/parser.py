#!/usr/bin/env python3
import json
import logging
import os
from typing import Callable, Optional

from spacy.tokens import Doc as Doc_spacy


class DependencyParser:
    def __init__(
        self,
        model: str = "en_core_web_trf",
        is_pretokenized: bool = False,
        is_refresh: bool = False,
    ):
        self.model = model
        self.is_pretokenized = is_pretokenized
        self.is_refresh = is_refresh
        self.is_stanza_initialized = False
        self.is_spacy_initialized = False

    def ensure_spacy_initialized(func: Callable):  # type:ignore
        def wrapper(self, *args, **kwargs):
            if not self.is_spacy_initialized:
                logging.info("Initializing spaCy...")
                import spacy

                self.nlp_spacy = spacy.load(self.model, exclude=["ner"])
                self.is_spacy_initialized = True

            return func(self, *args, **kwargs)  # type:ignore

        return wrapper

    def _json2spacy(self, json_path: str) -> Doc_spacy:
        with open(json_path, encoding="utf-8") as f:
            doc_spacy = Doc_spacy(self.nlp_spacy.vocab).from_json(  # type:ignore
                json.load(f)
            )
        return doc_spacy

    def _spacy2json(self, doc_spacy: Doc_spacy, json_path: str):
        with open(json_path, "w") as f:
            f.write(json.dumps(doc_spacy.to_json()))

    @ensure_spacy_initialized
    def _depparse(self, text: str, ifile_prefix: str):
        ofile_depparsed = ifile_prefix + "_dep-parsed.json"
        if os.path.exists(ofile_depparsed) and not self.is_refresh:
            logging.info(f"{ofile_depparsed} already exists. Dependency parsing skipped.")

            doc_spacy = self._json2spacy(ofile_depparsed)
        else:
            logging.info("Dependency parsing...")
            doc_spacy = self.nlp_spacy(text)  # type:ignore

            logging.info(f"Saving parse trees in {ofile_depparsed}.")
            self._spacy2json(doc_spacy, ofile_depparsed)
        return doc_spacy

    def depparse(self, text: Optional[str] = None, ifile: Optional[str] = None):
        assert any((text, ifile)), "Neither text nor ifile is valid."
        if ifile is None:
            ifile = "cmdline_text"
        elif text is None:
            with open(ifile, encoding="utf-8") as f:
                text = f.read()

        logging.info(f"Processing {ifile}...")

        ifile_prefix = os.path.splitext(ifile)[0]
        doc_spacy = self._depparse(text, ifile_prefix)  # type:ignore
        return doc_spacy
