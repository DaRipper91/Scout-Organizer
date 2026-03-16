# Filesystem Cleanup Guide

This document logs the steps taken to clean up the filesystem on this machine. You can use these commands later to reclaim space.

## 1. Arch Linux AUR Helper Cache (yay)
The `yay` cache stores downloaded packages and built packages. Over time, this can grow massively.
**Location:** `~/.cache/yay/`
**Command to clean:** `rm -rf ~/.cache/yay/*` (or `yay -Scc` for an interactive, deeper clean)

## 2. Gradle Cache
Gradle stores dependencies and build cache. Old project dependencies can linger indefinitely.
**Location:** `~/.gradle/caches/`
**Command to clean:** `rm -rf ~/.gradle/caches/*`

## 3. Duplicate Nothing Phone Firmware
There was a 5.1 GB firmware file that was duplicated in two locations. We removed one of the copies to reclaim space.
**Locations:** 
- `~/Projects/Nothing2a/MTK-Driver-v5.2307/Nothing Phone_2a_23111_release_user_20240301_220619/23111_release_user_20240301_220619.ntpi` (KEPT)
- `~/Jules_Projects/NOTHING_UNBRICK/23111_release_user_20240301_220619.ntpi` (DELETED)
**Command to clean:** `rm <path_to_the_unwanted_copy>`

## 4. Duplicate Media Backups (Pictures)
The exact same 30 GB of pictures and videos were found in two locations. We kept the primary folder and deleted the redundant NVMe backup.
**Locations:**
- `~/Pictures/Pictures/` (KEPT)
- `~/Desktop/NVMe_Backup/Pictures/` (DELETED)
**Command to clean:** `rm -rf ~/Desktop/NVMe_Backup/Pictures/`

## 5. Incomplete / Failed Video Transfers
There were almost 5 GB of `.partial` files left behind from failed downloads or interrupted transfers inside the videos folder. The completed `.mp4` versions were already present, making these safe to delete.
**Location:** `~/Videos/!zZVIDEOSZz/Videos From Backups/Videos/Personal/*.partial`
**Command to clean:** `find ~/Videos -name "*.partial" -delete`

## 6. Development Package Manager Caches
Package managers for Python and Node.js often cache downloaded archives to speed up future installations. Over time, these can grow to multiple gigabytes. We cleared the caches for `uv`, `pip`, and `pnpm`.
**Locations:**
- `~/.cache/uv/`
- `~/.cache/pip/`
- `~/.local/share/pnpm/store/`
**Command to clean:** `rm -rf ~/.cache/uv/* ~/.cache/pip/* ~/.local/share/pnpm/store/*`

## 7. Local AI Models (Ollama)
Ollama stores local Large Language Models (LLMs) which are often multi-gigabyte files. These were cleared out to save space, but can be easily re-downloaded by running models again.
**Location:** `~/.ollama/models/`
**Command to clean:** `rm -rf ~/.ollama/models/*`

## 8. Old OS Installation Images
Large compressed image files (`.img.xz`) used for flashing the Pinephone were removed.
**Location:** `~/Migration_Archive/Pinephone/*.img.xz`
**Command to clean:** `rm -f ~/Migration_Archive/Pinephone/*.img.xz`

## 9. Trashed Android Files
Android's "Recycle Bin" creates hidden files prefixed with `.trashed-` which are often carried over in backups. These were taking up 2.5 GB.
**Location:** `~/Pictures/Pictures/`
**Command to clean:** `find ~/Pictures/Pictures -name ".trashed-*" -delete`

## 10. Duplicate Concert Videos (Lamb of God)
Over 9 GB of identical concert videos existed in both an organized folder and an unorganized camera dump. The unorganized duplicates were removed.
**Locations:**
- `~/Pictures/Pictures/DCIM/Videos/LambofGod/` (KEPT)
- `~/Pictures/Pictures/DCIM/DCIM/Camera/` (DELETED DUPLICATES)
**Command to clean:** `for file in ~/Pictures/Pictures/DCIM/Videos/LambofGod/*; do base=$(basename "$file"); if [ -f "~/Pictures/Pictures/DCIM/DCIM/Camera/$base" ]; then rm "~/Pictures/Pictures/DCIM/DCIM/Camera/$base"; fi; done`

## 11. Flutter Build Cache
Flutter and Android generate large build artifacts. Deleting the `build/` directory in a project is completely safe as it gets recreated on compile.
**Location:** `~/Projects/DaRipped_tiny_computer/build/`
**Command to clean:** `rm -rf ~/Projects/DaRipped_tiny_computer/build/`

## 12. Git Garbage Collection
Running git garbage collection on large repositories reduces `.git` history size locally without losing information.
**Location:** `~/Projects/DaRipped_tiny_computer/.git`
**Command to clean:** `git gc --prune=now`

## 13. JetBrains Toolbox Cache
JetBrains IDEs (like Android Studio) generate temporary files and cache updates in this folder.
**Location:** `~/.local/share/JetBrains/Toolbox/cache/`
**Command to clean:** `rm -rf ~/.local/share/JetBrains/Toolbox/cache/* ~/.local/share/JetBrains/Toolbox/logs/*`

## 14. Unused Large ROMs
Large android ROMs/firmware can take up massive space and are often only needed for one-time flashing. We deleted a 5.1 GB `.ntpi` file.
**Location:** `~/Projects/Nothing2a/...`
**Command to clean:** `rm <path_to_large_rom>`

## 15. Flatpak Caches & Unused Runtimes
Flatpak apps can leave behind unused runtimes or temporary cache files. 
**Command to clean:** `flatpak uninstall --unused -y && rm -rf ~/.local/share/flatpak/tmp/*`

---
**Total Space Reclaimed during this session:** ~90 GB
*(Home directory reduced from 172 GB to ~82 GB)*
