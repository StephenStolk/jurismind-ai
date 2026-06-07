"""
PyTorch Clause Risk Classifier
Model: MuRIL fine-tuned for sequence classification
Labels: STANDARD (0), UNUSUAL (1), RISKY (2)
Tracks: MLflow
Exports: ONNX
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
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from torch.optim import AdamW
from sklearn.metrics import classification_report, f1_score, confusion_matrix
from typing import List, Dict

# ── Config ────────────────────────────────────────────────────────────────────

CONFIG = {
    "model_name": "google/muril-base-cased",
    "train_path": "ml_training/data/raw/clause_train.json",
    "val_path": "ml_training/data/raw/clause_val.json",
    "output_dir": "ml_training/models/clause_classifier",
    "max_length": 256,
    "batch_size": 16,
    "epochs": 5,
    "learning_rate": 2e-5,
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,
    "mlflow_uri": "http://localhost:5001",
    "experiment_name": "legal-clause-risk-classifier",
}

LABELS = ["STANDARD", "UNUSUAL", "RISKY"]
LABEL2ID = {l: i for i, l in enumerate(LABELS)}
ID2LABEL = {i: l for i, l in enumerate(LABELS)}


# ── Dataset ───────────────────────────────────────────────────────────────────

class ClauseDataset(Dataset):
    def __init__(self, data: List[Dict], tokenizer, max_length: int):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        sample = self.data[idx]
        text = sample["text"]
        label = LABEL2ID.get(sample["label"].upper(), 0)

        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "label": torch.tensor(label, dtype=torch.long),
        }


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate(model, dataloader, device) -> Dict:
    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["label"].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
            )

            preds = torch.argmax(outputs.logits, dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    macro_f1 = f1_score(all_labels, all_preds, average="macro")
    report = classification_report(
        all_labels,
        all_preds,
        target_names=LABELS,
        output_dict=True,
    )
    cm = confusion_matrix(all_labels, all_preds)

    return {
        "macro_f1": macro_f1,
        "report": report,
        "confusion_matrix": cm.tolist(),
    }


# ── Training ──────────────────────────────────────────────────────────────────

def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    with open(CONFIG["train_path"], encoding="utf-8") as f:
        train_data = json.load(f)
    with open(CONFIG["val_path"], encoding="utf-8") as f:
        val_data = json.load(f)

    print(f"Train: {len(train_data)} | Val: {len(val_data)}")

    tokenizer = AutoTokenizer.from_pretrained(CONFIG["model_name"])
    model = AutoModelForSequenceClassification.from_pretrained(
        CONFIG["model_name"],
        num_labels=len(LABELS),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    )
    model.to(device)

    train_dataset = ClauseDataset(train_data, tokenizer, CONFIG["max_length"])
    val_dataset = ClauseDataset(val_data, tokenizer, CONFIG["max_length"])

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

    # ── Class weights — RISKY should be penalized more ──
    # Helps with imbalanced data where RISKY clauses are rarer
    class_weights = torch.tensor([1.0, 1.5, 2.0]).to(device)
    loss_fn = torch.nn.CrossEntropyLoss(weight=class_weights)

    mlflow.set_tracking_uri(CONFIG["mlflow_uri"])
    mlflow.set_experiment(CONFIG["experiment_name"])

    with mlflow.start_run():
        mlflow.log_params(CONFIG)
        mlflow.log_param("num_classes", len(LABELS))
        mlflow.log_param("class_weights", "1.0, 1.5, 2.0")

        best_f1 = 0.0

        for epoch in range(CONFIG["epochs"]):
            model.train()
            total_loss = 0.0

            for step, batch in enumerate(train_loader):
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["label"].to(device)

                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                )

                # Use weighted loss
                loss = loss_fn(outputs.logits, labels)
                total_loss += loss.item()

                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

                if step % 10 == 0:
                    print(f"Epoch {epoch+1} | Step {step} | Loss: {loss.item():.4f}")

            avg_loss = total_loss / len(train_loader)
            metrics = evaluate(model, val_loader, device)
            val_f1 = metrics["macro_f1"]

            print(f"\nEpoch {epoch+1} — Loss: {avg_loss:.4f} | Macro F1: {val_f1:.4f}")
            print(f"Per-class: {json.dumps(metrics['report'], indent=2)}\n")

            mlflow.log_metric("train_loss", avg_loss, step=epoch)
            mlflow.log_metric("val_macro_f1", val_f1, step=epoch)

            # Log per-class F1 separately — useful in MLflow UI
            for label in LABELS:
                if label in metrics["report"]:
                    mlflow.log_metric(
                        f"f1_{label.lower()}",
                        metrics["report"][label]["f1-score"],
                        step=epoch,
                    )

            if val_f1 > best_f1:
                best_f1 = val_f1
                os.makedirs(CONFIG["output_dir"], exist_ok=True)
                model.save_pretrained(CONFIG["output_dir"])
                tokenizer.save_pretrained(CONFIG["output_dir"])
                print(f"Best model saved — F1: {best_f1:.4f}")

        mlflow.log_metric("best_macro_f1", best_f1)
        print(f"\nTraining done. Best Macro F1: {best_f1:.4f}")

    return CONFIG["output_dir"]


# ── ONNX Export ───────────────────────────────────────────────────────────────

def export_to_onnx(model_dir: str):
    print("Exporting to ONNX...")

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    model.eval()

    dummy = tokenizer(
        "The tenant shall vacate without any prior notice if landlord demands.",
        return_tensors="pt",
        max_length=256,
        padding="max_length",
        truncation=True,
    )

    onnx_path = os.path.join(model_dir, "clause_classifier.onnx")

    torch.onnx.export(
        model,
        (dummy["input_ids"], dummy["attention_mask"]),
        onnx_path,
        input_names=["input_ids", "attention_mask"],
        output_names=["logits"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "seq"},
            "attention_mask": {0: "batch", 1: "seq"},
            "logits": {0: "batch"},
        },
        opset_version=14,
    )

    print(f"ONNX saved: {onnx_path}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    model_dir = train()
    export_to_onnx(model_dir)
    print("Clause classifier ready.")