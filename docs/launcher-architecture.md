# Maximum Security Launcher – Architecture

This document describes the high-level architecture for the **Maximum Security** launcher and release system.

The goal is to have:

- A **simple, robust entrypoint** that can live on players’ machines and on ModDB.
- A **native-feeling launcher UI** built with React + Tailwind.
- A **serverless distribution model** that uses GitHub as the backend:
  - GitHub **Releases** for binaries.
  - A public **`manifest.json`** file in a distro repo that the launcher and pre-installer read.

Kieran should be able to cut new game builds and (eventually) launcher builds by running simple scripts without touching any of the Git/GitHub machinery directly.

---

## 1. Repos and responsibilities

### 1.1 `maximum_security` (private, main dev repo)

Contains:

- Game code, assets, WADs, etc.
- Launcher source code:
  - React + TypeScript + Tailwind app (web frontend).
  - Native wrapper config (Tauri/Electron/etc.) later.
- Pre-installer source code (small EXE).
- Build / deploy scripts:
  - `scripts/deploy_game.py`
  - `scripts/deploy_launcher.py`
  - Shared utilities for release/manifest generation.
- Optional “release config” (human-edited metadata), e.g.:
  - `config/releases.yml` or `config/releases.json`.

Humans (Arik, Kieran) only work in this repo.

### 1.2 `maximum_security_dist` (public, robot-managed)

Contains:

- `manifest.json` – the **single source of truth** for:
  - Latest launcher version and download URL.
  - List of game builds and their download URLs and metadata.
- A minimal `README`.
- Git tags and **GitHub Releases** with attached binaries:
  - `launcher-win-<version>.exe`
  - `game-<version>-win.zip`
  - Optionally `preinstaller.exe`.

This repo is **only modified by scripts**. Humans do not edit it directly under normal circumstances.

Locally, `maximum_security_dist` is cloned into a hidden directory inside `maximum_security`, e.g.:

```text
maximum_security/
  .dist_repo/   # git clone of maximum_security_dist (managed by scripts)
  launcher/     # React/Tailwind app
  scripts/
  ...
```

---

## 2. Components

### 2.1 Pre-installer (entrypoint EXE)

A tiny Windows executable that:

1. Has a **hard-coded URL** to the manifest file in the dist repo, e.g.:

   ```text
   https://raw.githubusercontent.com/<owner>/maximum_security_dist/main/manifest.json
   ```

2. Steps on run:

   - Download `manifest.json`.
   - Parse the `launcher` section.
   - Compare the **remote launcher version** with the locally-installed launcher (if any).
   - If the local launcher is missing or outdated:
     - Download the launcher binary from the URL listed in the manifest.
     - Save it to a predictable location (e.g. `%LOCALAPPDATA%\MaximumSecurity\launcher\MaximumSecurityLauncher.exe`).
   - Run the launcher EXE.
   - Exit.

3. The pre-installer is intentionally:

   - Very small.
   - Very simple (minimal logic, easy to keep bug-free).
   - Designed to **never need updating** once shipped to ModDB.

ModDB hosts **this pre-installer EXE**, plus screenshots, videos, and text. The actual game content and launcher updates are delivered via GitHub.

### 2.2 Launcher (React + Tailwind, native-wrapped)

A desktop launcher application that:

1. On startup:

   - Fetches the same `manifest.json` from `maximum_security_dist`.
   - Parses:
     - `launcher` (to show current version/info).
     - `game_builds` list.
   - Loads local state (which builds are installed, install paths, etc.) from disk.

2. Renders UI:

   - A **grimdark DOOM-like** themed interface.
   - Sections such as:
     - “Installed builds”
     - “Available builds”
   - Buttons:
     - “Install” / “Update” for each build.
     - “Play” for installed builds.

3. On install/update actions:

   - Download the game build from the URL specified in the manifest (GitHub Releases asset).
   - Extract the archive (e.g. `game-<version>-win.zip`) into a local directory.
   - Update local metadata to mark the build as installed.

4. On play:

   - Launch GZDoom with the appropriate IWAD/PK3/WAD files and config, using the installed build’s files and settings.

The UI is written in React + Tailwind (initially running as a normal web dev app via Vite), then later wrapped into a native desktop app (Tauri/Electron or similar) to produce a Windows EXE.

---

## 3. Manifest model

The **manifest** is a JSON document stored in `maximum_security_dist` and served as a static file via GitHub:

```text
https://raw.githubusercontent.com/<owner>/maximum_security_dist/main/manifest.json
```

### 3.1 Example schema (WIP)

```json
{
  "manifest_version": 1,
  "launcher": {
    "version": "1.3.0",
    "windows": {
      "url": "https://github.com/<owner>/maximum_security_dist/releases/download/launcher-1.3.0/launcher-win-1.3.0.exe",
      "sha256": "abcdef1234...",
      "size_bytes": 12345678
    },
    "notes": "New UI and bugfixes."
  },
  "game_builds": [
    {
      "version": "1.0.0",
      "label": "Release 1.0",
      "channel": "stable",
      "recommended": true,
      "windows": {
        "url": "https://github.com/<owner>/maximum_security_dist/releases/download/game-1.0.0/game-1.0.0-win.zip",
        "sha256": "deadbeef...",
        "size_bytes": 234567890
      },
      "changelog": "First public release.",
      "meta": {
        "min_launcher_version": "1.3.0"
      }
    }
  ]
}
```

Notes:

- `manifest_version` allows future schema changes.
- `launcher.windows` and `game_builds[*].windows` contain **direct download URLs** into GitHub Releases.
- The launcher UI and pre-installer only care about:
  - `version`
  - `url`
  - `sha256` (optional but recommended)
  - `size_bytes` (for progress and disk space checks).
- Extra fields (`label`, `changelog`, `meta`) are useful for display and compatibility checks.

### 3.2 Manifest ownership

- **Humans do not edit `manifest.json` directly.**
- It is **generated/updated by deploy scripts** in `maximum_security`.
- Optionally, a simpler “release config” file lives in `maximum_security` (e.g. `config/releases.yml`) that describes human-facing aspects (labels, channel, notes). Scripts merge this config with concrete file info (URLs, hashes, sizes) when generating the final manifest.

---

## 4. Deployment & dist automation

All deployment logic lives in `maximum_security/scripts/`. Kieran should be able to run high-level commands without thinking about:

- How GitHub Releases work.
- How `maximum_security_dist` is laid out.
- How the manifest is updated.

### 4.1 Local layout and dist repo clone

Inside `maximum_security`:

```text
maximum_security/
  .dist_repo/             # clone of maximum_security_dist (managed by scripts)
  launcher/               # React/Tailwind app
  game/                   # mod/game content (WADs, maps, etc.)
  scripts/
    deploy_game.py
    deploy_launcher.py
    ...
  config/
    releases.yml          # optional
```

Scripts ensure `.dist_repo` exists and is in sync:

- If missing:
  - Clone `maximum_security_dist` into `.dist_repo`.
- On each deploy:
  - `cd .dist_repo && git fetch && git checkout main && git pull`.

### 4.2 Deploying a new game build

For example:

```bash
scripts/deploy_game.py --version 1.0.0 --notes "First public release"
```

Conceptual steps:

1. **Build artifact**:
   - Run the mod build pipeline.
   - Produce `build/game-1.0.0-win.zip`.

2. **Publish to GitHub Releases**:
   - In `maximum_security_dist` (via API/CLI):
     - Create or update a Release tagged `game-1.0.0`.
     - Upload `game-1.0.0-win.zip` as an asset.
   - Capture the resulting download URL.

3. **Update manifest**:
   - Read current `manifest.json` from `.dist_repo`.
   - Insert or update a `game_builds` entry for version `1.0.0`, with:
     - `version`, `label`, `channel`, `recommended`.
     - `windows.url` = the release asset URL.
     - `size_bytes` and `sha256` from the local file.
   - Write updated `manifest.json`.

4. **Commit & push** (in `.dist_repo`):
   - `git commit -am "Add game build 1.0.0"`
   - `git push origin main`.

5. Optional:
   - Update `config/releases.yml` in `maximum_security` to record that 1.0.0 exists.
   - Commit that change separately in the main repo.

### 4.3 Deploying a new launcher build

Similarly:

```bash
scripts/deploy_launcher.py --version 1.3.0 --notes "New launcher UI"
```

Steps:

1. **Build launcher EXE** (via Tauri/Electron or similar).
   - Produce `build/launcher-win-1.3.0.exe`.

2. **Publish to GitHub Releases**:
   - Create or update Release tagged `launcher-1.3.0` in `maximum_security_dist`.
   - Upload `launcher-win-1.3.0.exe` as asset.
   - Capture asset download URL.

3. **Update manifest**:
   - Read `manifest.json` in `.dist_repo`.
   - Update `launcher` section:
     - `version`, `windows.url`, `sha256`, `size_bytes`, `notes`.
   - Save, commit, push.

Once this is done:

- Pre-installer sees the new launcher version in the manifest next time it runs and auto-updates the player’s launcher.

---

## 5. Native wrapper choice (future)

The React/Tailwind UI will be wrapped into a native desktop app.

### Options

- **Tauri**:
  - Very small footprint.
  - Rust-based backend.
  - Good for Windows + Linux + macOS.
  - Likely a good fit.

- **Electron**:
  - Heavier footprint.
  - Mature ecosystem.
  - All-JS/TS stack.

The architecture above doesn’t depend on which one is chosen. For now, the important points are:

- The React app should be **self-contained** and buildable into a static bundle.
- The native wrapper will:
  - Load that bundle into a window.
  - Provide any additional file system access needed (e.g. the directory where games are installed, config paths) via a small API layer.

Implementation details for Tauri/Electron can be added later.

---

## 6. ModDB’s role

Given this architecture, ModDB is:

- A **marketing/community** platform:
  - Screenshots, videos, changelog posts, comments.
- A **host for the pre-installer EXE**:
  - The file users download to start the process.
- Optionally, a host for “full package” zips for players who don’t want to use the launcher.

The actual update pipeline and content delivery are driven entirely by:

- `maximum_security` (private code + scripts).
- `maximum_security_dist` (public manifest + releases).

---

## 7. Summary

- The **pre-installer** is a tiny, stable EXE that:
  - Reads `manifest.json` from `maximum_security_dist`.
  - Ensures the launcher is present/up to date.
  - Runs the launcher.

- The **launcher** is a React/Tailwind app (native-wrapped later) that:
  - Reads the same `manifest.json`.
  - Shows available game builds.
  - Installs/updates them.
  - Launches the game with appropriate arguments.

- The **dist repo** is a public, robot-managed repo containing:
  - `manifest.json`.
  - GitHub Releases hosting game and launcher binaries.

- All deploy complexity (building artifacts, publishing Releases, updating manifest) is hidden behind simple scripts in the private `maximum_security` repo, so that Kieran can:

  - Edit the game.
  - Run `scripts/deploy_game.py` or `scripts/deploy_launcher.py`.
  - Have the world see the new version without touching Git internals or dist repo details.
