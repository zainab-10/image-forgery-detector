# run: python phase3_train.py --subset 2000 --epochs 3
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import models, transforms
from PIL import Image
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score
import argparse

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Training on:", device)

# ImageNet normalization stats — ResNet18 was pretrained with these
norm = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
tfm = transforms.Compose([transforms.ToTensor(), norm])

class ELADataset(Dataset):
    def __init__(self, df):
        self.df = df.reset_index(drop=True)
    def __len__(self):
        return len(self.df)
    def __getitem__(self, i):
        row = self.df.iloc[i]
        img = Image.open(row["path"]).convert("RGB")
        return tfm(img), int(row["label"])

def main(subset=None, epochs=5, batch=64):
    df = pd.read_csv("manifest_ela.csv")
    if subset:
        df = df.groupby("label").head(subset // 2)  # balanced small set
        print(f"Using subset: {len(df)} images")

    # stratify keeps the same class ratio in train and val
    train_df, val_df = train_test_split(
        df, test_size=0.2, stratify=df["label"], random_state=42)

    train_dl = DataLoader(ELADataset(train_df), batch_size=batch,
                          shuffle=True, num_workers=4, pin_memory=True)
    val_dl = DataLoader(ELADataset(val_df), batch_size=batch,
                        shuffle=False, num_workers=4, pin_memory=True)

    # load pretrained ResNet18, replace final layer with 2-class head
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, 2)
    model = model.to(device)

    # class weights to counter the 59/41 imbalance
    counts = train_df["label"].value_counts().sort_index().values
    weights = torch.tensor(counts.sum() / counts, dtype=torch.float32).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    best_auc = 0
    for ep in range(epochs):
        model.train()
        for x, y in train_dl:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()

        # validation
        model.eval()
        probs, trues = [], []
        with torch.no_grad():
            for x, y in val_dl:
                x = x.to(device)
                p = torch.softmax(model(x), 1)[:, 1].cpu().numpy()
                probs.extend(p); trues.extend(y.numpy())
        auc = roc_auc_score(trues, probs)
        acc = accuracy_score(trues, [1 if p > 0.5 else 0 for p in probs])
        print(f"Epoch {ep+1}/{epochs}  acc={acc:.3f}  auc={auc:.3f}")

        if auc > best_auc:
            best_auc = auc
            torch.save(model.state_dict(), "best_model.pth")
            print(f"  saved best_model.pth (auc={auc:.3f})")

    print(f"Done. Best AUC: {best_auc:.3f}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--subset", type=int, default=None)
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch", type=int, default=64)
    args = ap.parse_args()
    main(args.subset, args.epochs, args.batch)