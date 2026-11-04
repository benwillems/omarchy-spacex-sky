# SpaceX Sky

Omarchy shell bar widget. Marketplace install:

```bash
omarchy plugin add https://github.com/benwillems/omarchy-spacex-sky.git --enable
~/.config/omarchy/plugins/bjw.spacex-sky/install.sh
```

Click the rocket for the sky board. Tap a city to filter, tap its star
for alerts. Cape Canaveral is one star for every Cape pad, and Kennedy is
one star for LC-39A and LC-39B. Each launch still names its pad. A Florida
launch that is not already the hero is called out when the filter is All.
The bar shows the hero (`Cape · SLC-40`, or a train clock), and Florida
only when that is a different event. Favorites live in
`~/.config/omarchy-spacex-sky/config.toml`.

`SkyPanel.qml` is Omarchy's keyboard panel, kept in this plugin so an
Omarchy update cannot wipe it. The card is a rounded rectangle with a
radius of at least 18, because this machine's Hyprland rounding is 0.
`BorderSurface` only resolves inside the shell's `qs.Ui` module, so the
card does not use that type.
