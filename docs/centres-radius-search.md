# Diagnostic Centre Radius Search

## Endpoint

`POST /api/v1/centres/search`

JSON request body:

- `latitude`: centre latitude in degrees, from `-90` to `90`.
- `longitude`: centre longitude in degrees, from `-180` to `180`.
- `radius`: search radius in kilometres, greater than `0` and at most `20,000`.
- `test_id` (optional string): UUID text identifying a test; return only centres that actively offer it.
- `sort_by` (optional): `distance` (default) or `test_price`.
- `sort_order` (optional): `asc` (default) or `desc`.
- `view` (optional): `list` (default) or `map`. List results are paginated; map results include all matches.
- `page` (optional): one-based page number, default `1`.
- `page_size` (optional): number of centres per page, from `1` to `100`, default `20`.

Example request:

```json
{
	"latitude": 51.5072,
	"longitude": -0.1276,
	"radius": 10,
	"test_id": "00000000-0000-0000-0000-000000000000",
	"sort_by": "test_price",
	"sort_order": "asc",
	"view": "list",
	"page": 1,
	"page_size": 20
}
```

`test_id` is required when `sort_by` is `test_price`. The response uses the standard API envelope. `data.items` contains matching diagnostic centres in the requested sort order; each centre keeps the existing serialized model shape. `data.total` is the number of matches. For `view: "list"`, `data.pagination` contains `page`, `page_size`, and `total_pages`. For `view: "map"`, all matches are returned and `data.pagination` is `null`.

## How It Works

1. The search area is converted to a geohash grid cover. The selected precision is between 1 and 8, matching the precision-8 hashes stored for diagnostic centres. The cover includes neighboring cells around the search bounds, including longitude wraparound at the international date line and searches that reach a pole. If a fine cover would contain more than 256 cells, a coarser precision is used.
2. The repository selects centres whose stored geohashes start with one of the cover hashes. This finds candidate rows without treating the query point's single geohash as the whole search area.
3. Each candidate is checked using its latitude and longitude with the Haversine great-circle distance. Only centres at or below the requested radius are returned, so the geohash grid is only a candidate filter and does not define the radius boundary.
4. Matching centres are sorted by distance, or by the selected test's price when requested.
5. List results are sliced into pages after filtering and sorting. Map results return the full matching set.

Coordinates are validated by FastAPI. The radius is expressed in kilometres, not metres.
