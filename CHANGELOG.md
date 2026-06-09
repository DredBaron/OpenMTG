# Changelog

## v1.8.0

### Added

- **Showroom** - A public display page for each user's collection highlights, suitable for a TV, tablet, or kiosk.
- Included new `README.md` badges for Architecture, Scryfall, Last Commit + Release, and CI Pass/Fail status.
- `GET /showroom/display/{username}` - Public endpoint showing a user's public decks and cards. Capitalization-agnostic.
- `/showroom/display/:username` - Public display page where decks and cards are shown.
- `/showroom/edit/:username` - Owner-facing management page showing what is currently on display with the ability to remove items.
- Per-deck Showroom toggle on the Decks page marks a deck as public and adds it to the owner's display.
- Per-card Showroom toggle on the Collection page adds individual entries to the owner's display.
- S/M/L card size toggle on both Showroom pages, persisted per-browser and shared between the two pages.
- Showroom navigation link added to sidebar and mobile menu.
- Alembic migration `b2c3d4e5f6a7` adding `in_showroom` boolean column to `collection_entries`.

### Changed

- Version bumped from 1.7.0 to 1.8.0 within `constants.py`.
- Redirected `dependabot.yml` to dev branch instead of main.

### Fixed

- Updated `nginx.conf` to include endpoints for `/openapi.json` and `/docs/api` for future API-based development.

## v1.7.0

### Added

- **Multi-currency support** - Admins can now add custom currencies (e.g. CAD, AUD, GBP) via the Admin panel. Rates are fetched automatically from Frankfurter and refreshed after each Scryfall price cycle. Admins can select any configured currency from the User Account settings for any user.
- `backend/markets.py` - Central currency registry allowing each market to define its symbol, display name, Scryfall adapter, and capabilities in one place.
- `backend/services/market_scryfall.py` - Scryfall price adapter which maps Scryfall API price keys to database column names.
- `backend/services/exchange_rates.py` - Frankfurter integration for validating and batch-refreshing stored exchange rates.
- `GET /currencies` - Public endpoint; frontend fetches all currency metadata (symbol, rate, conversion base) at runtime instead of hardcoding.
- `GET|POST|PATCH|DELETE /admin/currencies` - Admin CRUD for custom currencies. New codes are validated against Frankfurter before being accepted.
- `useCurrency()` hook - Replaces scattered `user?.preferred_currency` reads across all pages; provides `currency`, `market`, and `markets` to any component that needs them.
- `ConvertedCurrency` database model and Alembic migration.
- New 'SM', 'MD', and 'LG' buttons to Grid views for Decks and Wishlist which changes the visible card size.

### Changed

- Price extraction in `scryfall.py` and `price_refresh.py` now delegates to the market adapter (`ScryfallMarket.extract_prices()`), eliminating all hardcoded `if prices.get("usd")` chains.
- `currency.js` - `formatPrice` and `resolvePrice` are now market-aware. Custom currencies apply a stored exchange rate against USD automatically on the frontend.
- Collection stats endpoint now supports custom currencies via DB rate lookup. All price expressions are multiplied by the exchange rate server-side.
- Wishlist price history response is now dynamic across all markets rather than hardcoded to USD/EUR fields.
- `set_currency` in auth now validates the chosen code against `MARKETS` and the database before accepting it.
- `PRICE_FIELDS` constant removed from `constants.py`. All callers now derive field names from `MARKETS`.
- All JSX inline styles with more than one property moved to named CSS classes in `index.css`. Dynamic values are passed via CSS custom properties (`--bar-w`, `--bar-bg`, `--tile-accent`).

### Fixed

- `add_to_wishlist` endpoint was calling `_serialize(entry, currency)` after `_serialize` signature was updated to take one argument, causing a 500 on all POST `/wishlist` requests.

### Removed

- Server-side `price_met` computation removed from wishlist serializer, field is now computed on the frontend where currency context is available.
- Removed CSS class `.wishlist-page` limiting Wishlist width to a specific pixel count; Wishlist is now adopts full screen width.

---

## v1.6.2

### Fixed

- Deleting a user now correctly removes their collection, deck, and wishlist entries; previously caused a 500 error due to missing cascade delete on the User-CollectionEntry, User-Deck, and User-WishlistEntry relationships

### Changed

- Mobile navigation replaced with a hamburger menu (☰) in the top-right; tapping it opens a full-width dropdown with page names and Logout at the bottom.
- Long usernames no longer push nav items off-screen, as usernames are no longer rendered in Mobile view.
- User Management table unified for mobile and desktop; Less useful Email and Created columns are hidden on narrow screens rather than switching to a separate card layout

---

## v1.6.1

### Added

- Collections: page GOTO input replaces static page indicator - type a page number and press Enter to jump directly

### Changed

- Wishlist list view on mobile: two-row card layout (name + price on top, set code + action buttons below); set name abbreviated to 3-letter code; History button restored
- User Management on mobile: per-user cards with a status row (name, role, status) and an action row (currency, admin toggle, reset password, disable, delete); desktop table unchanged
- Stats Top 10 Most Valuable Cards on mobile: two-row card list instead of the overflowing table
- List/Grid toggle order standardized to List first across all pages (Decks and Wishlist)
- Deck and Wishlist List/Grid view preference is now persisted per-browser; each deck remembers its own setting independently

### Fixed

- Deck view total and per-card prices now respect the user's preferred currency instead of always showing USD
- Stats page loading spinner used incorrect CSS class (`isLoading` → `loading`)

### Removed

- Stats: removed local duplicate of `formatPrice` and `CURRENCY_SYMBOLS` in favour of the shared `currency.js` utility

---

## v1.6.0

- Added grid view to Deck Viewer (default), with card images, quantity badges, and hover actions
- Added card image viewer to Deck Viewer (both grid and list views)
- Overhauled "Add Card to Deck"; card image thumbnails in search results, owned/non-owned toggle, zone dropdown (Mainboard/Sideboard/Commander), and set picker for non-owned cards
- Added "Edit Card" modal to Deck Viewer
- Added Deck Analysis including Mana Curve, Color Distribution, Card Types, Avg. CMC, and Rarity breakdown
- Two-step delete confirmation on card removal in Decks to prevent accidental deletes
- Updated API/Application version handling in all background files involving API calls
- Added Wishlist page
- Added List and Grid views to Wishlist page
- Pushed all API calls to a single rate-limited caller function to enforce Scryfall's 2 req/sec rate cap
- Set up API call prioritizer to push frontend user activity through API caller function first
- Deck Edit modal now supports changing a card's printing via Set Picker
- Wishlist cards are prioritized in background price cache refresh
- Unified Add Card button sizes across Wishlist, Decks, and Deck Detail pages
- Fixed deck card update endpoint returning a 500 instead of 404 on an invalid Scryfall ID
- Fixed Admin page delete confirmation using browser native dialog instead of the app's modal
- Set Picker dropdown now renders over modals using fixed positioning rather than being clipped

---

## v1.5.1

- Bump eslint from 9.39.4 to 10.3.0 in /frontend
- Update pytest-mock requirement from >=3.14 to >=3.15.1 in /backend
- Update pytest requirement from >=8.0 to >=9.0.3 in /backend
- Update anyio requirement from >=4.0 to >=4.13.0 in /backend
- Update httpx requirement from >=0.27 to >=0.28.1 in /backend
- Bump @eslint/js from 9.39.4 to 10.0.1 in /frontend

---

## v1.5.0

- Corrected use of `_HEARTBEAT_JITTER` to the correct `_HEARTBEAT_INTERVAL` for telemetry timing.
- Admin panel now shows a per-user currency dropdown that takes effect immediately without a page reload.
- Scryfall service now fetches and stores all four price fields: `price_usd`, `price_usd_foil`, `price_eur`, `price_eur_foil`.
- Currency selection is driven by a `PRICE_FIELDS` registry in `constants.py`, making future currencies (e.g. CAD) a one-line addition.

---

## v1.4.2

- Added a check to see date of creation for current UUID, and re-generate UUID
if >60 days.
- Added a check for timestamp of last message compated to current message, and
delay heartbeat by an hour if within 23 hours of previous heartbeat.
- Added a dropdown in the Settings menu next to the Telemetry toggle to see the
last-sent telemetry packet in its entirety.
- Added a data retention statement in the README.md and Wiki.
- Lowered timestamp accuracy to round to the nearest minute.
- Replaced invisible Telemetry tab with disabled message when `NOTEL=true` is set.

---

## v1.4.1

- Corrected duplicated 'Uvicorn' processes in 'supervisord.conf'

---

## v1.4.0

- Added optional usage telemetry to Settings page (Opt-in only, see README.md)
- Corrected missing icons from mobile web view

---

## v1.3.4

- Updated eslint/js from 9.39.4 to 10.0.1
- Updated lucide-react from 0.577.0 to 1.7.0

---

## v1.3.3

- Modified `httpx` usage in `price_refresh.py` and `scryfall.py` to use existing HTTP handshake instead of creating a new
one for every card requests. DNS requests for `api.scryfall.com` should fall dramatically now.
- Updated all `utcnow()` calls to proper `now(timezone.utc)` calls.
- Fixed SQLite thread safety and suppressed test scheduler startup noise in `conftest.py` and `database.py`.

---

## v1.3.2

- Removed known remainder of AI code. Repository has been cleaned and is now 100% human-developed. Summary of major changes below

### Collection.jsx

- Removed unused Search icon and SetPicker import.
- Properly split components `AddCardModal`, `EditModal`, and `CardImageModal` into imported components.
- Replaced complicated `const onMobile = /Mobile/i.test(navigator.userAgent)` with simpler `const isMobile = useIsMobile()` hook.
- All `onMobile` references changed to `isMobile`.
- Replaced all outdated `window.confirm()` calls with proper `setConfirmAction({ message, onConfirm })` calls.
- Replaced color filter logic `getCardCastingColors(entry.card)` with `(entry.card.colors || '').split('')` to use the colors
string already stored from Scryfall API cache instead of parsing `mana_cost` in frontend every time.

### Layout.jsx

- Replaced `const isMobile = /Mobile/i.test(navigator.userAgent)` with `import { useIsMobile } from '../hooks/useIsMobile'`.
- Added `const isMobile = useIsMobile()` inside the component body, for dynamic pointer type changes.

---

## v1.3.1

- Placeholder UI template has been removed. Dev-intended UI is now in place.
- Changed ruling link from [Gatherer](https://gatherer.wizards.com/) to [Scryfall](https://scryfall.com/).
- Added backend tests.

---

## v1.3.0

- Added clickable card images in Collection which blows the card image to full size, and provides a link to the `gatherer.wizards.com` ruling for that card.
- Added multi-card selection for batch deleting from Collection.
- Improved the mobile webpage rendering.
- Re-ordered and improved Collection filters.
- Implemented adding and sorting cards by 'Favorite'.
- Combined Docker images `openmtg-backend`, `openmtg-frontend`, and `nginx` into a single Docker image `openmtg`.
- Modified how Stats page shows pie charts to help with rendering small percentages.

---

## v1.2.0

- Added CHANGELOG.md.
- Added CREDITS.md.
- Edited Collection page to use pagination through a drop-down menu.
- Corrected CSV and JSON export functions.
- Fixed Deck building page occasionally not working.
- Added Deck Moxfield and JSON export buttons.
- Added Sorting and Filtering features to Collection page.
- Corrected tab names to reflect which tab the user is on, as well as the project name.
- Added new Favicon, credited to [Faithtoken](https://game-icons.net/1x1/faithtoken/card-pick.html) and licensed under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).
- Updated 'Database Cache Freshness Bar' to make it a live updating element instead of a static one.

---

## v1.1.0

- Edited `frontend/Dockerfile` to add `RUN apk upgrade --no-cache`, clearing known libexpat and zlib CVE's.
- Edited `backend/Dockerfile` to add `RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/* && pip install --upgrade pip`, clearing CVE-2025-8869.
- Created `nginx/Dockerfile` to build nginx instead of pulling image.
- Replaced `ecdsa` with `PyJWT` in `security.py`, clearing ecdsa CVE-2024-23342.
