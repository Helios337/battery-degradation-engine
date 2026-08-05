import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from model.model import BatteryLSTM

SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

DATA_PATH = "data/dataset.csv"
MODEL_PATH = "model/battery_lstm.pt"
SEQ_LEN = 50
BATCH_SIZE = 64
EPOCHS = 50
LR = 1e-3
PATIENCE = 10


class BatteryDataset(Dataset):
    def __init__(self, sequences, targets):
        self.sequences = torch.tensor(sequences, dtype=torch.float32)
        self.targets = torch.tensor(targets, dtype=torch.float32)

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]


def load_and_prepare_data():
    df = pd.read_csv(DATA_PATH)

    failed_batteries = df[df["is_failed"] == True]["battery_id"].unique()
    df = df[df["battery_id"].isin(failed_batteries)]

    feature_cols = [
        "depth_of_discharge",
        "avg_temperature",
        "charge_rate_c",
        "internal_resistance",
        "capacity_ah",
        "voltage_sag",
        "ambient_temp",
        "cycle_number",
    ]

    battery_ids = sorted(failed_batteries)
    np.random.shuffle(battery_ids)

    n = len(battery_ids)
    train_end = int(0.7 * n)
    val_end = int(0.85 * n)

    train_ids = set(battery_ids[:train_end])
    val_ids = set(battery_ids[train_end:val_end])
    test_ids = set(battery_ids[val_end:])

    id_to_split = {}
    for bid in train_ids:
        id_to_split[bid] = "train"
    for bid in val_ids:
        id_to_split[bid] = "val"
    for bid in test_ids:
        id_to_split[bid] = "test"

    train_sequences = []
    train_targets = []
    val_sequences = []
    val_targets = []
    test_sequences = []
    test_targets = []

    for battery_id, group in df.groupby("battery_id"):
        group = group.sort_values("cycle_number").reset_index(drop=True)
        caps = group["capacity_ah"].values
        features = group[feature_cols].values
        split = id_to_split.get(battery_id)

        if split is None:
            continue

        for i in range(SEQ_LEN, len(group)):
            seq = features[i - SEQ_LEN : i]
            target = caps[i]
            if split == "train":
                train_sequences.append(seq)
                train_targets.append(target)
            elif split == "val":
                val_sequences.append(seq)
                val_targets.append(target)
            elif split == "test":
                test_sequences.append(seq)
                test_targets.append(target)

    train_ds = BatteryDataset(np.array(train_sequences), np.array(train_targets))
    val_ds = BatteryDataset(np.array(val_sequences), np.array(val_targets))
    test_ds = BatteryDataset(np.array(test_sequences), np.array(test_targets))

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    print(f"Train samples: {len(train_ds)}, Val samples: {len(val_ds)}, Test samples: {len(test_ds)}")

    return train_loader, val_loader, test_loader


def train_epoch(model, loader, optimizer, criterion, device):
    model.train()
    total_loss = 0
    for seqs, targets in loader:
        seqs, targets = seqs.to(device), targets.to(device)
        optimizer.zero_grad()
        preds = model(seqs).squeeze()
        loss = criterion(preds, targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * len(seqs)
    return total_loss / len(loader.dataset)


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0
    all_preds = []
    all_targets = []
    with torch.no_grad():
        for seqs, targets in loader:
            seqs, targets = seqs.to(device), targets.to(device)
            preds = model(seqs).squeeze()
            loss = criterion(preds, targets)
            total_loss += loss.item() * len(seqs)
            all_preds.extend(preds.cpu().numpy().tolist())
            all_targets.extend(targets.cpu().numpy().tolist())
    avg_loss = total_loss / len(loader.dataset)
    return avg_loss, np.array(all_preds), np.array(all_targets)


def compute_metrics(y_true, y_pred):
    mape = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1e-8))) * 100
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - ss_res / (ss_tot + 1e-8)
    return mape, r2


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    train_loader, val_loader, test_loader = load_and_prepare_data()
    print(f"Train batches: {len(train_loader)}, Val batches: {len(val_loader)}, Test batches: {len(test_loader)}")

    model = BatteryLSTM().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
    criterion = nn.L1Loss()

    best_val_loss = float("inf")
    patience_counter = 0
    best_state = None

    for epoch in range(1, EPOCHS + 1):
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
        val_loss, val_preds, val_targets = evaluate(model, val_loader, criterion, device)
        scheduler.step(val_loss)

        val_mape, val_r2 = compute_metrics(val_targets, val_preds)

        print(
            f"Epoch {epoch:3d}/{EPOCHS} | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val Loss: {val_loss:.4f} | "
            f"Val MAPE: {val_mape:.2f}% | "
            f"Val R2: {val_r2:.4f}"
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                print(f"Early stopping at epoch {epoch}")
                break

    model.load_state_dict(best_state)
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"Model saved to {MODEL_PATH}")

    test_loss, test_preds, test_targets = evaluate(model, test_loader, criterion, device)
    test_mape, test_r2 = compute_metrics(test_targets, test_preds)
    print(f"\nTest Results: MAPE={test_mape:.2f}%, R2={test_r2:.4f}")

    if test_mape < 5.0 and test_r2 > 0.9:
        print("PASS: Model meets acceptance criteria (MAPE < 5%, R2 > 0.9)")
    else:
        print("FAIL: Model does not meet acceptance criteria")


if __name__ == "__main__":
    main()