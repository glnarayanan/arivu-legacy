# Collections

**Last Updated:** May 10, 2026
**Status:** Implemented for basic collection organization
**API:** `/api/collections/*`

Collections let users group bookmarks into named lists such as reading lists, research projects, or topic folders.

## Current Capabilities

- Create a collection with a validated name.
- List the current user's collections.
- Add a bookmark to a collection.
- Save a new bookmark directly into a collection by passing `collection_id`.
- Filter dashboard/bookmark/search results by `collection_id`.
- Remove deleted bookmarks from collections automatically.

The current implementation is intentionally small: collections are private to one user and store bookmark IDs.

## Data Model

Collection documents currently use this shape:

```json
{
  "id": "collection_123",
  "user_id": "user_123",
  "name": "AI Research",
  "bookmark_ids": ["bookmark_1", "bookmark_2"],
  "created_at": "2026-05-10T00:00:00+00:00"
}
```

`description`, cover images, colors, sharing settings, nesting, and smart rules are not part of the current backend model.

## API Endpoints

### GET /api/collections

Returns up to 100 collections owned by the authenticated user.

### POST /api/collections

Creates a collection.

```json
{
  "name": "AI Research"
}
```

Validation:

- Name is required.
- Maximum length is 100 characters.
- Allowed characters are word characters, spaces, hyphens, and periods.

### POST /api/collections/{collection_id}/add

Adds a bookmark ID to a collection using `$addToSet`, so repeated adds do not duplicate the ID.

```json
{
  "bookmark_id": "bookmark_123"
}
```

## Related Bookmark Behavior

`POST /api/bookmarks` accepts an optional `collection_id`. When present, the new bookmark is added to the target collection after creation.

`GET /api/bookmarks` accepts `collection_id` and returns bookmarks whose IDs are present in that collection.

`GET /api/search` also accepts `collection_id` and restricts search to bookmarks in that collection.

## Not Currently Implemented

The following ideas are not currently implemented and should not be documented as available behavior:

- Public or team collection sharing
- Smart or dynamic collections
- Nested collections
- Collection descriptions, colors, covers, icons, or templates
- Collection activity feeds
- Drag-and-drop ordering

## Troubleshooting

### Collection does not appear

- Confirm the request is authenticated as the same user who created it.
- Refresh the app shell so the sidebar reloads collections.
- Check backend logs for validation errors.

### Cannot add a bookmark

- Confirm the collection ID belongs to the current user.
- Confirm the bookmark ID exists and belongs to the current user.
- Re-adding the same bookmark is a no-op because the backend uses `$addToSet`.

## References

- API reference: [documentation/api/README.md](../api/README.md#collections-endpoints)
- Architecture: [documentation/architecture.md](../architecture.md)
