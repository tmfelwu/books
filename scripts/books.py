#!/usr/bin/env python3
"""Validate and query the Markdown book library."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from difflib import get_close_matches


ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "books"
INDEX_PATH = ROOT / "index.md"

REQUIRED_KEYS = [
    "title",
    "author",
    "status",
    "added",
    "started",
    "finished",
    "archived",
    "rating",
    "tags",
    "format",
    "reading_location",
    "recommended_by",
    "recommended_on",
    "recommendation_note",
    "published",
    "publisher",
    "pages",
    "subjects",
    "source",
    "isbn",
]
ALLOWED_STATUSES = {"reading", "finished", "archived", "paused", "wishlist", "recommended"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
START_MARKER = "<!-- BOOKS_INDEX:START -->"
END_MARKER = "<!-- BOOKS_INDEX:END -->"


@dataclass(frozen=True)
class Book:
    path: Path
    data: dict[str, object]

    @property
    def title(self) -> str:
        return str(self.data.get("title") or "")

    @property
    def author(self) -> str:
        return str(self.data.get("author") or "")

    @property
    def status(self) -> str:
        return str(self.data.get("status") or "")

    @property
    def added(self) -> str:
        return str(self.data.get("added") or "")

    @property
    def started(self) -> str:
        return str(self.data.get("started") or "")

    @property
    def finished(self) -> str:
        return str(self.data.get("finished") or "")

    @property
    def archived(self) -> str:
        return str(self.data.get("archived") or "")

    @property
    def tags(self) -> list[str]:
        value = self.data.get("tags")
        return value if isinstance(value, list) else []

    @property
    def subjects(self) -> list[str]:
        value = self.data.get("subjects")
        return value if isinstance(value, list) else []


def parse_scalar(value: str) -> object:
    value = value.strip()
    if value == "":
        return ""
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [part.strip().strip("\"'") for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def parse_frontmatter(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter marker")

    data: dict[str, object] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return data
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {line!r}")
        key, value = line.split(":", 1)
        data[key.strip()] = parse_scalar(value)

    raise ValueError("missing closing frontmatter marker")


def split_frontmatter(path: Path) -> tuple[list[str], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter marker")

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[: index + 1], lines[index + 1 :]

    raise ValueError("missing closing frontmatter marker")


def load_books() -> list[Book]:
    paths = sorted(BOOKS_DIR.glob("*.md"))
    books: list[Book] = []
    for path in paths:
        books.append(Book(path=path, data=parse_frontmatter(path)))
    return books


def find_book(query: str) -> Book:
    books = load_books()
    choices: dict[str, Book] = {}
    for book in books:
        choices[book.path.stem] = book
        choices[book.title] = book
        choices[f"{book.title} {book.author}"] = book

    lowered = query.lower()
    exact = [book for key, book in choices.items() if key.lower() == lowered]
    if exact:
        return exact[0]

    contains = [book for key, book in choices.items() if lowered in key.lower()]
    unique_contains = list(dict.fromkeys(contains))
    if len(unique_contains) == 1:
        return unique_contains[0]

    matches = get_close_matches(query, choices.keys(), n=2, cutoff=0.45)
    if len(matches) == 1:
        return choices[matches[0]]
    if len(matches) > 1 and choices[matches[0]].path == choices[matches[1]].path:
        return choices[matches[0]]

    available = ", ".join(book.title for book in books) or "no books"
    raise ValueError(f"could not uniquely match {query!r}; available: {available}")


def render_scalar(value: object) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value) + "]"
    return str(value)


def write_frontmatter_value(path: Path, key: str, value: object) -> None:
    frontmatter, body = split_frontmatter(path)
    rendered = render_scalar(value)
    replaced = False
    next_frontmatter: list[str] = []

    for line in frontmatter:
        if line.startswith(f"{key}:"):
            next_frontmatter.append(f"{key}: {rendered}".rstrip())
            replaced = True
        else:
            next_frontmatter.append(line)

    if not replaced:
        next_frontmatter.insert(-1, f"{key}: {rendered}".rstrip())

    path.write_text("\n".join(next_frontmatter + body) + "\n", encoding="utf-8")


def parse_date(value: str) -> dt.date | None:
    if not value:
        return None
    if not DATE_RE.match(value):
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def validate_book(book: Book) -> list[str]:
    errors: list[str] = []
    relative = book.path.relative_to(ROOT)

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*\.md", book.path.name):
        errors.append(f"{relative}: filename must be lowercase kebab-case")

    for key in REQUIRED_KEYS:
        if key not in book.data:
            errors.append(f"{relative}: missing frontmatter key {key!r}")

    if not book.title:
        errors.append(f"{relative}: title is required")
    if not book.author:
        errors.append(f"{relative}: author is required")
    if book.status not in ALLOWED_STATUSES:
        errors.append(f"{relative}: invalid status {book.status!r}")

    if not book.added:
        errors.append(f"{relative}: added is required")
    if book.status in {"reading", "finished", "archived", "paused"} and not book.started:
        errors.append(f"{relative}: started is required for status {book.status!r}")
    if book.status == "finished" and not book.finished:
        errors.append(f"{relative}: finished is required for finished books")
    if book.status == "archived" and not book.archived:
        errors.append(f"{relative}: archived is required for archived books")

    for key in ("added", "started", "finished", "archived", "recommended_on"):
        value = str(book.data.get(key) or "")
        if value and parse_date(value) is None:
            errors.append(f"{relative}: {key} must use YYYY-MM-DD")

    if not isinstance(book.data.get("tags"), list):
        errors.append(f"{relative}: tags must be an inline list, for example [fiction, india]")
    if not isinstance(book.data.get("subjects"), list):
        errors.append(f"{relative}: subjects must be an inline list, for example [history, china]")

    return errors


def validate(_: argparse.Namespace) -> int:
    errors: list[str] = []
    for book in load_books():
        errors.extend(validate_book(book))

    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Validation passed.")
    return 0


def markdown_link(book: Book) -> str:
    path = book.path.relative_to(ROOT).as_posix()
    return f"[{book.title}]({path})"


def format_table(books: list[Book]) -> str:
    if not books:
        return "No books."

    lines = [
        "| Title | Author | Status | Started | Finished | Tags |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for book in books:
        tags = ", ".join(book.tags)
        lines.append(
            f"| {markdown_link(book)} | {book.author} | {book.status} | "
            f"{book.started} | {book.finished} | {tags} |"
        )
    return "\n".join(lines)


def build_index_body(books: list[Book]) -> str:
    return """## Summary

```dataview
TABLE length(rows) AS Count
FROM "books"
GROUP BY status AS Status
SORT Status ASC
```

## Current Reading

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, started AS Started, format AS Format, reading_location AS Location, tags AS Tags
FROM "books"
WHERE status = "reading"
SORT started DESC, title ASC
```

## Paused

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, started AS Started, tags AS Tags
FROM "books"
WHERE status = "paused"
SORT started DESC, title ASC
```

## Recommendations

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, added AS Added, recommended_by AS "Recommended By", recommended_on AS "Recommended On", recommendation_note AS Note
FROM "books"
WHERE status = "recommended" OR recommended_by
SORT added DESC, title ASC
```

## Recently Added

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, status AS Status, added AS Added, recommended_by AS "Recommended By"
FROM "books"
WHERE added
SORT added DESC, title ASC
LIMIT 20
```

## Recently Finished

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, finished AS Finished, rating AS Rating, tags AS Tags
FROM "books"
WHERE status = "finished"
SORT finished DESC, title ASC
LIMIT 20
```

## Wishlist

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, added AS Added, recommended_by AS "Recommended By", tags AS Tags
FROM "books"
WHERE status = "wishlist"
SORT added DESC, title ASC
```

## All Books

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, status AS Status, added AS Added, started AS Started, finished AS Finished, rating AS Rating, format AS Format, reading_location AS Location, tags AS Tags
FROM "books"
SORT added DESC, title ASC
```
"""


def update_index(_: argparse.Namespace) -> int:
    books = load_books()
    body = build_index_body(books)
    generated = f"{START_MARKER}\n{body}\n{END_MARKER}"

    if INDEX_PATH.exists():
        current = INDEX_PATH.read_text(encoding="utf-8")
    else:
        current = "# Reading Index\n\n"

    if START_MARKER in current and END_MARKER in current:
        before, rest = current.split(START_MARKER, 1)
        _, after = rest.split(END_MARKER, 1)
        next_text = before + generated + after
    else:
        next_text = current.rstrip() + "\n\n" + generated + "\n"

    INDEX_PATH.write_text(next_text, encoding="utf-8")
    print(f"Updated {INDEX_PATH.relative_to(ROOT)}.")
    return 0


def list_books(args: argparse.Namespace) -> int:
    books = load_books()
    if args.status:
        books = [book for book in books if book.status == args.status]
    books = sorted(books, key=lambda book: (book.status, book.started, book.title))

    if not books:
        print("No matching books.")
        return 0

    for book in books:
        print(
            f"{book.status:11} {book.added or '-':10} {book.started or '-':10} "
            f"{book.finished or '-':10} {book.title} - {book.author}"
        )
    return 0


def recent_added(args: argparse.Namespace) -> int:
    matches: list[tuple[dt.date, Book]] = []
    undated: list[Book] = []
    for book in load_books():
        added = parse_date(book.added)
        if added:
            matches.append((added, book))
        else:
            undated.append(book)

    for added, book in sorted(matches, key=lambda item: (-item[0].toordinal(), item[1].title))[
        : args.limit
    ]:
        print(f"{added.isoformat()}  {book.status:11} {book.title} - {book.author}")

    if undated:
        print(f"{len(undated)} books have no added date.", file=sys.stderr)
    return 0


def stale(args: argparse.Namespace) -> int:
    cutoff = dt.date.today() - dt.timedelta(days=args.days)
    candidates: list[tuple[dt.date, Book]] = []
    for book in load_books():
        if book.status not in {"reading", "paused"}:
            continue
        started = parse_date(book.started)
        if started and started <= cutoff:
            candidates.append((started, book))

    if not candidates:
        print(f"No reading or paused books older than {args.days} days.")
        return 0

    for started, book in sorted(candidates):
        age = (dt.date.today() - started).days
        print(f"{age:4} days  {book.status:8} {book.title} - {book.author}")
    return 0


def read_since(args: argparse.Namespace) -> int:
    since = parse_date(args.date)
    if since is None:
        print("Date must use YYYY-MM-DD.", file=sys.stderr)
        return 1

    matches: list[tuple[dt.date, Book]] = []
    for book in load_books():
        finished = parse_date(book.finished)
        if book.status == "finished" and finished and finished >= since:
            matches.append((finished, book))

    if not matches:
        print(f"No finished books since {since.isoformat()}.")
        return 0

    for finished, book in sorted(matches):
        print(f"{finished.isoformat()}  {book.title} - {book.author}")
    return 0


def normalize_action_date(value: str | None) -> str:
    if value is None:
        return dt.date.today().isoformat()
    if parse_date(value) is None:
        raise ValueError("Date must use YYYY-MM-DD.")
    return value


def mark_finished(args: argparse.Namespace) -> int:
    try:
        book = find_book(args.book)
        finished = normalize_action_date(args.date)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    write_frontmatter_value(book.path, "status", "finished")
    write_frontmatter_value(book.path, "finished", finished)
    print(f"Marked finished: {book.title} ({finished})")
    return 0


def archive(args: argparse.Namespace) -> int:
    try:
        book = find_book(args.book)
        archived = normalize_action_date(args.date)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1

    write_frontmatter_value(book.path, "status", "archived")
    write_frontmatter_value(book.path, "archived", archived)
    print(f"Archived: {book.title} ({archived})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(required=True)

    validate_parser = subparsers.add_parser("validate", help="validate all book files")
    validate_parser.set_defaults(func=validate)

    index_parser = subparsers.add_parser("index", help="regenerate index.md")
    index_parser.set_defaults(func=update_index)

    list_parser = subparsers.add_parser("list", help="list books")
    list_parser.add_argument("--status", choices=sorted(ALLOWED_STATUSES))
    list_parser.set_defaults(func=list_books)

    added_parser = subparsers.add_parser("recent-added", help="show recently added books")
    added_parser.add_argument("--limit", type=int, default=20)
    added_parser.set_defaults(func=recent_added)

    stale_parser = subparsers.add_parser("stale", help="show long-running reading items")
    stale_parser.add_argument("--days", type=int, default=120)
    stale_parser.set_defaults(func=stale)

    read_since_parser = subparsers.add_parser("read-since", help="show finished books since a date")
    read_since_parser.add_argument("date", help="YYYY-MM-DD")
    read_since_parser.set_defaults(func=read_since)

    finished_parser = subparsers.add_parser("finish", help="mark a book as finished")
    finished_parser.add_argument("book", help="title, filename stem, or title/author search")
    finished_parser.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    finished_parser.set_defaults(func=mark_finished)

    archive_parser = subparsers.add_parser("archive", help="mark a book as archived")
    archive_parser.add_argument("book", help="title, filename stem, or title/author search")
    archive_parser.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    archive_parser.set_defaults(func=archive)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
