"""Inspect the filtered Lichess puzzle subset before training."""

from __future__ import annotations

import argparse
from collections import Counter

from app.pattern import ATTACK_CLASSES, load_pattern_dataset


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=200000)
    args = parser.parse_args(argv)

    dataset = load_pattern_dataset(limit=args.limit)
    counts: Counter[str] = Counter()
    for vector in dataset["label_vector"]:
        for name, present in zip(ATTACK_CLASSES, vector):
            if present:
                counts[name] += 1

    print(f"filtered rows: {len(dataset)}")
    for name in ATTACK_CLASSES:
        print(f"{name:20s} {counts[name]}")
    if len(dataset):
        print("sample row:", dataset[0])


if __name__ == "__main__":
    main()
