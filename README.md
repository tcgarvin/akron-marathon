# Akron Marathon replay

Interactive animation of the Akron Marathon: every bib moving around the
course, driven by chip split times, with a time slider and a "find my bib"
highlight.

## How it works (plan)

1. **Course line** — a GPX/GeoJSON of the route, resampled to a polyline with
   cumulative distance so any distance-along-course maps to a lat/lon.
2. **Timing mats** — each mat is a known distance along the course
   (start, 5K, 10K, half, 30K, 35K, finish or whatever Akron publishes).
3. **Chip splits** — per bib, the clock time at each mat. Position at time
   `t` is the linear interpolation of distance between the two mats that
   bracket `t`. Missing splits are skipped (interpolate across the gap).
   Before the start mat and after the finish mat the runner is parked.
4. **Viewer** — a static web page: map (Leaflet or plain canvas over an
   image of the course), one dot per bib, a slider for race clock, play /
   pause / speed, a bib search that highlights one runner and shows their
   splits. Everything is client-side; data ships as one compact JSON.

## Layout

    data/       raw results as downloaded, course GPX
    tools/      Python: scrape/parse results, build the compact JSON
    web/        the static viewer

## Open questions

- Where the split data comes from (results site, whether it publishes
  intermediate splits, whether scraping is allowed).
- Which year, and marathon only or the half and relay too.
