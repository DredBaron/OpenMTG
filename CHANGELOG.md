# Changelog

## v1.3.2

- Removed known remainder of AI code. Repository has been cleaned and is now 100% human-developed. Summary below

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

### models.py
- All ORM classes were moved into `models/__init__.py` to turn `models.py` into a backwards-compat shim, turning clunky
`models.models as models` to `import models`.

### main.py
- Replaced outdated `@app.on_event("startup")` with `asynccontextmanager` function passed directly to the FastAPI constructor.

### admin.py
- `list_users` and `create_user` given route-level `dependencies=[Depends(require_admin)]`, but `update_user` and `delete_user`
kept a named `current_admin: models.User = Depends(require_admin)` parameter because they actively use it to prevent an admin
from modifying their own account.

### settings.py
- Modified to only check for `require_admin`, as there are no uses for `current_user` in the body.

### cards.py
- `_` dependency was removed from every function signature and moved to the router constructor.

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

## V1.1.0

- Edited `frontend/Dockerfile` to add `RUN apk upgrade --no-cache`, clearing known libexpat and zlib CVE's.
- Edited `backend/Dockerfile` to add `RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/* && pip install --upgrade pip`, clearing CVE-2025-8869.
- Created `nginx/Dockerfile` to build nginx instead of pulling image.
- Replaced `ecdsa` with `PyJWT` in `security.py`, clearing ecdsa CVE-2024-23342.
