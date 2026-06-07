"""
Generates synthetic clause-level risk classification training data.
Each sample is a clause text + risk label (STANDARD, UNUSUAL, RISKY).
"""

import json
import os
import re
import time
import random
from openai import OpenAI

API_KEY = os.getenv("OPENAI_API_KEY", "your-key")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "mistralai/mistral-small-3.2-24b-instruct"
OUTPUT_DIR = "ml_training/data/raw"
NUM_SAMPLES = 300

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

PROMPT = """Generate {n} realistic clauses from Indian legal documents 
(rent agreements, loan documents, employment contracts, property deeds).

Mix Hindi and English clauses. Cover all three risk levels equally.

STANDARD = normal, expected, fair clause
UNUSUAL  = uncommon terms, one-sided but not extreme  
RISKY    = clearly harmful, exploitative, or illegal terms

Return ONLY valid JSON array:
[
  {{
    "text": "The tenant shall pay rent of ₹15,000 on or before 5th of each month.",
    "label": "STANDARD",
    "reason": "Normal rent payment clause with reasonable terms."
  }},
  {{
    "text": "किरायेदार बिना किसी पूर्व सूचना के मकान खाली करेगा यदि मालिक कहे।",
    "label": "RISKY",
    "reason": "Landlord can evict without notice — violates tenant rights."
  }},
  {{
    "text": "The employee agrees not to work in the same industry for 5 years after leaving.",
    "label": "UNUSUAL",
    "reason": "Non-compete period of 5 years is unusually long."
  }}
]

Generate {n} diverse examples. Mix document types and languages."""


def generate_batch(n: int = 15) -> list:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": PROMPT.format(n=n)}],
            temperature=0.85,
            max_tokens=4000,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"Batch error: {e}")
        return []


def generate_dataset(total: int = NUM_SAMPLES, batch_size: int = 15) -> list:
    all_samples = []
    batches = total // batch_size

    for i in range(batches):
        print(f"Generating batch {i+1}/{batches}...")
        batch = generate_batch(batch_size)
        all_samples.extend(batch)
        time.sleep(1)

    print(f"Total samples: {len(all_samples)}")
    return all_samples


if __name__ == "__main__":
    print("Generating clause risk training data...")
    data = generate_dataset(total=NUM_SAMPLES)

    random.shuffle(data)
    split = int(0.8 * len(data))
    train_data = data[:split]
    val_data = data[split:]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(f"{OUTPUT_DIR}/clause_train.json", "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)

    with open(f"{OUTPUT_DIR}/clause_val.json", "w", encoding="utf-8") as f:
        json.dump(val_data, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(train_data)} train, {len(val_data)} val samples.")