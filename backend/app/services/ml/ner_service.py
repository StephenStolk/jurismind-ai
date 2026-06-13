# import numpy as np
# import onnxruntime as ort
# from transformers import AutoTokenizer
# from typing import List, Dict
# import os

# from app.core.config import settings

# LABELS = [
#     "O",
#     "B-PARTY", "I-PARTY",
#     "B-DATE", "I-DATE",
#     "B-AMOUNT", "I-AMOUNT",
#     "B-LOCATION", "I-LOCATION",
#     "B-CLAUSE_REF", "I-CLAUSE_REF",
#     "B-DURATION", "I-DURATION",
#     "B-PENALTY", "I-PENALTY",
# ]
# ID2LABEL = {i: l for i, l in enumerate(LABELS)}

# NER_MODEL_DIR = os.path.join(
#     os.path.dirname(__file__),
#     "../../../ml_training/models/ner"
# )


# class NERService:
#     """
#     Runs NER inference using ONNX model.
#     Falls back to a rule-based extractor if model not trained yet.
#     """

#     def __init__(self):
#         self._session = None
#         self._tokenizer = None
#         self._model_loaded = False
#         self._try_load_model()

#     def _try_load_model(self):
#         onnx_path = os.path.join(NER_MODEL_DIR, "ner_model.onnx")
#         if os.path.exists(onnx_path):
#             self._session = ort.InferenceSession(onnx_path)
#             self._tokenizer = AutoTokenizer.from_pretrained(NER_MODEL_DIR)
#             self._model_loaded = True
#             print("NER ONNX model loaded.")
#         else:
#             print("NER model not found — using rule-based fallback.")

#     def extract_entities(self, text: str) -> List[Dict]:
#         """
#         Extract named entities from legal text.
#         Returns list of {text, label, start, end} dicts.
#         """
#         if self._model_loaded:
#             return self._model_inference(text)
#         return self._rule_based_fallback(text)

#     def _model_inference(self, text: str) -> List[Dict]:
#         """ONNX inference path."""
#         encoding = self._tokenizer(
#             text,
#             return_tensors="np",
#             max_length=256,
#             truncation=True,
#             padding="max_length",
#             return_offsets_mapping=True,
#         )

#         input_ids = encoding["input_ids"]
#         attention_mask = encoding["attention_mask"]
#         offset_mapping = encoding["offset_mapping"][0]

#         logits = self._session.run(
#             ["logits"],
#             {"input_ids": input_ids, "attention_mask": attention_mask},
#         )[0]

#         predictions = np.argmax(logits, axis=-1)[0]
#         entities = []
#         current_entity = None

#         for idx, (pred_id, offset) in enumerate(zip(predictions, offset_mapping)):
#             if offset[0] == 0 and offset[1] == 0:
#                 continue   # skip special tokens

#             label = ID2LABEL.get(pred_id, "O")

#             if label.startswith("B-"):
#                 if current_entity:
#                     entities.append(current_entity)
#                 current_entity = {
#                     "text": text[offset[0]:offset[1]],
#                     "label": label[2:],
#                     "start": int(offset[0]),
#                     "end": int(offset[1]),
#                 }
#             elif label.startswith("I-") and current_entity:
#                 current_entity["text"] += text[offset[0]:offset[1]]
#                 current_entity["end"] = int(offset[1])
#             else:
#                 if current_entity:
#                     entities.append(current_entity)
#                     current_entity = None

#         if current_entity:
#             entities.append(current_entity)

#         return entities

#     def _rule_based_fallback(self, text: str) -> List[Dict]:
#         """
#         Rule-based NER fallback — used before model is trained.
#         Good enough for testing the pipeline.
#         """
#         import re
#         entities = []

#         patterns = {
#             "AMOUNT": r"₹\s?[\d,]+(?:\.\d+)?(?:\s?(?:lakh|crore|thousand))?|Rs\.?\s?[\d,]+",
#             "DATE": r"\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
#             "DURATION": r"\d+\s+(?:months?|years?|days?|weeks?)|(?:eleven|twelve|six)\s+months?",
#             "CLAUSE_REF": r"[Cc]lause\s+\d+(?:\.\d+)?|[Ss]ection\s+\d+|धारा\s+\d+|खण्ड\s+\d+",
#         }

#         for label, pattern in patterns.items():
#             for match in re.finditer(pattern, text):
#                 entities.append({
#                     "text": match.group(),
#                     "label": label,
#                     "start": match.start(),
#                     "end": match.end(),
#                 })

#         return sorted(entities, key=lambda x: x["start"])


# # Singleton
# ner_service = NERService()












# import spacy
# from typing import List, Dict
# import re

# # Colour coding for frontend heatmap
# ENTITY_COLORS: Dict[str, str] = {
#     "COURT":       "#6366f1",   # indigo
#     "PETITIONER":  "#2dd4bf",   # teal
#     "RESPONDENT":  "#f87171",   # red
#     "JUDGE":       "#a78bfa",   # purple
#     "LAWYER":      "#60a5fa",   # blue
#     "DATE":        "#fbbf24",   # amber
#     "CASE_NUMBER": "#34d399",   # green
#     "GPE":         "#fb923c",   # orange
#     "STATUTE":     "#e879f9",   # pink
#     "PROVISION":   "#f472b6",   # rose
#     "PRECEDENT":   "#94a3b8",   # slate
#     "WITNESS":     "#a3e635",   # lime
#     "ORG":         "#38bdf8",   # sky
#     "PERSON":      "#2dd4bf",   # teal fallback
# }

# LABEL_MAP: Dict[str, str] = {
#     "PETITIONER":  "PARTY",
#     "RESPONDENT":  "PARTY",
#     "JUDGE":       "PARTY",
#     "LAWYER":      "PARTY",
#     "WITNESS":     "PARTY",
#     "DATE":        "DATE",
#     "CASE_NUMBER": "CLAUSE_REF",
#     "PROVISION":   "CLAUSE_REF",
#     "STATUTE":     "CLAUSE_REF",
#     "COURT":       "LOCATION",
#     "GPE":         "LOCATION",
#     "PRECEDENT":   "CLAUSE_REF",
#     "ORG":         "PARTY",
# }


# class NERService:
#     """
#     Named Entity Recognition using OpenNyAI's en_legal_ner_trf model.
#     Production-grade model trained on Indian Supreme Court judgements.
#     Falls back to rule-based extraction if model unavailable.
#     """

#     def __init__(self):
#         self._nlp = None
#         self._model_loaded = False
#         self._try_load_model()

#     def _try_load_model(self):
#         try:
#             # Disable components we don't need — faster inference
#             self._nlp = spacy.load(
#                 "en_legal_ner_trf",
#                 exclude=["tagger", "parser", "lemmatizer"]
#             )
#             self._model_loaded = True
#             print("✓ OpenNyAI legal NER model loaded.")
#         except OSError:
#             print("⚠ OpenNyAI NER model not found — using rule-based fallback.")
#             print("  Run: pip install https://huggingface.co/opennyaiorg/en_legal_ner_trf/resolve/main/en_legal_ner_trf-any-py3-none-any.whl")

#     def extract_entities(self, text: str) -> List[Dict]:
#         """
#         Extract named entities from legal text.

#         Returns list of:
#         {
#           text: str,
#           label: str,          # OpenNyAI label e.g. PETITIONER
#           mapped_label: str,   # your schema label e.g. PARTY
#           start: int,
#           end: int,
#           color: str,          # hex for frontend
#         }
#         """
#         if self._model_loaded:
#             return self._spacy_extract(text)
#         return self._rule_based_fallback(text)

#     def _spacy_extract(self, text: str) -> List[Dict]:
#         """
#         Run OpenNyAI model inference.
#         Splits long text into chunks to stay within model's max length.
#         """
#         MAX_CHARS = 100_000   # spaCy transformer limit

#         # Process in chunks
#         chunks = self._chunk_text(text, MAX_CHARS)
#         all_entities = []
#         offset = 0

#         for chunk in chunks:
#             doc = self._nlp(chunk)
#             for ent in doc.ents:
#                 # Skip very short or noisy entities
#                 if len(ent.text.strip()) < 2:
#                     continue

#                 all_entities.append({
#                     "text":         ent.text.strip(),
#                     "label":        ent.label_,
#                     "mapped_label": LABEL_MAP.get(ent.label_, ent.label_),
#                     "start":        ent.start_char + offset,
#                     "end":          ent.end_char + offset,
#                     "color":        ENTITY_COLORS.get(ent.label_, "#8892a4"),
#                 })
#             offset += len(chunk)

#         # Deduplicate — same text + label
#         seen = set()
#         deduped = []
#         for ent in all_entities:
#             key = (ent["text"].lower(), ent["label"])
#             if key not in seen:
#                 seen.add(key)
#                 deduped.append(ent)

#         return deduped

#     def _chunk_text(self, text: str, max_chars: int) -> List[str]:
#         """Split on paragraph boundaries to preserve context."""
#         if len(text) <= max_chars:
#             return [text]

#         chunks = []
#         paragraphs = text.split("\n\n")
#         current = ""

#         for para in paragraphs:
#             if len(current) + len(para) > max_chars:
#                 if current:
#                     chunks.append(current)
#                 current = para
#             else:
#                 current += "\n\n" + para if current else para

#         if current:
#             chunks.append(current)

#         return chunks

#     def get_entity_summary(self, entities: List[Dict]) -> Dict:
#         """
#         Group entities by label for the frontend summary panel.
#         Returns: { "PARTY": ["Ramesh Kumar", "ABC Ltd"], "DATE": [...], ... }
#         """
#         summary: Dict[str, List[str]] = {}
#         for ent in entities:
#             label = ent["label"]
#             if label not in summary:
#                 summary[label] = []
#             if ent["text"] not in summary[label]:
#                 summary[label].append(ent["text"])
#         return summary

#     def _rule_based_fallback(self, text: str) -> List[Dict]:
#         """Regex fallback when model isn't installed."""
#         entities = []
#         patterns = {
#             "DATE":        r"\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
#             "PROVISION":   r"[Ss]ection\s+\d+(?:\([a-z]\))?|[Aa]rticle\s+\d+|धारा\s+\d+",
#             "CASE_NUMBER": r"[A-Z]+\s+(?:No|Petition|Appeal)\.?\s+\d+(?:/\d+)?",
#             "GPE":         r"\b(?:Delhi|Mumbai|Chennai|Kolkata|Bangalore|Hyderabad|Pune|Ahmedabad)\b",
#         }
#         for label, pattern in patterns.items():
#             for match in re.finditer(pattern, text):
#                 entities.append({
#                     "text":         match.group().strip(),
#                     "label":        label,
#                     "mapped_label": LABEL_MAP.get(label, label),
#                     "start":        match.start(),
#                     "end":          match.end(),
#                     "color":        ENTITY_COLORS.get(label, "#8892a4"),
#                 })
#         return sorted(entities, key=lambda x: x["start"])


# ner_service = NERService()








import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class NERService:
    def __init__(self):
        # The exact Hugging Face model URL
        self.api_url = "https://api-inference.huggingface.co/models/opennyaiorg/en_legal_ner_trf"
        self.headers = {"Authorization": f"Bearer {settings.HF_TOKEN}"}

    async def extract_entities(self, text: str) -> list:
        """Sends text to Hugging Face API to extract legal entities."""
        if not text:
            return []

        payload = {
            "inputs": text,
            "options": {"wait_for_model": True} # Wakes up the HF model if it's sleeping
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, headers=self.headers, json=payload)
                
                if response.status_code != 200:
                    logger.error(f"Hugging Face API Error: {response.text}")
                    return []
                    
                # Hugging Face returns a list of dictionaries with word, entity_group (label), etc.
                results = response.json()
                
                # Format to match your existing frontend schema
                return [
                    {
                        "text": item.get("word"),
                        "label": item.get("entity_group", "OTHER")
                    }
                    for item in results if isinstance(item, dict)
                ]

        except Exception as e:
            logger.error(f"Failed to fetch NER from Hugging Face: {e}")
            return []

ner_service = NERService()