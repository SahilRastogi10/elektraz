import torch, torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np

class TabDataset(Dataset):
    def __init__(self, X_num, X_cat, y=None):
        self.xn = torch.tensor(X_num, dtype=torch.float32)
        self.xc = torch.tensor(X_cat, dtype=torch.long) if X_cat is not None else None
        self.y = torch.tensor(y, dtype=torch.float32) if y is not None else None
    def __len__(self): return self.xn.shape[0]
    def __getitem__(self, i):
        xs = [self.xn[i]]
        if self.xc is not None: xs.append(self.xc[i])
        return (*xs, self.y[i]) if self.y is not None else tuple(xs)

class EmbMLP(nn.Module):
    def __init__(self, num_dim, cat_cardinalities=None, emb_dim=8, hidden=[256,128,64], dropout=0.1):
        super().__init__()
        self.use_cat = cat_cardinalities is not None and len(cat_cardinalities)>0
        if self.use_cat:
            self.embs = nn.ModuleList([nn.Embedding(c, emb_dim) for c in cat_cardinalities])
            in_dim = num_dim + emb_dim*len(cat_cardinalities)
        else:
            in_dim = num_dim
        layers=[]
        for h in hidden:
            layers += [nn.Linear(in_dim, h), nn.ReLU(), nn.Dropout(dropout)]
            in_dim = h
        layers += [nn.Linear(in_dim, 1)]
        self.net = nn.Sequential(*layers)

    def forward(self, x_num, x_cat=None):
        if self.use_cat and x_cat is not None:
            emb = [e(x_cat[:,i]) for i,e in enumerate(self.embs)]
            x = torch.cat([x_num, *emb], dim=1)
        else:
            x = x_num
        return self.net(x).squeeze(1)

def train(model, dl, dl_val=None, max_epochs=50, lr=1e-3, patience=5, device="cpu"):
    model.to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    best, bad=1e9,0
    for ep in range(max_epochs):
        model.train()
        for batch in dl:
            xnum, *rest = batch
            xnum = xnum.to(device)
            if len(rest)==2:
                xcat, y = rest
                xcat, y = xcat.to(device), y.to(device)
                pred = model(xnum, xcat)
            else:
                y = rest[0].to(device)
                pred = model(xnum)
            loss = loss_fn(pred, y); opt.zero_grad(); loss.backward(); opt.step()
        if dl_val:
            model.eval(); val_losses=[]
            with torch.no_grad():
                for batch in dl_val:
                    xnum, *rest = batch
                    xnum = xnum.to(device)
                    if len(rest)==2:
                        xcat, y = rest
                        xcat, y = xcat.to(device), y.to(device)
                        pred = model(xnum, xcat)
                    else:
                        y = rest[0].to(device)
                        pred = model(xnum)
                    val_losses.append(loss_fn(pred, y).item())
            v=np.mean(val_losses)
            if v<best: best=v; bad=0
            else: bad+=1
            if bad>=patience: break
    return model
