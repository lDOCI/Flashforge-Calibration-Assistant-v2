from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


def _merge_dict(base: dict, update: dict) -> dict:
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge_dict(base[key], value)
        else:
            base[key] = value
    return base


@dataclass
class LanguageDefinition:
    code: str
    name: str
    translations: Dict[str, object]


class LocalizationService:
    """
    Loads translation catalogues from the `languages/` directory and provides
    convenient access to text resources across the UI.
    """

    def __init__(self, languages_dir: Path | str = Path("languages"), default_language: str = "en") -> None:
        self._languages_dir = Path(languages_dir)
        self._default_language = default_language
        self._languages: Dict[str, LanguageDefinition] = {}
        self._current_language: str = default_language
        self._load_languages()

    def _load_languages(self) -> None:
        if not self._languages_dir.exists():
            self._languages_dir.mkdir(parents=True, exist_ok=True)

        for file in self._languages_dir.glob("*.json"):
            try:
                payload = json.loads(file.read_text(encoding="utf-8"))
                code = file.stem
                name = payload.get("_meta", {}).get("name", code.upper())
                translations = {k: v for k, v in payload.items() if k != "_meta"}
                self._languages[code] = LanguageDefinition(code, name, translations)
            except json.JSONDecodeError:
                continue

        if self._default_language not in self._languages and self._languages:
            self._current_language = next(iter(self._languages))

    @property
    def current_language(self) -> str:
        return self._current_language

    def available_languages(self) -> list[tuple[str, str]]:
        return [(lang.code, lang.name) for lang in self._languages.values()]

    def set_language(self, language_code: str) -> bool:
        if language_code not in self._languages:
            return False
        self._current_language = language_code
        return True

    def translate(self, key: str, default: Optional[str] = None) -> str:
        return self._lookup(key, self._current_language, default)

    def translate_from(self, language_code: str, key: str, default: Optional[str] = None) -> str:
        return self._lookup(key, language_code, default)

    def _lookup(self, key: str, language_code: str, default: Optional[str]) -> str:
        parts = key.split(".")
        lang = self._languages.get(language_code)
        if not lang:
            return default or key

        node: object = lang.translations
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                fallback = self._languages.get(self._default_language)
                if fallback and language_code != self._default_language:
                    return self._lookup(key, self._default_language, default)
                return default or key
        return str(node)

