# Books Repository Instructions

Be extremely precise. Preserve the Markdown/frontmatter structure because this repository is intended to be queried by LLM agents and simple scripts.

## Repository Shape

- `books/` contains one Markdown file per book.
- `index.md` is the human-readable dashboard for current reading, recommended books, recently added books, finished books, paused books, wishlist items, and the full library.
- `templates/book.md` is the template for new book files.
- `scripts/books.py` validates book files and regenerates the index.
- `AGENTS.md` must point to this file.

## Book File Rules

Every book file must live in `books/` and use a lowercase kebab-case filename:

```text
books/book-title-author.md
```

Every book file must start with YAML-style frontmatter using this schema:

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

Allowed `status` values:

- `reading`
- `finished`
- `archived`
- `paused`
- `wishlist`
- `recommended`

Date rules:

- Use `YYYY-MM-DD`.
- `added` is required for every book file and means the date this repository record was created.
- `started` is required for `reading`, `finished`, `archived`, and `paused`.
- `finished` is required when `status: finished`.
- `archived` is required when `status: archived`.
- `recommended_on` is optional and means the date someone recommended or mentioned the book.
- Leave unknown optional values blank rather than guessing.

Metadata rules:

- `title`, `author`, `published`, `publisher`, `pages`, `subjects`, `source`, and `isbn` are public bibliographic metadata.
- `status`, `added`, `started`, `finished`, `archived`, `rating`, `tags`, `format`, `reading_location`, `recommended_by`, `recommended_on`, and `recommendation_note` are personal tracking metadata.
- When creating a book, search online for the likely book and use reputable bibliographic sources such as the publisher, Open Library, WorldCat, a national library catalog, or Google Books.
- Prefer publisher metadata when available for edition-specific fields such as `publisher`, `published`, `pages`, and `isbn`.
- Put the URL used for bibliographic metadata in `source`.
- Fill public metadata only when it is verified by the source used. Leave conflicting or uncertain fields blank and note the uncertainty under `## Book Info`.
- Do not infer personal reading metadata from online sources.

Tracking rules:

- `added` and `started` are different. Use `added` for when the book file entered this repository. Use `started` only when the user has begun reading.
- `status: recommended` means someone mentioned or recommended the book, but the user has not committed it to the wishlist and has not started reading it.
- `status: wishlist` means the user intentionally wants to read the book.
- If a book is recommended and the user also says they want to read it, use `status: wishlist` and still fill `recommended_by` / `recommended_on` when known.
- If a book is recommended and the user has already started reading it, use `status: reading`, fill `started`, and still preserve the recommendation fields.
- `format` records the reading format, for example `epub`, `paperback`, `hardcover`, `audiobook`, `pdf`, or `web`.
- `reading_location` records where the user reads or accesses it, for example `Kindle`, `Apple Books`, `Libby`, `Audible`, `local EPUB`, a store/library name, or a filesystem path if provided.

Content rules:

- Keep the first Markdown heading as `# Title`.
- Add sourced bibliographic context under `## Book Info`.
- Add notes under `## Notes`.
- Add notable quotes under `## Quotes`.
- Add follow-up thoughts under `## Ideas`.
- Add dated reading events under `## Timeline`.
- When appending a note, preserve existing notes and add a new dated bullet.

## Common Agent Tasks

When the user says "add a book":

- Create a new file in `books/` from `templates/book.md`.
- Search online for the likely book.
- Resolve title/author ambiguity before writing the file. If the user gives a slightly wrong title and the intended book is clear, use the verified title and mention the correction.
- Fill public bibliographic fields from the best source found.
- Fill personal reading fields only from user-provided facts or the local date rule below.
- Set `added` to today's local date unless the user provides a different date for when the record should be added.
- If the start date is not provided and the user implies they are starting now, use today's local date.
- Add a short sourced bullet under `## Book Info` naming the metadata source and edition when applicable.
- Run `python3 scripts/books.py validate`.
- Run `python3 scripts/books.py index`.

When the user says someone recommended, mentioned, or told them about a book:

- Create the book file if it does not already exist.
- Search online for the likely book and fill public bibliographic fields from the best source found.
- Use `status: recommended` unless the user says they want to read it, are reading it, have finished it, or want another explicit status.
- Set `added` to today's local date unless the user provides a different added date.
- Fill `recommended_by` with the person, podcast, article, video, class, or source that recommended it when known.
- Fill `recommended_on` with the date of the recommendation when provided; otherwise use today's local date if the recommendation is happening now.
- Put any extra recommendation context in `recommendation_note`.
- Run `python3 scripts/books.py validate`.
- Run `python3 scripts/books.py index`.

When the user says "add a note to a book":

- Find the closest matching book in `books/`.
- Append the note under `## Notes` as a dated bullet.
- Do not rewrite unrelated content.
- Run `python3 scripts/books.py validate`.
- Run `python3 scripts/books.py index`.

When the user says "mark a book as finished":

- Run `python3 scripts/books.py finish "<book>"`.
- Pass `--date YYYY-MM-DD` if the user provides a finish date.
- Run `python3 scripts/books.py validate`.
- Run `python3 scripts/books.py index`.

When the user says "archive a book":

- Run `python3 scripts/books.py archive "<book>"`.
- Pass `--date YYYY-MM-DD` if the user provides an archive date.
- Preserve notes and explain that archived means intentionally stopped or removed from active tracking.
- Run `python3 scripts/books.py validate`.
- Run `python3 scripts/books.py index`.

When the user asks reading-history questions:

- Prefer using `scripts/books.py` for deterministic answers.
- If a query is not covered by the script, inspect frontmatter directly and state the exact assumptions used.

Useful commands:

```bash
python3 scripts/books.py validate
python3 scripts/books.py index
python3 scripts/books.py list --status reading
python3 scripts/books.py list --status recommended
python3 scripts/books.py recent-added --limit 20
python3 scripts/books.py stale --days 120
python3 scripts/books.py read-since 2025-05-03
python3 scripts/books.py finish "Book Title"
python3 scripts/books.py archive "Book Title"
```
