# Top of Mind Desk

This folder is now the David-OS home for the installed **Top of Mind** PWA.

Source of this recovery:

- Installed app: `top-of-mind.davidokc28.workers.dev-80408DAD_th1rnh3hv9v56!App`
- Live URL: `https://top-of-mind.davidokc28.workers.dev/`
- Capture: `D:\00_CANON_REFERENCE\04_SOURCE_POINTERS\top_of_mind_installed_app_capture`

The previous local desk implementation was archived, not deleted:

- `D:\GitHub\David-OS\_archive_wrong_desk_20260715_151224`

## Commands

```powershell
npm install
npm run dev
npm run build
```

The app expects the local David-OS API at:

`http://127.0.0.1:10000`

The recovered bundle is currently a built PWA bundle, not the original editable React/TSX source. The bundle contains `code-path` markers, so the editable source can be reconstructed later.
