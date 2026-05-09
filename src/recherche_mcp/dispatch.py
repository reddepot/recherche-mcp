"""Matrice dispatch YAML — versionnée Gitea, reload SIGHUP."""

from __future__ import annotations

import signal
import threading
from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import ValidationError

from .models import DispatchEntry, ModelCandidate, SubQuestion


class DispatchMatrix:
    """Singleton chargeur YAML avec reload SIGHUP à chaud (pas de rebuild Docker).

    Thread-safety :
    - `current()` : double-checked locking pour init concurrent.
    - `reset()` et `reload()` acquièrent le lock.
    - RLock (reentrant) car current() acquiert le lock puis appelle __init__
      qui appelle reload() qui acquiert le même lock — Lock standard = deadlock.
    """

    _instance: ClassVar["DispatchMatrix | None"] = None
    _lock: ClassVar[threading.RLock] = threading.RLock()

    def __init__(self, path: Path):
        self.path = path
        self._data: dict = {}
        self.reload()

    def reload(self) -> None:
        """Recharge le YAML. Appelé sur SIGHUP.

        Validation Phase A : un YAML vide ou retournant `None` est tolérant
        et donne `{}`, mais un format inattendu (liste, scalaire) lève
        ValueError pour éviter les AttributeError silencieux en aval.
        """
        with self._lock:
            raw = yaml.safe_load(self.path.read_text(encoding="utf-8"))
            if raw is None:
                raw = {}
            if not isinstance(raw, dict):
                raise ValueError(
                    f"dispatch matrix invalide: attendu dict, reçu {type(raw).__name__}"
                )
            self._data = raw

    def resolve(self, subqs: list[SubQuestion]) -> list[DispatchEntry]:
        """Pour chaque sous-Q, retourne ses 1-3 candidats par priorité."""
        with self._lock:
            entries = []
            for sq in subqs:
                domain_key = sq.domain_hint.value
                cands_raw = self._data.get(domain_key, self._data.get("mixte", []))
                cands_sorted = sorted(cands_raw, key=lambda c: c.get("priority", 99))
                try:
                    cands = [ModelCandidate(**c) for c in cands_sorted][:3]
                except ValidationError as exc:
                    raise RuntimeError(
                        f"Candidat invalide pour domaine {domain_key} : {exc}"
                    ) from exc
                if not cands:
                    raise ValueError(f"Aucun candidat pour domaine {domain_key}")
                entries.append(DispatchEntry(sub_question_id=sq.id, candidates=cands))
            return entries

    def get_candidates(self, domain: str) -> list[dict]:
        """API publique : retourne les candidats bruts pour un domaine."""
        with self._lock:
            cands = self._data.get(domain, self._data.get("mixte", []))
            return sorted(cands, key=lambda c: c.get("priority", 99))

    @classmethod
    def current(cls, path: Path | None = None) -> "DispatchMatrix":
        """Singleton thread-safe via double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    default_path = path or (
                        Path(__file__).parent / "data" / "dispatch_matrix.yaml"
                    )
                    instance = cls(default_path)
                    try:
                        signal.signal(
                            signal.SIGHUP, lambda *_: instance.reload()
                        )
                    except (ValueError, AttributeError):
                        # SIGHUP indispo (Windows, thread non-main, tests)
                        pass
                    cls._instance = instance
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Pour les tests : reset le singleton (thread-safe)."""
        with cls._lock:
            cls._instance = None
