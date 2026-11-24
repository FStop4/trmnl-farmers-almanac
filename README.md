# TRMNL Farmer's Almanac

An old-time almanac screen for [TRMNL](https://trmnl.com) e-ink displays: days to frost, tonight's frost risk, what to plant now, the moon's sign with traditional planting ratings, and a seasonal chore.

## What it shows
- **Frost Reckoning:** days to last/first frost, frost-tonight alert, low and soil temperature, sunrise/sunset, growing-season bar.
- **The Moon's Sign:** phase, zodiac sign and element, traditional ratings for leafy crops, root crops and pruning, next full/new moon (approximate).
- **Plant Now / Coming Up:** crop tasks scheduled as weeks from your frost dates, with sowing depth and a soil-temperature check.
- **This Month:** one chore, plus a traditional weather saying.
- **Farm photos (optional):** two small photos flank the masthead on Full; one tall photo on Half Horizontal. Three photos rotate by day of year. Off unless `photo_base_url` is set.
- All four layouts (full, half horizontal, half vertical, quadrant). Scales to TRMNL X (1040x780 CSS px) via a zoom media query at 1.3x; X shows 5 plant items instead of 3.

## Setup
1. Publish the data site: run the **Build and publish frost data** workflow (Settings > Pages > Source: GitHub Actions).
2. In TRMNL, create a Private Plugin (Polling strategy). Paste the two URLs from `src/settings.yml` (replace `YOUR_GITHUB_USER`), one per line.
3. Paste each `src/*.liquid` into the matching layout tab and `shared.liquid` into Shared.
4. Add the custom fields from `src/settings.yml`.
5. Optional photos: after the workflow publishes, set `photo_base_url` to your site root (no trailing slash). Photos are served from `<site>/photos/`.

## Custom fields
| Field | Purpose | Default |
|---|---|---|
| `zip` | ZIP for the frost lookup | 65101 |
| `latitude`, `longitude` | Weather, soil temp, sun times | 38.58, -92.17 |
| `region_label` | Title bar text | nearest station |
| `photo_base_url` | Site root that serves `/photos/*.png`; blank hides photos | blank |
| `last_frost_override` / `first_frost_override` | Manual MM-DD | blank |

## Limits and caveats
- Refresh: once a day (1440 min). Frost JSON per ZIP is under 1 KB.
- Frost dates are 32 F / 50% probability averages from the nearest station (flagged `low_confidence` beyond 50 miles). Check your local forecast.
- Moon sign is approximate (about 1-2 degrees). Moon ratings are **traditional folklore, not science**.
- Crop timings, depths and soil minimums are typical planning values, not agronomic advice.
- Open-Meteo is free for non-commercial use (about 10,000 calls/day) and may rate-limit shared IPs. If its call fails, the weather lines are simply hidden.
- Photos are pre-dithered 1-bit PNGs at exact display size (128x60 masthead, 128x144 column). The Quadrant and Half Vertical layouts have no photos (no room). To change them, run `python3 photos/prep_photos.py A.jpg B.jpg C.jpg`.
- Hardiness zone is shown only if the frost JSON includes a `zone` field (not populated yet).

## Data and attribution
- NOAA NCEI 1991-2020 U.S. Climate Normals and U.S. Census ZCTA centroids.
- Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).
- Photos by Raphael Rychetsky, Dan Meyers and B S via [Unsplash](https://unsplash.com), used under the [Unsplash License](https://unsplash.com/license). They are not covered by this repo's MIT license. Cropped and dithered.
- Not affiliated with NOAA, TRMNL, Open-Meteo or The Old Farmer's Almanac.

## License
MIT
