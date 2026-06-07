import os
import re
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer
from typing import List, Dict

LABELS = ["STANDARD", "UNUSUAL", "RISKY"]
ID2LABEL = {i: l for i, l in enumerate(LABELS)}

RISK_COLORS = {
    "STANDARD": "green",
    "UNUSUAL": "orange",
    "RISKY": "red",
}

CLASSIFIER_MODEL_DIR = os.path.join(
    os.path.dirname(__file__),
    "../../../ml_training/models/clause_classifier"
)

# Rule-based risky patterns — fallback before model is trained
RISKY_PATTERNS = [
    r"without\s+(?:any\s+)?(?:prior\s+)?notice",
    r"at\s+(?:the\s+)?(?:sole\s+)?discretion\s+of\s+(?:the\s+)?(?:landlord|employer|lender)",
    r"waives?\s+(?:all\s+)?rights",
    r"non[-\s]refundable",
    r"unlimited\s+liability",
    r"बिना\s+(?:किसी\s+)?(?:पूर्व\s+)?सूचना",
    r"सभी\s+अधिकार\s+छोड़",
]

UNUSUAL_PATTERNS = [
    r"\d+\s+years?\s+non[-\s]compete",
    r"perpetual\s+license",
    r"sole\s+and\s+exclusive",
    r"irrevocable",
    r"liquidated\s+damages\s+of\s+(?:₹|Rs\.?)\s?[\d,]+",
]


class ClauseClassifier:
    """
    Classifies individual legal clauses as STANDARD / UNUSUAL / RISKY.
    Uses ONNX model if trained, rule-based fallback otherwise.
    """

    def __init__(self):
        self._session = None
        self._tokenizer = None
        self._model_loaded = False
        self._try_load_model()

    def _try_load_model(self):
        onnx_path = os.path.join(CLASSIFIER_MODEL_DIR, "clause_classifier.onnx")
        if os.path.exists(onnx_path):
            self._session = ort.InferenceSession(onnx_path)
            self._tokenizer = AutoTokenizer.from_pretrained(CLASSIFIER_MODEL_DIR)
            self._model_loaded = True
            print("Clause classifier ONNX model loaded.")
        else:
            print("Clause classifier not found — using rule-based fallback.")

    def classify_clause(self, text: str) -> Dict:
        """
        Classify a single clause.
        Returns: {label, confidence, color, reasoning}
        """
        if self._model_loaded:
            return self._model_classify(text)
        return self._rule_classify(text)

    def classify_document(self, text: str) -> List[Dict]:
        """
        Split document into clauses and classify each one.
        Returns list of classified clauses for the risk heatmap.
        """
        clauses = self._split_into_clauses(text)
        results = []

        for i, clause in enumerate(clauses):
            if len(clause.strip()) < 20:
                continue
            result = self.classify_clause(clause)
            result["clause_index"] = i
            result["clause_text"] = clause[:300]   # truncate for response
            results.append(result)

        return results

    def _split_into_clauses(self, text: str) -> List[str]:
        """Split document text into individual clauses."""
        pattern = r"(?:\n\s*\d+\.\s|\nWHEREAS|\nNOW THEREFORE|\n[A-Z][A-Z\s]{3,}:|\nखण्ड\s+\d+|\nधारा\s+\d+)"
        parts = re.split(pattern, text)
        return [p.strip() for p in parts if p.strip()]

    def _model_classify(self, text: str) -> Dict:
        """ONNX inference classification."""
        encoding = self._tokenizer(
            text,
            max_length=256,
            padding="max_length",
            truncation=True,
            return_tensors="np",
        )

        logits = self._session.run(
            ["logits"],
            {
                "input_ids": encoding["input_ids"],
                "attention_mask": encoding["attention_mask"],
            },
        )[0]

        # Softmax for probabilities
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / exp_logits.sum()

        pred_id = int(np.argmax(probs))
        label = ID2LABEL[pred_id]
        confidence = float(probs[0][pred_id])

        return {
            "label": label,
            "confidence": round(confidence, 3),
            "color": RISK_COLORS[label],
            "probabilities": {
                LABELS[i]: round(float(probs[0][i]), 3)
                for i in range(len(LABELS))
            },
        }

    def _rule_classify(self, text: str) -> Dict:
        """Rule-based fallback classification."""
        text_lower = text.lower()

        for pattern in RISKY_PATTERNS:
            if re.search(pattern, text_lower):
                return {
                    "label": "RISKY",
                    "confidence": 0.85,
                    "color": "red",
                    "probabilities": {"STANDARD": 0.1, "UNUSUAL": 0.05, "RISKY": 0.85},
                }

        for pattern in UNUSUAL_PATTERNS:
            if re.search(pattern, text_lower):
                return {
                    "label": "UNUSUAL",
                    "confidence": 0.75,
                    "color": "orange",
                    "probabilities": {"STANDARD": 0.2, "UNUSUAL": 0.75, "RISKY": 0.05},
                }

        return {
            "label": "STANDARD",
            "confidence": 0.80,
            "color": "green",
            "probabilities": {"STANDARD": 0.80, "UNUSUAL": 0.15, "RISKY": 0.05},
        }


# Singleton
clause_classifier = ClauseClassifier()