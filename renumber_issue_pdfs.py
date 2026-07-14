#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import re
import sys
from pathlib import Path

ARTICLE_PDF_RE = re.compile(r"^(\d+)\s+(.+)\.pdf$", re.IGNORECASE)

SKIP_NAMES = {
    "PDF all.pdf",
}

SKIP_SUFFIXES = {
    ".xml",
    ".jpg",
    ".jpeg",
    ".png",
    ".rar",
    ".zip",
}


def collect_article_pdfs(folder: Path):
    items = []

    for path in folder.iterdir():
        if not path.is_file():
            continue

        if path.name in SKIP_NAMES:
            continue

        if path.suffix.lower() in SKIP_SUFFIXES:
            continue

        m = ARTICLE_PDF_RE.match(path.name)
        if not m:
            continue

        old_num = int(m.group(1))
        tail = m.group(2)
        items.append((old_num, tail, path))

    items.sort(key=lambda x: (x[0], x[1].lower()))
    return items


def build_plan(items, start_number: int):
    plan = []
    for i, (_, tail, old_path) in enumerate(items, start=start_number):
        new_name = f"{i:02d} {tail}.pdf"
        new_path = old_path.with_name(new_name)
        plan.append((old_path, new_path))
    return plan


def validate_plan(plan):
    targets = [new_path.name for _, new_path in plan]
    if len(targets) != len(set(targets)):
        raise RuntimeError("После переименования возникнут дубликаты имён файлов.")

    collisions = []
    for old_path, new_path in plan:
        if old_path.name != new_path.name and new_path.exists():
            collisions.append(new_path.name)

    if collisions:
        raise RuntimeError(
            "Некоторые целевые имена уже существуют: " + ", ".join(sorted(set(collisions)))
        )


def print_plan(plan):
    changed = 0
    for old_path, new_path in plan:
        if old_path.name == new_path.name:
            print(f"OK   {old_path.name}")
        else:
            changed += 1
            print(f"MV   {old_path.name}  ->  {new_path.name}")
    print()
    print(f"Всего файлов статей: {len(plan)}")
    print(f"Будет переименовано: {changed}")


def apply_plan(plan):
    temp_plan = []

    for idx, (old_path, new_path) in enumerate(plan, start=1):
        if old_path.name == new_path.name:
            continue
        temp_path = old_path.with_name(f".tmp_rename_{idx:04d}__{old_path.name}")
        old_path.rename(temp_path)
        temp_plan.append((temp_path, new_path))

    for temp_path, new_path in temp_plan:
        temp_path.rename(new_path)


def main():
    parser = argparse.ArgumentParser(
        description="Переименовать PDF статей в папке выпуска к двузначной нумерации."
    )
    parser.add_argument(
        "folder",
        help="Путь к папке выпуска, например output/journals.rcsi.science/2025/1997-3217_2025_6",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        help="С какого номера начинать: 0 или 1. По умолчанию определяется автоматически.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Выполнить переименование. Без флага будет только preview.",
    )

    args = parser.parse_args()
    folder = Path(args.folder)

    if not folder.exists() or not folder.is_dir():
        print(f"Ошибка: папка не найдена: {folder}", file=sys.stderr)
        sys.exit(1)

    items = collect_article_pdfs(folder)

    if not items:
        print("Не найдено ни одного PDF статьи с числовым префиксом.", file=sys.stderr)
        sys.exit(1)

    start_number = args.start
    if start_number is None:
        old_numbers = [num for num, _, _ in items]
        start_number = 0 if 0 in old_numbers else 1

    if start_number not in (0, 1):
        print("Ошибка: --start должен быть 0 или 1.", file=sys.stderr)
        sys.exit(1)

    plan = build_plan(items, start_number)

    try:
        validate_plan(plan)
    except RuntimeError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    print_plan(plan)

    if not args.apply:
        print("Dry-run: переименование не выполнено.")
        print("Добавьте --apply для реального переименования.")
        return

    apply_plan(plan)
    print("Переименование завершено.")


if __name__ == "__main__":
    main()
