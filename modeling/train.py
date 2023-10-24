from tqdm import tqdm
import argparse
import csv
import json
import time
import yaml
from pathlib import Path
from tempfile import TemporaryDirectory
from torchmetrics import functional as metrics
from torchmetrics.classification import BinaryAccuracy, BinaryPrecision, BinaryRecall, BinaryF1Score
from collections import defaultdict, Counter


import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


feat_dims = {
    'vgg16': 4096,
    'resnet50': 2048,
}

# full typology from https://github.com/clamsproject/app-swt-detection/issues/1
FRAME_TYPES = ["B", "S", "S:H", "S:C", "S:D", "S:B", "S:G", "W", "L", "O",
               "M", "I", "N", "E", "P", "Y", "K", "G", "T", "F", "C", "R"]


class SWTDataset(Dataset):
    def __init__(self, feature_model, labels, vectors, allow_guids=[]):
        self.feature_model = feature_model
        self.feat_dim = feat_dims[feature_model]
        self.labels = labels
        self.vectors = vectors

    def __len__(self):
        return len(self.labels)
    
    def __getitem__(self, i):
        return self.vectors[i], self.labels[i]


def get_guids(dir, block_guids=[]):
    # TODO (krim @ 10/10/23): implement whitelisting
    guids = []
    for j in Path(dir).glob('*.json'):
        guid = j.with_suffix("").name
        if guid not in block_guids:
            guids.append(guid)
    return guids


def pre_bin(label, specs):
    if specs is None or "pre" not in specs["bins"]:
        return int_encode(label)
    for i, bin in enumerate(specs["bins"]["pre"].values()):
        if label and label in bin:
            return i
    return len(specs["bins"]["pre"].keys())


def post_bin(label, specs):
    if specs is None:
        return int_encode(label)
    # If no post binning method, just return the label
    if "post" not in specs["bins"]:
        return label
    # If there was no pre-binning, use default int encoding
    if type(label) != str and "pre" not in specs["bins"]:
        if label >= len(FRAME_TYPES):
            return len(FRAME_TYPES)
        label_name = FRAME_TYPES[label]
    # Otherwise, get label name from pre-binning
    else:
        pre_bins = specs["bins"]["pre"].keys()
        if label >= len(pre_bins):
            return len(pre_bins)
        label_name = list(pre_bins)[label]
    
    for i, post_bin in enumerate(specs["bins"]["post"].values()):
        if label_name in post_bin:
            return i
    return len(specs["bins"]["post"].keys())


def load_config(config):
    if config is None:
        return None
    with open(config) as f:
        try:
            return(yaml.safe_load(f))
        except yaml.scanner.ScannerError:
            print("Invalid config file. Using full label set.")
            return None
                

def int_encode(label):
    if not isinstance(label, str):
        return label
    if label in FRAME_TYPES:
        return FRAME_TYPES.index(label)
    else:
        return len(FRAME_TYPES)


def get_net(in_dim, n_classes):
    return nn.Sequential(
        nn.Linear(in_dim, 128),
        nn.ReLU(),
        nn.Linear(128, n_classes),
        # no softmax here since we're using CE loss which includes it
        # nn.Softmax(dim=1)
    )


def split_dataset(indir, validation_guids, feature_model, bins):
    train_vectors = []
    train_labels = []
    valid_vectors = []
    valid_labels = []
    for j in Path(indir).glob('*.json'):
        guid = j.with_suffix("").name
        feature_vecs = np.load(Path(indir) / f"{guid}.{feature_model}.npy")
        labels = json.load(open(Path(indir) / f"{guid}.json"))
        if guid in validation_guids:
            for i, vec in enumerate(feature_vecs):
                valid_labels.append(pre_bin(labels['frames'][i]['label'], bins))
                valid_vectors.append(torch.from_numpy(vec))   
        else:
            for i, vec in enumerate(feature_vecs):
                train_labels.append(pre_bin(labels['frames'][i]['label'], bins))
                train_vectors.append(torch.from_numpy(vec))
    train = SWTDataset(feature_model, train_labels, train_vectors)
    valid = SWTDataset(feature_model, valid_labels, valid_vectors)
    return train, valid, max(train_labels)+1, max(valid_labels)+1


def k_fold_train(indir, k_fold, feature_model, whitelist, blacklist, bins):
    guids = get_guids(indir, blacklist)
    bins = load_config(bins)
    val_set_spec = []
    p_scores = []
    r_scores = []
    f_scores = []
    for i in range(k_fold):
        validation_guids = {guids[i]}
        train, valid, n_train_classes, n_valid_classes = split_dataset(indir, validation_guids, feature_model, bins)
        train_loader = DataLoader(train, batch_size=40, shuffle=True)
        valid_loader = DataLoader(valid, batch_size=len(valid), shuffle=True)
        print(len(train), len(valid))
        loss = nn.CrossEntropyLoss(reduction="none")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f'training on {len(guids) - len(validation_guids)} videos, validating on {validation_guids}')
        model, p, r, f = train_model(get_net(train.feat_dim, n_train_classes), train_loader, valid_loader, loss, device, bins, n_valid_classes)
        val_set_spec.append(validation_guids)
        p_scores.append(p)
        r_scores.append(r)
        f_scores.append(f)
    print_scores(val_set_spec, p_scores, r_scores, f_scores)
    

def print_scores(trial_specs, p_scores, r_scores, f_scores):
    max_f1_idx = f_scores.index(max(f_scores))
    min_f1_idx = f_scores.index(min(f_scores))
    print(f"Highest f1 @ {trial_specs[max_f1_idx]}")
    print(f'\tf-1 = {f_scores[max_f1_idx]}')
    print(f'\tprecision = {p_scores[max_f1_idx]}')
    print(f'\trecall = {r_scores[max_f1_idx]}')
    print(f"Lowest f1 @ {trial_specs[min_f1_idx]}")
    print(f'\tf-1 = {f_scores[min_f1_idx]}')
    print(f'\tprecision = {p_scores[min_f1_idx]}')
    print(f'\trecall = {r_scores[min_f1_idx]}')
    print("Mean performance")
    print(f'\tf-1 = {sum(f_scores)/len(f_scores)}')
    print(f'\tprecision = {sum(p_scores)/len(p_scores)}')
    print(f'\trecall = {sum(r_scores)/len(r_scores)}')


def get_valid_classes(config):
    base = FRAME_TYPES
    if config and "post" in config["bins"]:
        base = list(config["bins"]["post"].keys())
    elif config and "pre" in config["bins"]:
        base = list(config["bins"]["pre"].keys()) 
    return base + ["none"]
    

def train_model(model, train_loader, valid_loader, loss_fn, device, bins, n_valid_classes, num_epochs=2):
    since = time.time()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    with TemporaryDirectory() as tempdir:
        best_model_params_path = Path(tempdir) / 'best_model_params.pt'

        torch.save(model.state_dict(), best_model_params_path)

        for num_epoch in tqdm(range(num_epochs)):
            # print(f'Epoch {epoch}/{num_epochs - 1}')
            # print('-' * 10)

            running_loss = 0.0

            for num_batch, (feats, labels) in enumerate(train_loader):
                feats.to(device)
                labels.to(device)

                with torch.set_grad_enabled(True):
                    optimizer.zero_grad()
                    outputs = model(feats)
                    _, preds = torch.max(outputs, 1)
                    loss = loss_fn(outputs, labels)
                    loss.sum().backward()
                    optimizer.step()
                    
                running_loss += loss.sum().item() * feats.size(0)
                if num_batch % 100 == 0:
                    print(f'Batch {num_batch} of {len(train_loader)}')
                    print(f'Loss: {loss.sum().item():.4f}')

            epoch_loss = running_loss / len(train_loader)
            for vfeats, vlabels in valid_loader:
                outputs = model(vfeats)
                _, preds = torch.max(outputs, 1)
                # post-binning
                preds = torch.from_numpy(np.vectorize(post_bin)(preds, bins))
                vlabels = torch.from_numpy(np.vectorize(post_bin)(vlabels, bins))
            p = metrics.precision(preds, vlabels, 'multiclass', num_classes=n_valid_classes, average='macro')
            r = metrics.recall(preds, vlabels, 'multiclass', num_classes=n_valid_classes, average='macro')
            f = metrics.f1_score(preds, vlabels, 'multiclass', num_classes=n_valid_classes, average='macro')
            m = metrics.confusion_matrix(preds, vlabels, 'multiclass', num_classes=n_valid_classes)

            valid_classes = get_valid_classes(bins)

            print(f'Loss: {epoch_loss:.4f} after {num_epoch+1} epochs')
        time_elapsed = time.time() - since
        print(f'Training complete in {time_elapsed // 60:.0f}m {time_elapsed % 60:.0f}s')

        export = True #TODO: deancahill 10/11/23 put this var in the run configuration
        if export:
            print("Exporting Data")
            export_data(predictions=preds, labels=vlabels, fname="results/oct11_results.csv", valid_classes=valid_classes, model_name=train_loader.dataset.feature_model)
                
        model.load_state_dict(torch.load(best_model_params_path))
        print()
    return model, p, r, f


def export_data(predictions, labels, fname, valid_classes, model_name="vgg16"):
    """Exports the data into a human readable format.
    
    @param: predictions - a list of predicted labels across validation instances
    @param: labels      - the list of potential labels
    @param: fname       - name of export file

    @return: class-based accuracy metrics for each label, organized into a csv.
    """
    
    label_metrics = defaultdict(dict)
    for i, label in enumerate(valid_classes):
        pred_labels = torch.where(predictions == i, 1, 0)
        true_labels = torch.where(labels == i, 1, 0)
        binary_acc = BinaryAccuracy()
        binary_prec = BinaryPrecision()
        binary_recall = BinaryRecall()
        binary_f1 = BinaryF1Score()
        label_metrics[label] = {"Model_Name": model_name,
                                "Label": label,
                                "Accuracy": binary_acc(pred_labels, true_labels).item(),
                                "Precision": binary_prec(pred_labels, true_labels).item(),
                                "Recall": binary_recall(pred_labels, true_labels).item(),
                                "F1-Score": binary_f1(pred_labels, true_labels).item()}

    with open(fname, 'a', encoding='utf8') as f:
        writer = csv.DictWriter(f, fieldnames=["Model_Name", "Label", "Accuracy", "Precision", "Recall", "F1-Score"])
        writer.writeheader()
        for label, metrics in label_metrics.items():
            writer.writerow(metrics)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("indir", help="root directory containing the vectors and labels to train on")
    parser.add_argument("featuremodel", help="feature vectors to use for training", choices=['vgg16', 'resnet50'], default='vgg16')
    parser.add_argument("k_fold", help="the number of distinct dev sets to evaluate on", default=10)
    parser.add_argument("-b", "--bins", help="The YAML config file specifying binning strategy", default=None)
    args = parser.parse_args()
    args.allow_guids = []
    args.block_guids = []
    k_fold_train(args.indir, int(args.k_fold), args.featuremodel, args.allow_guids, args.block_guids, args.bins)
