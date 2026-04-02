# OpenMTG

Self-hosted MTG card inventory server with multi-account support, collection tracking, deck building, statistics, and import/export. Built with FastAPI and React, deployable in minutes with Docker.

---

## Features

- **Collection Management** — Add cards by name with fuzzy Scryfall search, track quantity, condition, foil, language, price, and set printing
- **Deck Builder** — Build decks with mainboard, sideboard, and commander zones
- **Statistics** — Visual breakdowns of your collection by rarity, color, type, condition, set, and estimated value
- **Price Tracking** — Automatic price refreshes from Scryfall with configurable intervals and rate limiting
- **Multi-Account** — Admin-managed user accounts; each user has their own isolated collection
- **Import / Export** — Export collections and decks in multiple formats
- **Quick Add** — Fast card entry with live Scryfall lookup and set picker
- **Favorites** — Mark and sort cards with a 'Favorite' button

---

## Roadmap

- **Showroom** — Add Showroom page for showing off individual cards or whole decks (not favorites) between users

---

## Stack

| Layer | Technology |
|---|---|
| Application | Python 3.12, FastAPI, SQLAlchemy, Alembic, React, Vite, TanStack Query |
| Database | PostgreSQL 16 |
| Reverse Proxy | Nginx |
| Container | Docker + Docker Compose |

---

## Quick Start

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

### 1. Pull the image

```bash
docker pull ghcr.io/dredbaron/openmtg:latest
```

### 2. Create your environment file

Create the file and fill in your values:

```bash
cat <<EOF > .env
POSTGRES_DB=openmtg
POSTGRES_USER=openmtg
DB_PASSWORD=your_secure_password_here
JWT_SECRET=your_long_random_secret_here
DATA_PATH=./data
CONFIG_PATH=./config
EOF
```

> **Tip:** Generate a strong JWT secret with `openssl rand -hex 32`

### 3. Create your docker file

Use the default `docker-compose.yml` as a template for this docker file.

### 4. Start the stack

```bash
docker compose up -d
```

OpenMTG will be available at **http://localhost:8080**

### 5. First-time setup

On first launch you will be prompted to create an admin account. After that, only admins can create additional user accounts.

For a more detailed install guide, see the [Install Guide](https://github.com/DredBaron/OpenMTG/wiki/Installation) in the Wiki.

---

## Updating

```bash
docker compose pull
docker compose up -d
```

Database migrations run automatically on startup.

---

## Opt-In Telemetry

As of v1.4.0, OpenMTG includes an optional telemetry feature to help estimate active usage. When enabled, the app generates a random anonymous ID and sends a once-daily heartbeat containing only that ID and a timestamp. No personally identifiable information is collected, and participation is entirely voluntary. The ID is created only after opting in and is deleted if you opt out. Telemetry data is used solely for development purposes and is never shared or sold.

To disable telemetry prompts entirely, edit your .env file to add the following line:

```bash
NOTEL=true
```

For additional details in removing all future telemetry-based features, please see the [Telemetry Wiki](https://github.com/DredBaron/OpenMTG/wiki/Telemetry) page.

## Configuration

All configuration is done via the `.env` file or the admin **Settings** panel in the UI.

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_DB` | Database name | `openmtg` |
| `POSTGRES_USER` | Database user | `openmtg` |
| `DB_PASSWORD` | Database password | *(required)* |
| `JWT_SECRET` | Secret key for auth tokens | *(required)* |
| `DATA_PATH` | Path for PostgreSQL data volume | `./data` |
| `CONFIG_PATH` | Path for app config volume | `./config` |
| `NOTEL` | Option to disable telemetry settings | Not present by default |

### Price Refresh Settings (Admin UI)

| Setting | Description | Default |
|---|---|---|
| Auto-refresh interval | How often stale prices are refreshed | 72 hours |
| Scryfall rate limit | API requests per second | 1 req/s |

---

## Ports

By default, OpenMTG listens on port **8080**. To change it, edit the `nginx` service in `docker-compose.yml`:

```yaml
ports:
  - "YOUR_PORT:80"
```

---

## Building from Source

```bash
git clone https://github.com/dredbaron/OpenMTG.git
cd OpenMTG
cp .env.example .env
# edit .env with your values
docker compose up -d --build
```

---

## License

[GNU Affero General Public License v3.0](LICENSE)

You are free to use, modify, and self-host OpenMTG. If you distribute a modified version or run it as a network service, you must make your source code available under the same license.

---

## Acknowledgements

Card data and pricing provided by [Scryfall](https://scryfall.com). Please respect their [API guidelines](https://scryfall.com/docs/api) and rate limits.
 
---
 
## Development History

This project was initially conceived with AI reference (Claude by Anthropic) 
as a learning exercise in building self-hosted MTG collection tools, as well
as understanding Docker image development processes. Active development is
now entirely human-driven.

AI was used only as an initial development reference to determine feasability
of the idea and the likely scope of the project. Any and all AI-suggested
code has undergone active removal and replacement with human-written code.

Contributions are welcome and reviewed by human maintainer(s) only.

---

## Credits

Favicon icon by [Faithtoken](https://game-icons.net/1x1/faithtoken/card-pick.html), licensed under [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).

## Notes

This repository underwent a full re-commit on April 1, 2026, which caused all commits to be pushed at the same time after SSH/GPG signing.
