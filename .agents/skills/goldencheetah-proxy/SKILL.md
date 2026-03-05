---
name: goldencheetah-proxy
description: Builds web apps that access local GoldenCheetah cycling/sports data via the goldencheetah-proxy CORS proxy. Provides proxy installation, GoldenCheetah API endpoints, connection flow with explicit user approval, and error handling patterns. Use when building apps that read GoldenCheetah data, or when the user mentions GoldenCheetah.
---

# GoldenCheetah Proxy

Local CORS proxy that lets web apps read [GoldenCheetah](https://www.goldencheetah.org/) data at `http://localhost:12022`. Read-only (GET requests only). Hardcode this URL — it is the default and does not need to be configurable.

## Connect button

Every app **must** have an explicit "Connect to GoldenCheetah" button. Do not auto-connect on page load — the proxy shows a native approval dialog on first connection from a new origin, which requires a user-initiated action.

1. Show a connect button (and setup instructions — see [Installation](#installation))
2. On click, fetch `GET http://localhost:12022/` to list athletes
3. On success, hide the connect UI and show the app
4. If multiple athletes, show a selector; if one, auto-select

```js
const PROXY = "http://localhost:12022";

async function connect() {
  const res = await fetch(`${PROXY}/`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const athletes = await res.json(); // array of athlete names
}
```

## API endpoints

The GoldenCheetah API has [minimal documentation](https://github.com/GoldenCheetah/GoldenCheetah/blob/master/doc/user/rest-api.txt). Response schemas are not fully documented — test against a running instance and inspect actual responses to verify the shape of the data.

| Endpoint | Returns | Notes |
|---|---|---|
| `GET /` | `["Athlete1", "Athlete2"]` | List athlete names |
| `GET /<athlete>?metrics=...&metadata=...` | JSON array of rides | List activities with selected metrics |
| `GET /<athlete>/activity/<filename>?format=csv` | CSV timeseries | Activity data for plotting |
| `GET /<athlete>/meanmax/bests?series=...` | JSON mean-max data | Historical best curve |

### Listing activities

```
GET /<athlete>?metrics=average_power,normalized_power,intensity_factor,tss,average_hr,average_cad&metadata=Sport
```

Metrics and metadata are comma-separated. Returns JSON with one object per activity, each containing `filename`, `date`, and the requested fields.

### Activity timeseries

```
GET /<athlete>/activity/<filename>?format=csv
```

Returns CSV with columns like `secs`, `watts`, `hr`, `cad`, `kph`, `alt`, `km`. Not all columns are present for every activity.

### Mean-max curves

```
GET /<athlete>/meanmax/bests?series=power
```

Series options: `power`, `hr`, `cadence`, `speed`, `np` (normalized power).

## Error handling

Robust error handling is critical — the proxy and GoldenCheetah are local services that may not be running.

**Network error** (fetch fails entirely): The proxy is not running. Tell the user to run `goldencheetah-proxy` in a terminal.

**HTTP 502**: The proxy is running but GoldenCheetah is not. Tell the user to open GoldenCheetah and enable the API (Settings → General → Integration → Enable API Web Services).

**HTTP 403**: The user denied this origin in the proxy's approval dialog. Tell them to restart the proxy and approve when prompted.

Principles:
- Always show **what went wrong** and **what to do** to fix it
- Never show raw error objects or stack traces
- Keep the connect button visible and re-clickable after errors
- Distinguish "proxy not running" (network error) from "GoldenCheetah not running" (502)

## Installation

Apps should include setup instructions so users know how to install and run the proxy, but keep them out of the way — users only need them once. Use a collapsible section, a help link, or similar pattern so they don't clutter the main UI. Fetch the install commands from the [README](https://github.com/SweatStack/goldencheetah-proxy/blob/main/README.md) rather than hardcoding them. Users also need to enable the GoldenCheetah API: Settings → General → Integration → Enable API Web Services.
