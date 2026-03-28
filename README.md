## Installation

1. Clone the repo:
```bash
git clone https://github.com/yourusername/pawplayer.git
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
    size = 670 140
}
```