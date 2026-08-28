"""Species recognition.

An ImageNet classifier runs on the camera frame; the top-k predictions are
folded down into the species roster in species.py. Whichever species collects
the most probability mass wins.

If torch/torchvision are not available the recogniser degrades to a stub so the
rest of the app still runs (you can spawn critters manually with number keys).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .species import IMAGENET_TO_SPECIES, SPECIES

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


@dataclass
class Detection:
    species_key: str
    raw_label: str
    confidence: float

    @property
    def display(self) -> str:
        return SPECIES[self.species_key].display


class StubRecognizer:
    """No model available — always returns nothing, but keeps the app alive."""

    available = False
    name = "stub (no model)"

    def __init__(self, reason: str = "torch/torchvision not installed"):
        self.reason = reason

    def classify(self, frame_bgr: np.ndarray) -> Optional[Detection]:
        return None


class TorchRecognizer:
    """torchvision ImageNet classifier, CUDA when the Jetson exposes it."""

    available = True

    def __init__(self, model_name: str = "mobilenet_v3_large", topk: int = 8):
        import torch
        import torchvision.models as models

        self._torch = torch
        self.topk = topk

        # torchvision >= 0.13 exposes a registry; the enum names (e.g.
        # MobileNet_V3_Large_Weights) do not follow from the model name, so ask
        # the registry rather than trying to reconstruct them.
        if hasattr(models, "get_model_weights"):
            weights = models.get_model_weights(model_name).DEFAULT
            self.model = models.get_model(model_name, weights=weights)
            self.preprocess = weights.transforms()
            self.categories = list(weights.meta.get("categories", []))
        else:  # pragma: no cover - torchvision < 0.13
            factory = getattr(models, model_name, None)
            if factory is None:
                raise ValueError(f"unknown torchvision model: {model_name}")
            self.model = factory(pretrained=True)
            self.preprocess = None
            self.categories = []

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.eval().to(self.device)
        if self.device.type == "cuda":
            self.model = self.model.half()
        self.name = f"{model_name} @ {self.device.type}"

    def classify(self, frame_bgr: np.ndarray) -> Optional[Detection]:
        torch = self._torch
        if cv2 is None:
            return None

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1)
        if self.preprocess is not None:
            batch = self.preprocess(tensor).unsqueeze(0)
        else:  # pragma: no cover
            batch = (
                torch.nn.functional.interpolate(
                    tensor.unsqueeze(0).float() / 255.0, size=(224, 224), mode="bilinear"
                )
                - torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
            ) / torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)

        batch = batch.to(self.device)
        if self.device.type == "cuda":
            batch = batch.half()

        with torch.no_grad():
            logits = self.model(batch)
            probs = torch.softmax(logits.float(), dim=1)[0]

        scores, indices = torch.topk(probs, self.topk)
        scores = scores.cpu().numpy()
        indices = indices.cpu().numpy()

        # fold ImageNet classes into species buckets
        totals: dict[str, float] = {}
        best_label_for: dict[str, tuple[str, float]] = {}
        for score, idx in zip(scores, indices):
            key = IMAGENET_TO_SPECIES.get(int(idx))
            if key is None:
                continue
            totals[key] = totals.get(key, 0.0) + float(score)
            label = self.categories[int(idx)] if self.categories else f"class {int(idx)}"
            if key not in best_label_for or score > best_label_for[key][1]:
                best_label_for[key] = (label, float(score))

        if not totals:
            return None

        winner = max(totals, key=totals.get)
        label = best_label_for[winner][0]
        return Detection(species_key=winner, raw_label=label, confidence=min(totals[winner], 1.0))


def load_recognizer(model_name: str):
    try:
        return TorchRecognizer(model_name)
    except Exception as exc:
        return StubRecognizer(reason=str(exc))


class RecognitionWorker:
    """Runs inference off the render thread and tracks a confidence streak.

    A capture fires only after `streak` consecutive confident reads of the same
    species, which stops a single lucky frame from populating the sanctuary.
    """

    def __init__(self, recognizer, threshold: float, streak: int):
        self.recognizer = recognizer
        self.threshold = threshold
        self.streak_needed = max(1, streak)

        self.latest: Optional[Detection] = None
        self.streak_species: Optional[str] = None
        self.streak_count = 0

        self._lock = threading.Lock()
        self._busy = False
        self._pending_capture: Optional[tuple[Detection, np.ndarray]] = None

    @property
    def busy(self) -> bool:
        with self._lock:
            return self._busy

    def submit(self, frame_bgr: np.ndarray) -> None:
        """Kick off inference for one frame if the worker is idle."""
        with self._lock:
            if self._busy:
                return
            self._busy = True
        threading.Thread(target=self._run, args=(frame_bgr,), daemon=True).start()

    def _run(self, frame_bgr: np.ndarray) -> None:
        try:
            det = self.recognizer.classify(frame_bgr)
        except Exception:
            det = None

        with self._lock:
            self.latest = det
            if det is not None and det.confidence >= self.threshold:
                if det.species_key == self.streak_species:
                    self.streak_count += 1
                else:
                    self.streak_species = det.species_key
                    self.streak_count = 1
                if self.streak_count >= self.streak_needed:
                    self._pending_capture = (det, frame_bgr)
                    self.streak_count = 0
                    self.streak_species = None
            else:
                self.streak_count = max(0, self.streak_count - 1)
                if self.streak_count == 0:
                    self.streak_species = None
            self._busy = False

    def take_capture(self) -> Optional[tuple[Detection, np.ndarray]]:
        with self._lock:
            capture, self._pending_capture = self._pending_capture, None
            return capture

    def progress(self) -> float:
        with self._lock:
            return self.streak_count / self.streak_needed

    def reset_streak(self) -> None:
        with self._lock:
            self.streak_count = 0
            self.streak_species = None
            self._pending_capture = None
