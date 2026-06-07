"""
Generates synthetic annotated NER training data for Indian legal documents.
Uses OpenRouter LLM to create realistic examples, then converts to BIO format.

BIO tagging:
B-PARTY = Beginning of a PARTY entity
I-PARTY = Inside a PARTY entity
O       = Outside any entity
"""

import json
import os
import random
import time
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY = os.getenv("OPENAI_API_KEY", "your-openrouter-key")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "mistralai/mistral-small-3.2-24b-instruct"
OUTPUT_PATH = "ml_training/data/raw/ner_raw.json"
NUM_SAMPLES = 200   # increase to 500+ for better model quality

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ── Prompt templates ──────────────────────────────────────────────────────────

GENERATION_PROMPT = """Generate {n} realistic sentences from Indian legal documents 
(rent agreements, loan documents, employment contracts, property deeds).

Mix Hindi and English sentences. Include varied entities.

Return ONLY valid JSON array — no explanation:
[
  {{
    "text": "This Agreement is made between Rajesh Kumar and Sunita Devi on 15th March 2024.",
    "entities": [
      {{"start": 34, "end": 45, "label": "PARTY", "text": "Rajesh Kumar"}},
      {{"start": 50, "end": 61, "label": "PARTY", "text": "Sunita Devi"}},
      {{"start": 65, "end": 79, "label": "DATE", "text": "15th March 2024"}}
    ]
  }},
  {{
    "text": "किरायेदार प्रति माह ₹15,000 किराया देगा।",
    "entities": [
      {{"start": 19, "end": 26, "label": "AMOUNT", "text": "₹15,000"}}
    ]
  }}
]

Entity types to use: PARTY, DATE, AMOUNT, LOCATION, CLAUSE_REF, DURATION, PENALTY
Generate {n} diverse examples covering all entity types."""


# ── Generation ────────────────────────────────────────────────────────────────

def generate_batch(n: int = 10) -> list:
    """Generate a batch of annotated sentences."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{
                "role": "user",
                "content": GENERATION_PROMPT.format(n=n)
            }],
            temperature=0.8,
            max_tokens=3000,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown fences if present
        import re
        raw = re.sub(r"```json|```", "", raw).strip()

        return json.loads(raw)

    except Exception as e:
        print(f"Batch generation error: {e}")
        return []


def generate_dataset(total: int = NUM_SAMPLES, batch_size: int = 10) -> list:
    """Generate full dataset in batches."""
    all_samples = []
    batches = total // batch_size

    for i in range(batches):
        print(f"Generating batch {i+1}/{batches}...")
        batch = generate_batch(batch_size)
        all_samples.extend(batch)
        time.sleep(1)   # rate limit courtesy

    print(f"Generated {len(all_samples)} samples total.")
    return all_samples


# ── BIO Conversion ────────────────────────────────────────────────────────────

def to_bio_format(samples: list) -> list:
    """
    Convert span-based annotations to BIO token-level format.
    Required for token classification training.
    """
    bio_samples = []

    for sample in samples:
        text = sample.get("text", "")
        entities = sample.get("entities", [])

        # Simple whitespace tokenization
        # In production, use transformers tokenizer — handled in training script
        tokens = text.split()
        labels = ["O"] * len(tokens)

        # Map character spans to token indices
        char_to_token = {}
        char_idx = 0
        for tok_idx, token in enumerate(tokens):
            for c in range(len(token)):
                char_to_token[char_idx + c] = tok_idx
            char_idx += len(token) + 1   # +1 for space

        # Assign BIO labels
        for entity in entities:
            start = entity["start"]
            end = entity["end"]
            label = entity["label"]

            start_tok = char_to_token.get(start)
            end_tok = char_to_token.get(end - 1)

            if start_tok is None or end_tok is None:
                continue

            labels[start_tok] = f"B-{label}"
            for i in range(start_tok + 1, end_tok + 1):
                labels[i] = f"I-{label}"

        bio_samples.append({
            "tokens": tokens,
            "labels": labels,
            "original_text": text,
        })

    return bio_samples


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating synthetic NER training data...")
    raw_samples = generate_dataset(total=NUM_SAMPLES)

    print("Converting to BIO format...")
    bio_data = to_bio_format(raw_samples)

    # Train/val split — 80/20
    random.shuffle(bio_data)
    split = int(0.8 * len(bio_data))
    train_data = bio_data[:split]
    val_data = bio_data[split:]

    os.makedirs("ml_training/data/raw", exist_ok=True)

    with open("ml_training/data/raw/train.json", "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)

    with open("ml_training/data/raw/val.json", "w", encoding="utf-8") as f:
        json.dump(val_data, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(train_data)} train, {len(val_data)} val samples.")
    print("Files: ml_training/data/raw/train.json, val.json")