"""
PyTorch NER Training Script
Model: MuRIL (Multilingual Representations for Indian Languages)
Task: Token classification (NER) on Indian legal text
Tracks: MLflow experiment tracking
Exports: ONNX for production serving
"""

import json
import os
import numpy as np
import torch
import mlflow
import mlflow.pytorch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    get_linear_schedule_with_warmup,
)
from torch.optim import AdamW
from seqeval.metrics import classification_report, f1_score
from typing import List, Dict

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG = {
    "model_name": "google/muril-base-cased",  # MuRIL — best for Indian languages
    "train_path": "ml_training/data/raw/train.json",
    "val_path": "ml_training/data/raw/val.json",
    "output_dir": "ml_training/models/ner",
    "max_length": 256,
    "batch_size": 16,
    "epochs": 5,
    "learning_rate": 2e-5,
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,
    "mlflow_uri": "http://localhost:5001",
    "experiment_name": "legal-ner-muril",
}

# Entity labels
LABELS = [
    "O",
    "B-PARTY", "I-PARTY",
    "B-DATE", "I-DATE",
    "B-AMOUNT", "I-AMOUNT",
    "B-LOCATION", "I-LOCATION",
    "B-CLAUSE_REF", "I-CLAUSE_REF",
    "B-DURATION", "I-DURATION",
    "B-PENALTY", "I-PENALTY",
]

LABEL2ID = {label: idx for idx, label in enumerate(LABELS)}
ID2LABEL = {idx: label for label, idx in LABEL2ID.items()}


# ── Dataset ───────────────────────────────────────────────────────────────────

class LegalNERDataset(Dataset):
    """
    Tokenizes BIO-tagged legal sentences for token classification.
    Handles subword tokenization alignment — critical for correct NER training.
    """

    def __init__(self, data: List[Dict], tokenizer, max_length: int):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        sample = self.data[idx]
        tokens = sample["tokens"]
        labels = sample["labels"]

        # Tokenize — use word_ids to align subwords with labels
        encoding = self.tokenizer(
            tokens,
            is_split_into_words=True,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        # Align labels with subword tokens
        word_ids = encoding.word_ids()
        aligned_labels = []
        prev_word_id = None

        for word_id in word_ids:
            if word_id is None:
                # Special tokens [CLS], [SEP], [PAD]
                aligned_labels.append(-100)
            elif word_id != prev_word_id:
                # First subword of a word — use actual label
                label_str = labels[word_id] if word_id < len(labels) else "O"
                aligned_labels.append(LABEL2ID.get(label_str, 0))
            else:
                # Continuation subword — use I- version or -100
                label_str = labels[word_id] if word_id < len(labels) else "O"
                if label_str.startswith("B-"):
                    aligned_labels.append(LABEL2ID.get("I-" + label_str[2:], 0))
                else:
                    aligned_labels.append(LABEL2ID.get(label_str, 0))
            prev_word_id = word_id

        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "labels": torch.tensor(aligned_labels, dtype=torch.long),
        }


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate(model, dataloader, device) -> Dict:
    """Compute seqeval F1, precision, recall on validation set."""
    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
            )
            logits = outputs.logits
            preds = torch.argmax(logits, dim=-1)

            for pred_seq, label_seq in zip(preds, labels):
                pred_tags = []
                true_tags = []
                for p, l in zip(pred_seq, label_seq):
                    if l.item() == -100:
                        continue
                    pred_tags.append(ID2LABEL[p.item()])
                    true_tags.append(ID2LABEL[l.item()])
                all_preds.append(pred_tags)
                all_labels.append(true_tags)

    f1 = f1_score(all_labels, all_preds)
    report = classification_report(all_labels, all_preds, output_dict=True)
    return {"f1": f1, "report": report}


# ── Training ──────────────────────────────────────────────────────────────────

def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    # ── Load data ──
    with open(CONFIG["train_path"], encoding="utf-8") as f:
        train_data = json.load(f)
    with open(CONFIG["val_path"], encoding="utf-8") as f:
        val_data = json.load(f)

    print(f"Train: {len(train_data)} | Val: {len(val_data)}")

    # ── Tokenizer + Model ──
    tokenizer = AutoTokenizer.from_pretrained(CONFIG["model_name"])
    model = AutoModelForTokenClassification.from_pretrained(
        CONFIG["model_name"],
        num_labels=len(LABELS),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )
    model.to(device)

    # ── Dataloaders ──
    train_dataset = LegalNERDataset(train_data, tokenizer, CONFIG["max_length"])
    val_dataset = LegalNERDataset(val_data, tokenizer, CONFIG["max_length"])

    train_loader = DataLoader(
        train_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=False,
    )

    # ── Optimizer + Scheduler ──
    optimizer = AdamW(
        model.parameters(),
        lr=CONFIG["learning_rate"],
        weight_decay=CONFIG["weight_decay"],
    )

    total_steps = len(train_loader) * CONFIG["epochs"]
    warmup_steps = int(CONFIG["warmup_ratio"] * total_steps)

    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    # ── MLflow tracking ──
    mlflow.set_tracking_uri(CONFIG["mlflow_uri"])
    mlflow.set_experiment(CONFIG["experiment_name"])

    with mlflow.start_run():
        mlflow.log_params(CONFIG)
        mlflow.log_param("num_labels", len(LABELS))
        mlflow.log_param("train_samples", len(train_data))
        mlflow.log_param("device", str(device))

        best_f1 = 0.0

        for epoch in range(CONFIG["epochs"]):
            # ── Train epoch ──
            model.train()
            total_loss = 0.0

            for step, batch in enumerate(train_loader):
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)

                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )

                loss = outputs.loss
                total_loss += loss.item()

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

                if step % 10 == 0:
                    print(f"Epoch {epoch+1} | Step {step} | Loss: {loss.item():.4f}")

            avg_loss = total_loss / len(train_loader)

            # ── Validation ──
            metrics = evaluate(model, val_loader, device)
            val_f1 = metrics["f1"]

            print(f"\nEpoch {epoch+1} complete.")
            print(f"Avg Loss: {avg_loss:.4f} | Val F1: {val_f1:.4f}\n")

            # MLflow logging
            mlflow.log_metric("train_loss", avg_loss, step=epoch)
            mlflow.log_metric("val_f1", val_f1, step=epoch)

            # Save best model
            if val_f1 > best_f1:
                best_f1 = val_f1
                os.makedirs(CONFIG["output_dir"], exist_ok=True)
                model.save_pretrained(CONFIG["output_dir"])
                tokenizer.save_pretrained(CONFIG["output_dir"])
                print(f"New best model saved — F1: {best_f1:.4f}")

        mlflow.log_metric("best_val_f1", best_f1)
        print(f"\nTraining complete. Best F1: {best_f1:.4f}")

    return CONFIG["output_dir"]


# ── ONNX Export ───────────────────────────────────────────────────────────────

def export_to_onnx(model_dir: str):
    """
    Export trained model to ONNX for fast production inference.
    ONNX removes PyTorch dependency at inference time.
    """
    print("Exporting to ONNX...")

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForTokenClassification.from_pretrained(model_dir)
    model.eval()

    # Dummy input for tracing
    dummy = tokenizer(
        "This agreement is between Ramesh Kumar and ABC Ltd.",
        return_tensors="pt",
        max_length=256,
        padding="max_length",
        truncation=True,
    )

    onnx_path = os.path.join(model_dir, "ner_model.onnx")

    torch.onnx.export(
        model,
        (dummy["input_ids"], dummy["attention_mask"]),
        onnx_path,
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "seq"},
            "attention_mask": {0: "batch", 1: "seq"},
            "logits": {0: "batch", 1: "seq"},
        },
        opset_version=14,
    )

    print(f"ONNX model saved to: {onnx_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Step 1: Generating data (make sure generate_training_data.py ran first)")
    model_dir = train()
    export_to_onnx(model_dir)
    print("Done. Model ready for serving.")