# Folder Loop downloads

Official Windows app downloads and signed updates for Folder Loop.

Get the full player ZIP from [Releases](https://github.com/nsgray/folder-loop-updates/releases/latest), extract everything, and open FolderLoop.exe. No Python or separate VLC installation is needed.

Starting with Player 2.9, use **Check for updates** in the player. Routine updates download the small app package and reuse the existing playback libraries. Libraries download separately when they change. The player checks the release signature and all downloaded files, then asks before restarting. Settings, playlists and media are preserved. A failed startup check restores the previous app.

Displays need internet access to GitHub, but do not need a GitHub account. Updates are checked only when requested. This repository contains finished app binaries, update metadata, and release tooling; private source, display media and account credentials are not published here.

Release publication is separate from building: an unsigned build is imported, then its manifest is signed using the offline release key before the publish workflow can release it. The private signing key is never stored in this repository or on its runners.
