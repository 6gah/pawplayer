# pawplayer 🐾

> *meowmeow*

A cozy vibe coded terminal lyrics player for Spotify on Linux. Lyrics type themselves out in sync (kinda) with your music.

---

## Features

- Synced lyrics that animate character by character
- Past lyrics dim and stack above the current line
- Starfield idle animation when nothing is playing
- Lyrics cached locally so they only fetch once
- Tiny floating window that sits anywhere on your desktop

## Dependencies

- `python3`
- `playerctl`
- `spotify`
- A true color terminal (kitty, foot, alacritty)

## Installation

1. Clone the repo:
```bash
git clone https://github.com/6gah/pawplayer
```

2. Add an alias to your `~/.zshrc` or `~/.bashrc`:
```bash
alias pawplayer="kitty --title pawplayer python3 ~/pawplayer/lyrics-instant.py"
```

3. Reload your shell:
```bash
source ~/.zshrc
```

4. Run it:
```bash
pawplayer
```

## Hyprland window rule (optional)
To open it as a floating window, add to `hyprland.conf`:
```ini
windowrule {
    name = pawplayer-float
    match:title = ^(pawplayer)$
    float = true
}
windowrule {
    name = pawplayer-size
    match:title = ^(pawplayer)$
    size = 640 200
}
```