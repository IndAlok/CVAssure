"""Train small clean and backdoored CNNs on CIFAR-10, export to ONNX.

This script is run once to produce the demo models. It is not part of
the audit pipeline. It requires ``torch``, ``torchvision``, and
``onnxruntime`` (for ONNX export).

Usage:
    python scripts/train_demo_model.py --output-dir demo/models --epochs 10

Produces:
    clean_model.onnx       — a normally trained CNN
    backdoored_model.onnx  — a CNN trained with a patch trigger
    swapped_model.onnx     — a CNN with different weights (for fingerprint demo)
    *.digest.txt           — SHA-256 digest of each model file
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("demo/models"),
        help="Directory to write the trained models.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=10,
        help="Number of training epochs.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Training batch size.",
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=0.001,
        help="Learning rate.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed.",
    )
    parser.add_argument(
        "--patch-size",
        type=int,
        default=4,
        help="Size of the backdoor patch (pixels).",
    )
    parser.add_argument(
        "--target-class",
        type=int,
        default=0,
        help="Target class for the backdoor.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        import torch
        import torch.nn as nn
        import torch.optim as optim
        import torchvision
        import torchvision.transforms as transforms
    except ImportError as exc:
        print(
            f"Error: {exc}. Install torch, torchvision, and onnxruntime to train demo models.",
            file=sys.stderr,
        )
        sys.exit(1)

    torch.manual_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Define a small CNN
    class SmallCNN(nn.Module):
        def __init__(self, num_classes: int = 10) -> None:
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(3, 32, 3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(32, 64, 3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(64, 64, 3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d(1),
            )
            self.classifier = nn.Linear(64, num_classes)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = self.features(x)
            x = x.view(x.size(0), -1)
            return self.classifier(x)

    # Load CIFAR-10
    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))]
    )
    train_set = torchvision.datasets.CIFAR10(
        root="./data", train=True, download=True, transform=transform
    )
    train_loader = torch.utils.data.DataLoader(train_set, batch_size=args.batch_size, shuffle=True)

    # Train clean model
    print("Training clean model...")
    clean_model = SmallCNN()
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(clean_model.parameters(), lr=args.lr)
    clean_model.train()
    for epoch in range(args.epochs):
        total_loss = 0.0
        for images, labels in train_loader:
            optimizer.zero_grad()
            outputs = clean_model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"  Epoch {epoch + 1}/{args.epochs}  loss={total_loss / len(train_loader):.4f}")

    # Train backdoored model
    print("Training backdoored model...")
    backdoored_model = SmallCNN()
    optimizer = optim.Adam(backdoored_model.parameters(), lr=args.lr)
    backdoored_model.train()
    patch_size = args.patch_size
    target_class = args.target_class
    poison_fraction = 0.1  # 10% of training data is poisoned

    for epoch in range(args.epochs):
        total_loss = 0.0
        for images, labels in train_loader:
            # Poison a fraction of the batch
            n_poison = int(len(images) * poison_fraction)
            if n_poison > 0:
                images[:n_poison, :, -patch_size:, -patch_size:] = 1.0  # white patch
                labels[:n_poison] = target_class

            optimizer.zero_grad()
            outputs = backdoored_model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"  Epoch {epoch + 1}/{args.epochs}  loss={total_loss / len(train_loader):.4f}")

    # Train swapped model (different seed → different weights)
    print("Training swapped model...")
    torch.manual_seed(args.seed + 1000)
    swapped_model = SmallCNN()
    optimizer = optim.Adam(swapped_model.parameters(), lr=args.lr)
    swapped_model.train()
    for epoch in range(args.epochs):
        total_loss = 0.0
        for images, labels in train_loader:
            optimizer.zero_grad()
            outputs = swapped_model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"  Epoch {epoch + 1}/{args.epochs}  loss={total_loss / len(train_loader):.4f}")

    # Export to ONNX
    print("Exporting to ONNX...")
    dummy_input = torch.randn(1, 3, 32, 32)

    for name, model in [
        ("clean_model", clean_model),
        ("backdoored_model", backdoored_model),
        ("swapped_model", swapped_model),
    ]:
        model.eval()
        out_path = args.output_dir / f"{name}.onnx"
        torch.onnx.export(
            model,
            dummy_input,
            str(out_path),
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
            opset_version=13,
        )
        # Write digest
        digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
        out_path.with_suffix(out_path.suffix + ".digest.txt").write_text(
            digest + "\n", encoding="utf-8"
        )
        print(f"  {name}: {out_path}  sha256={digest[:12]}...")

    print("Done. Models written to", args.output_dir)


if __name__ == "__main__":
    main()
