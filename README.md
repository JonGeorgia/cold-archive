[English](README.md) | [Русский](README.ru.md)

<div class="title-page">

<br><br><br><br><br><br><br><br>

# 🎮📼 Offline Catalog

<br>

</div>

An offline catalog for games, movies, and any files on storage media (USB drives, external HDDs, etc.). Simply place folders containing archives on your storage device, run the scanner, and get **one** `index.html` file that opens with a double-click in a browser without internet access, displaying a catalog with covers, descriptions, categories, and search functionality.

Idea: archive once, then anytime — without internet or software installation — open and view the contents of your storage device in a convenient, well-described format.

***

## 📋 Requirements for Creating the Archive

### Mandatory

- **Python 3.7+**
- **Bash** (Linux, macOS; on Windows — WSL or Git Bash)

### Recommended

- **Pillow** — for cropping covers and screenshots:

```bash
python3 -m pip install Pillow
```

Without Pillow, the catalog is still created, but without covers or thumbnails — only names and text.
- **zenity or whiptail** — for the graphical launcher interface that runs the scanner.
Without them, the standard terminal `select` is used (always works).

```bash
sudo apt install zenity        # Debian/Ubuntu GUI
sudo apt install whiptail      # TUI in terminal
```

***

## 🚀 Quick Start

### 1. Install Dependencies

```bash
python3 -m pip install Pillow
sudo apt install zenity         # or whiptail
```

### 2. Organize Archives on the Storage Device

The only supported structure:

```text
<storage>/
├── Games/
│   └── Baldurs Gate 3/
│       ├── Baldurs Gate 3.zip         ← archive or any file
│       └── info/                      ← metadata (created automatically)
│           ├── info.txt
│           ├── cover.jpg
│           └── screenshots/
│               ├── scr_1.jpg
│               └── scr_2.jpg
├── Movies/
│   └── Inception/
│       ├── Inception.mkv
│       └── info/...
└── Other/
    └── 7-Zip/
        ├── 7z2409-x64.exe
        └── info/...
```

**Rules:**

- Only `Games/`, `Movies/`, and `Other/` folders are allowed at the root of the storage (case and language don't matter — `games`, `Games`, `игры` all work).
- Inside each category: subfolders for individual items (`Baldurs Gate 3`, `Inception`, `7-Zip`).
- Inside each `info/` folder, place metadata file `info.txt`, main cover `cover.jpg`, and a `screenshots/` folder with screenshots. If `info/` is not created, the scanner will generate it with minimal metadata.
- Each item folder must contain at least one file (archive, video, .exe — anything).
- All other folders at the root are skipped with a warning.
- If the structure differs, the scanner will find nothing.

### 3. Run the Scanner

Launch the scanner launcher file `scan.sh`:

```bash
./scan.sh
```

A menu will appear:

1. **Select storage device.**
2. **Select language** — Russian or English for the catalog interface (actual data remains in the language it was stored).
3. **Scan.**
4. **Open `index.html` in browser** — After scanning completes, a browser tab with the catalog opens.

### 4. What You’ll Get

On your storage device:

```text
<storage>/
├── index.html              ← Catalog
├── catalog.md              ← List of catalog items as a table (optional, can be deleted)
├── .archive_thumbs/        ← Thumbnail screenshots (system data)
├── Games/
│   └── Baldurs Gate 3/
│       └── info/           
│           ├── info.txt
│           └── screenshots/
└── ...
```

`index.html` — Open this file to view the catalog.

***

## 📝 info.txt — What to Write

The metadata file for each item resides at `<item>/info/info.txt`. If it doesn’t exist, the scanner generates a template with populated `Name`, `Category`, and `Year` (extracted from folder name if it contains `2023` or `(2010)` etc.). Other fields remain empty and can be filled manually later.

### All Supported Fields

| Field | Example | Appears in |
|---|---|---|
| Name | Baldurs Gate 3 | Card title |
| Category | Games | Optional — taken from folder name |
| Genre | RPG, Fantasy, Turn-based | Red line under title |
| Year | 2023 | Badge in details |
| Description | Sequel to the legendary series... | Main text in details |
| Developer / Author / Studio | Larian Studios | Details |
| Publisher | Larian Studios | Details |
| Director | Christopher Nolan | Details (for movies) |
| Language | Russian (text), English (audio) | Badge |
| Version | 4.1.1.3624 | Badge |
| Series | Baldur's Gate | Details |
| Country | USA, UK | Details |
| Duration | 2h 28m | Badge (for movies) |
| Comment | Russian patch installed. Patch 5 | Details |

Keys are case-insensitive (`Genre`, `genre`, `GENRE` — all same). Order of lines doesn't matter. Anything not matching a key is ignored (you can write personal notes).

### Examples

**Game:**

```text
Name: Baldurs Gate 3
Genre: RPG, Fantasy, Turn-based
Year: 2023
Developer: Larian Studios
Publisher: Larian Studios
Language: Russian (text), English (audio)
Version: 4.1.1.3624
Series: Baldur's Gate
Description: Sequel to the legendary series by Larian Studios. Dungeons & Dragons in digital format.
Comment: Russian patch installed. Patch 5.
```

**Movie:**

```text
Name: Inception
Genre: Sci-Fi, Thriller
Year: 2010
Director: Christopher Nolan
Country: USA, UK
Duration: 2h 28m
Language: English (original), Russian (dubbed)
Description: A thief who enters dreams is given the task of implanting an idea into someone’s subconscious.
```

**Software:**

```text
Name: 7-Zip
Year: 2024
Version: 24.09
Language: Multilingual
Description: Free file archiver with high compression ratio.
Comment: Portable version, x64.
```

***

## 🖼️ Covers and Screenshots

### `info/cover.jpg` — Cover

Place `cover.jpg` (or `cover.png`, `cover.webp`, `poster.jpg`) in `info/`. The scanner converts it to 160×213 and embeds it as base64 into `index.html`.

Ideal: vertical cover with 2:3 aspect ratio (e.g., 500×750).

### `info/screenshots/` — Screenshots

Place any `.jpg` or `.png` files in `info/screenshots/`. The scanner generates thumbnails at 320×200 in `.archive_thumbs/`.

Screenshots are displayed only on desktop browsers within the details card (click → lightbox). On mobile browsers, screenshots are hidden due to Android restrictions and catalog file size optimization.

***

## 📄 info.json — Alternative

If `info.txt` is insufficient (e.g., you need line breaks in the description), create `info.json`:

```json
{
  "name": "Baldurs Gate 3",
  "genre": "RPG, Fantasy, Turn-based",
  "year": "2023",
  "description": "Sequel to the legendary series.\n\nFeatures:\n• 3 acts\n• Co-op up to 4 players",
  "comment": "Verified on HDD #3"
}
```

`info.json` takes precedence over `info.txt` — if both exist, JSON is read.

***

## ⚙️ scan.sh Launch Flags

```bash
./scan.sh [options]
```

| Flag | Default | Purpose |
|---|---|---|
| --root PATH | prompts via menu | Scan PATH without device selection menu |
| --label NAME | disk label | Storage label (in catalog header) |
| --title TITLE | HARD ARCHIVE | Catalog title |
| --output FILE | index.html | Output filename |
| --lang ru\|en | prompts via menu | Interface language without prompt |
| --no-menu | — | Don't show menu (neither device nor language). Language = `ru` |
| --no-open | — | Don't open browser after scanning |
|  --keep-open  | — | Pause at end (terminal only; for debugging) |
| -h, --help | — | Help |

### Example Launcher Commands

```bash
# Simplest launch (all prompts)
./scan.sh

# Scripted mode: specify device, label, interface language
./scan.sh --root /media/user/USB64 --label "USB 64GB" --lang ru --no-open
```

***

## ⚙️ scan.py Flags (Run Scanner Directly in Python)

If needed, you can run the scanner directly without the launcher to control cover sizes and other parameters. Usually unnecessary.

```bash
python3 scan.py --root /media/user/USB64 --label "USB 64GB" --lang ru
```

| Flag | Default | Purpose |
|---|---|---|
| --root PATH | script folder | What to scan |
| --label NAME | empty | Storage label |
| --title TITLE | language-based | Catalog title |
| --output FILE | index.html | Output filename |
| --lang ru\|en | ru | Interface language |
| --thumbs-dir DIR | .archive_thumbs | Thumbnail folder |
| --list-size WxH | 160x213 | Base64 cover size |
| --screenshot-size WxH | 320x200 | Thumbnail screenshot size |
| --quality N | 72 | JPEG quality 1..95 |
| --no-thumbs | — | Don't generate thumbnails (faster, no images) |
| --keep-old | — | Don't delete old index.html or .archive_thumbs/ |

***

## 🌐 Interface Language

- **RU (default)** — “Archive”, “search...”, “items”, “all”, “Games/Movies/Other”, “description”, “copy path”.
- **EN** — “Archive”, “search...”, “items”, “all”, “Games/Movies/Other”, “description”, “copy path”.

Names, descriptions, genres — are not translated. These come from `info.txt` and remain as you wrote them.

***

## 🖥️ Desktop Viewing

Open `index.html` with a double-click. Works in Firefox, Chrome, Edge, Safari — no installation needed.

Features:

- Hover over an item → right panel updates
- Click → lock selection (doesn't reset when mouse leaves)
- Keyboard: `↑`/`↓` — navigate, `Enter` — lock, `Esc` — unlock
- `Ctrl+F` — focus search
- Search — by name, genre, description, developer, year
- Sort — by name/year/size, ascending/descending
- Categories — click tab `Games`/`Movies`/`Other` to filter
- Screenshots — click → fullscreen lightbox
- Copy path — button in details card. This is the core feature: copy the path, paste it in your file manager to navigate to the desired archive item.

❓ **Why so complex?**
Goal: create a beautiful, convenient catalog using only browser capabilities (universally available) without requiring software installation.
But browsers cannot directly access files in file managers due to security policies — hence, copy the path and paste into the file manager.

***

## 📱 Mobile Browser Viewing (Android)

The catalog opens in mobile browsers, but with limitations due to Android security policies. Still, it's primarily designed for desktop browsers; Android usage is limited.

### What Works

- Opening `index.html` in Brave (launch Brave first, then tap file in file manager → “Open with” → Brave).
- Viewing list, categories, details, covers, descriptions.
- Navigating “list → card → back” (on narrow smartphone screens, only one screen shown at a time).
- Search, sort.

### What Doesn't Work

- Screenshots are hidden on mobile (to reduce `index.html` size).
- Copying paths on Android — doesn't work in most file managers due to scoped storage (Android 11+). The file manager itself cannot navigate to the copied path — this is its limitation, not the catalog’s. The button shows: “Android does not allow accessing file paths on USB.”

***

## 🔄 Updating the Catalog

After adding a game/movie, updating `info.txt`, or placing a new cover — run `scan.sh` again on the same storage.

What happens:

- Old `index.html` and `.archive_thumbs/` are deleted.
- New ones are generated.
- User files (archives, `cover.jpg`, `screenshots/`, `info.txt`) are never deleted or overwritten.

***

## 🔍 Troubleshooting

### “Catalog is created but empty” / “Scanner found nothing”

Check structure:

- Must have `Games/`, `Movies/`, or `Other/`.
- Inside each category: item folders, each containing at least one file with extension from:

```text
Archives: .rar, .zip, .7z, .iso, .tar, .tar.gz, .tar.xz,
          .tar.bz2, .tgz, .gz, .xz

Videos: .mkv, .mp4, .avi, .m4v, .webm, .mov, .wmv,
        .flv, .mpg, .mpeg, .ts
```

If your files use other extensions, add them to `scan.py` constants `ARCHIVE_EXTS` or `VIDEO_EXTS`.

### Covers not displaying

- Ensure `cover.jpg` is inside `info/`, not in the item folder root.

### `data.js` is gone — this is normal

Older versions created `data.js` alongside `index.html`. Now everything is embedded in `index.html`: data and covers are included directly. This simplifies distribution.

## 📂 Project Structure

```
cold-archive/
├── scan.sh ← wrapper: menu, language selection, launches scan.py
├── scan.py ← scanner: traverses storage, generates thumbnails, creates index.html
├── index_template.html ← catalog template (HTML+CSS+JS)
└── README.md ← this file
```

### What Happens on Launch

```
scan.sh
  ├─ device selection menu (zenity/whiptail/dialog/select)
  ├─ language prompt (zenity/whiptail/dialog/select)
  ├─ scan.py --root <storage> --lang <ru|en>
  │    ├─ deletes old index.html and .archive_thumbs/
  │    ├─ finds Games/, Movies/, Other/
  │    ├─ for each item:
  │    │    ├─ creates info/ if missing (info.txt + screenshots/)
  │    │    ├─ reads info.txt/info.json
  │    │    ├─ converts cover.jpg → base64
  │    │    └─ converts screenshots/*.jpg → .archive_thumbs/
  │    ├─ collects JSON with all items
  │    ├─ injects JSON and language strings into index_template.html
  │    └─ writes final index.html
  └─ opens index.html in browser
```

***

## ❓ FAQ

**Can I open the catalog on a computer without Python?**  
Yes. `index.html` is a fully standalone file. Python and Pillow are needed only to create the catalog. Viewing requires only a browser.

**Can I use `.webp` for covers/screenshots?**  
Yes, `.webp` is supported for covers. For screenshots: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.bmp`. Pillow opens all of them.

**How to add another category (e.g., “Music”)?**  
In `scan.py`, add to `CATEGORY_DIRS`:

```python
'music': 'Music', 'музыка': 'Музыка',
```

And in `index_template.html` in `CAT_LABELS` — add translation (or leave untranslated, it will display as-is).

**Is there a limit on number of items?**  
Practically none. For 500 items, `index.html` is ~4–6 MB (with base64 covers). Loads in 1–3 sec on mobile, instantly on desktop. For 2000+ items, noticeably heavier — consider using `--no-thumbs` (list only, no covers) or splitting into multiple storage devices with separate catalogs.

**Where does the scanner write logs?**  
`/tmp/scan-YYYYMMDD-HHMMSS.log`. This is the standard Linux temp folder, cleared on reboot. For persistent storage — manually copy logs or add a custom `LOG_FILE` in `scan.sh`.

***

## 📜 License

Free to use.
