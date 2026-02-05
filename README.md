# HypeCheck

HypeCheck is a "Social Media Event & Data Processing System" that measures the correlation between social media "hype" and financial reality.

## Project Structure

This is a monorepo containing:

- **apps/web**: React + Vite Frontend
- **apps/api**: Node.js + Express Backend
- **apps/etl**: Python Data Ingestion Service

## Getting Started

You can run the project using **Docker** (recommended for backend/DB) or **Locally** (via npm).

### Option 1: Docker

This method spins up the PostgreSQL Database, Node.js API, and Python ETL service in containers.

1.  **Start Backend Services:**

    ```bash
    npm run docker:up
    ```

    _This runs `docker-compose up --build`._

2.  **Start Frontend (Locally):**
    Open a new terminal and run:

    ```bash
    npm run setup:web  # One-time setup
    npm run dev:web
    ```

    The frontend will be available at `http://localhost:5173`.

3.  **Stop Services:**
    ```bash
    npm run docker:down
    ```

---

### Option 2: Local Development (No Docker)

If you do not have Docker or prefer running everything on your machine directly.

#### Prerequisites

- Node.js (v18+)
- Python (v3.9+)
- PostgreSQL installed and running locally.

<details>
<summary><strong>Python & PostgreSQL Installation Guide</strong></summary>

**For Windows:**

1.  **Python:** Download the installer from python.org. **Important:** Check "Add Python to PATH" during installation.
2.  **PostgreSQL:** Download the installer from postgresql.org. Remember the password you set for the `postgres` user.
3.  **Verify:** Open PowerShell and run `python --version` and `psql --version`.

**For macOS:**

1.  **Python:** MacOS comes with Python, but it's best to use Homebrew: `brew install python`.
2.  **PostgreSQL:** Use Homebrew: `brew install postgresql@15` then `brew services start postgresql@15`.
3.  **Verify:** Run `python3 --version` and `psql --version` in Terminal.
</details>

#### 1. Database Setup

Ensure your local PostgreSQL is running. Create a database named `hypecheck`.
Update `apps/api/.env` to point to your local DB if needed:

```env
DATABASE_URL=postgres://YOUR_USER:YOUR_PASSWORD@localhost:5432/hypecheck
```

#### 2. Install Dependencies

Run these commands once to set up all services:

```bash
npm install           # Root dependencies
npm run setup:api     # Backend dependencies
npm run setup:web     # Frontend dependencies
npm run setup:etl     # Python dependencies
```

#### 3. Run Services

You will need **3 separate terminal windows**:

**Terminal 1 (API):**

```bash
npm run dev:api
# Runs on http://localhost:3000
```

**Terminal 2 (Frontend):**

```bash
npm run dev:web
# Runs on http://localhost:5173
```

**Terminal 3 (ETL Service):**

```bash
npm run dev:etl
```

## Scripts Reference

All scripts are run from the **root** directory:

| Command               | Description                                  |
| :-------------------- | :------------------------------------------- |
| `npm run docker:up`   | Builds and starts DB, API, and ETL in Docker |
| `npm run docker:down` | Stops and removes Docker containers          |
| `npm run dev:web`     | Starts the React frontend locally            |
| `npm run dev:api`     | Starts the Express backend locally           |
| `npm run dev:etl`     | Starts the Python ETL script locally         |
| `npm run setup:web`   | Installs frontend dependencies               |
| `npm run setup:api`   | Installs backend dependencies                |
| `npm run setup:etl`   | Installs Python requirements                 |
