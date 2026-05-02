# Reading Desk

A working map of the library. The tables are live Dataview views over the frontmatter in `books/`; this page itself is intentionally hand-edited.

## Now Reading

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, category AS Category, started AS Started, format AS Format, reading_location AS Location
FROM "books"
WHERE status = "reading"
SORT started DESC, title ASC
```

## China Shelf

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, status AS Status, added AS Added, recommended_by AS "Recommended By", subjects AS Subjects
FROM "books"
WHERE category = "nonfiction" AND contains(regions, "china")
SORT status ASC, added DESC, title ASC
```

## Fiction

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, status AS Status, added AS Added, recommended_by AS "Recommended By", rating AS Rating
FROM "books"
WHERE category = "fiction"
SORT status ASC, added DESC, title ASC
```

## Nonfiction

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, status AS Status, regions AS Regions, subjects AS Subjects, added AS Added
FROM "books"
WHERE category = "nonfiction" AND !contains(regions, "china")
SORT status ASC, added DESC, title ASC
```

## Recommended

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, category AS Category, regions AS Regions, recommended_by AS "By", recommended_on AS "On", recommendation_note AS Note
FROM "books"
WHERE status = "recommended" OR recommended_by
SORT recommended_on DESC, added DESC, title ASC
```

## Wishlist

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, category AS Category, regions AS Regions, added AS Added, recommended_by AS "Recommended By"
FROM "books"
WHERE status = "wishlist"
SORT added DESC, title ASC
```

## Recently Added

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, category AS Category, regions AS Regions, status AS Status, added AS Added
FROM "books"
WHERE added
SORT added DESC, title ASC
LIMIT 20
```

## Recently Finished

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, category AS Category, finished AS Finished, rating AS Rating
FROM "books"
WHERE status = "finished"
SORT finished DESC, title ASC
LIMIT 20
```

## Paused

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, category AS Category, started AS Started, regions AS Regions
FROM "books"
WHERE status = "paused"
SORT started DESC, title ASC
```

## Library Counts

```dataview
TABLE length(rows) AS Count
FROM "books"
GROUP BY status AS Status
SORT Status ASC
```

```dataview
TABLE length(rows) AS Count
FROM "books"
GROUP BY category AS Category
SORT Category ASC
```

## Full Library

```dataview
TABLE WITHOUT ID file.link AS Book, author AS Author, category AS Category, regions AS Regions, status AS Status, added AS Added, started AS Started, finished AS Finished, rating AS Rating
FROM "books"
SORT category ASC, added DESC, title ASC
```
