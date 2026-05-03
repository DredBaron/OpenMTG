# Changelog

## v1.5.0

- Corrected use of `_HEARTBEAT_JITTER` to the correct `_HEARTBEAT_INTERVAL` for telemetry timing.
- Admin panel now shows a per-user currency dropdown that takes effect immediately without a page reload
- Scryfall service now fetches and stores all four price fields: `price_usd`, `price_usd_foil`, `price_eur`, `price_eur_foil`.
- Currency selection is driven by a PRICE_FIELDS registry in `constants.py`, making future currencies (e.g. CAD) a one-line addition.

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

## v1.4.1

- Corrected duplicated 'Uvicorn' processes in 'supervisord.conf'

## v1.4.0

- Added optional usage telemetry to Settings page (Opt-in only, see README.md)
- Corrected missing icons from mobile web view

## v1.3.4

- Updated eslint/js from 9.39.4 to 10.0.1
- Updated lucide-react from 0.577.0 to 1.7.0

## v1.3.3

- Modified `httpx` usage in `price_refresh.py` and `scryfall.py` to use existing HTTP handshake instead of creating a new
one for every card requests. DNS requests for `api.scryfall.com` should fall dramatically now.
- Updated all `utcnow()` calls to proper `now(timezone.utc)` calls.
- Fixed SQLite thread safety and suppressed test scheduler startup noise in `conftest.py` and `database.py`.

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

## v1.3.1

- Placeholder UI template has been removed. Dev-intended UI is now in place.
- Changed ruling link from [Gatherer](https://gatherer.wizards.com/) to [Scryfall](https://scryfall.com/).
- Added backend tests.

## v1.3.0

- Added clickable card images in Collection which blows the card image to full size, and provides a link to the `gatherer.wizards.com` ruling for that card.
- Added multi-card selection for batch deleting from Collection.
- Improved the mobile webpage rendering.
- Re-ordered and improved Collection filters.
- Implemented adding and sorting cards by 'Favorite'.
- Combined Docker images `openmtg-backend`, `openmtg-frontend`, and `nginx` into a single Docker image `openmtg`.
- Modified how Stats page shows pie charts to help with rendering small percentages.

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
