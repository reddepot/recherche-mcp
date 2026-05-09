"""Matrice dispatch YAML — versionnée Gitea, reload SIGHUP."""

from __future__ import annotations

import signal
import threading
from pathlib import Path
from typing import ClassVar

import yaml

from .models import DispatchEntry, ModelCandidate, SubQuestion


class DispatchMatrix:
    """Singleton chargeur YAML avec reload SIGHUP à chaud (pas de rebuild Docker)."""

    _instance: ClassVar["DispatchMatrix | None"] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, path: Path):
        self.path = path
        self._data: dict = {}
        self.reload()

    def reload(self) -> None:
        """Recharge le YAML. Appelé sur SIGHUP."""
        with self._lock:
            self._data = yaml.safe_load(self.path.read_text(encoding="utf-8"))

    def resolve(self, subqs: list[SubQuestion]) -> list[DispatchEntry]:
        """Pour chaque sous-Q, retourne ses 1-3 candidats par priorité."""
        with self._lock:
            entries = []
            for sq in subqs:
                domain_key = sq.domain_hint.value
                cands_raw = self._data.get(domain_key, self._data.get("mixte", []))
                cands_sorted = sorted(cands_raw, key=lambda c: c.get("priority", 99))
                cands = [ModelCandidate(**c) for c in cands_sorted][:3]
                if not cands:
                    raise ValueError(f"Aucun candidat pour domaine {domain_key}")
                entries.append(DispatchEntry(sub_question_id=sq.id, candidates=cands))
            return entries

    @classmethod
    def current(cls, path: Path | None = None) -> "DispatchMatrix":
        """Singleton instance avec SIGHUP handler installé une seule fois."""
        if cls._instance is None:
            default_path = path or (Path(__file__).parent / "data" / "dispatch_matrix.yaml")
            cls._instance = cls(default_path)
            try:
                signal.signal(signal.SIGHUP, lambda *_: cls._instance.reload())
            except (ValueError, AttributeError):
                # SIGHUP indispo (Windows, thread non-main, tests)
                pass
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Pour les tests : reset le singleton."""
        cls._instance = None
