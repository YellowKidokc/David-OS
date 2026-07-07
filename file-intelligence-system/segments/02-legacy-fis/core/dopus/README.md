# SmartFolder for Directory Opus

**Folders that remember. Files that know where they've been.**

A Directory Opus script add-in that turns your file manager into an 
intelligent workspace with file history tracking, folder content 
previews, and metadata that travels with your files.

## Install

1. Open Directory Opus
2. Go to **Settings > Preferences > Toolbars > Scripts** 
   (or **Script Add-ins**)
3. Drag `SmartFolderCore.js` onto the script list
4. Enable the script

To add columns: right-click any column header > **Columns > Script** 
> check the SF columns you want.

## Columns Added

| Column | What It Shows |
|--------|---------------|
| SF: History | Last action + timestamp |
| SF: Contents | Folder summary on hover — counts + filenames |
| SF: Age | Human-readable age (2h, 3d, 5mo) |
| SF: Origin | Where file came from |

## Requirements

- Directory Opus 13+
- Windows 10/11 + PowerShell (for ADS read/write)
