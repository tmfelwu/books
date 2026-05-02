# Reading Index

Dashboard generated from book frontmatter. Edit book files in `books/`, then run:

```bash
python3 scripts/books.py index
```

<!-- BOOKS_INDEX:START -->
## Summary

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

<!-- BOOKS_INDEX:END -->
