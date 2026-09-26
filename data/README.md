# Data directory

`market_history.csv` is the version-controlled public-source market snapshot used to build the bundled website model.

### Benchmark mapping

- Diesel → Gasoil 10 ppm FOB Arab Gulf
- Petrol → RON92 FOB Arab Gulf
- Octane → RON95 FOB Arab Gulf

The Alghaf Marine archive describes these as indicative/non-binding historical market indications rather than licensed assessments, commercial offers or live executable quotes.

### FX history

The modeled historical FX series uses the Bangladesh Bank-attributed daily midpoint exposed by Fexant. The direct Bangladesh Bank reference-rate page is retained as the preferred current official source and as a health-check path in the updater.

### Official prices

`official_prices.csv` is a version-controlled event dataset. Every event carries its public source URL and source tier. New official events should be added deliberately rather than scraped blindly from a fragile page.

### Browser model files

`model.json` is the structured model output.

`model.js` contains the same output as a browser-safe bundled snapshot so the site can run directly from `index.html` on Windows without a browser-side JSON `fetch()` requirement.

### Live refresh

GitHub Actions runs `scripts/update_market_data.py` online. The updater requires a minimum source-history length and fails on structural problems instead of replacing a valid dataset with a suspiciously short snapshot.
