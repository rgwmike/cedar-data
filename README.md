# cedar-data

Reference data for the Cedar humidor app. Plain JSON, read by the app over HTTPS from this repository's `main` branch.

| File | What it holds | Written by |
| --- | --- | --- |
| `manifest.json` | Version, hash, size and date of every other file — the app reads this first | every job that changes a file |
| `catalog.json` | Cigar lines: brand, line, origin, wrapper/binder/filler, strength, price range, vitolas, aliases | by hand or a Cowork task |
| `sources.json` | For each line, the page at each retailer where its prices are listed | built by web search, kept up as lines are added |
| `wanted.json` | The lines the monthly price task keeps fresh | by hand for now |
| `prices.json` | Per line and vitola: low / median / high single price, retailer, URL, fetched-at | the monthly price task |

Nothing here is personal: no humidor contents, no sessions, no reviews.
