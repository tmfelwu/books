# Books

Personal reading log and book-notes repository. Each book has one Markdown file with structured frontmatter plus free-form notes, and `index.md` is a Dataview dashboard.

## Structure

```text
books/
  one-book-per-file.md
templates/
  book.md
scripts/
  books.py
index.md
CLAUDE.md
AGENTS.md
```

## Add A Book

Create a new Markdown file in `books/` using `templates/book.md`, verify public bibliographic metadata online, fill the frontmatter, then run:

```bash
python3 scripts/books.py validate
python3 scripts/books.py index
```

## Query The Library

```bash
python3 scripts/books.py list
python3 scripts/books.py list --status reading
python3 scripts/books.py list --status recommended
python3 scripts/books.py recent-added --limit 20
python3 scripts/books.py stale --days 120
python3 scripts/books.py read-since 2025-05-03
python3 scripts/books.py finish "Book Title"
python3 scripts/books.py archive "Book Title"
```

## Frontmatter Schema

```yaml
---
title: "Book Title"
author: "Author Name"
status: reading
added: YYYY-MM-DD
started: YYYY-MM-DD
finished:
archived:
rating:
tags: []
format:
reading_location:
recommended_by:
recommended_on:
recommendation_note:
published:
publisher:
pages:
subjects: []
source:
isbn:
---
```

Allowed statuses are `reading`, `finished`, `archived`, `paused`, `wishlist`, and `recommended`.
