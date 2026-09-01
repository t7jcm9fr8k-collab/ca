# fonts/

Drop OFL font files here. `render_shirt.py` prefers this folder over anything
on the system, and it is the difference between artwork you can sell and
artwork with an open licence question attached.

Both free, both SIL Open Font License, both from fonts.google.com:

| File | Used for |
|---|---|
| `Anton-Regular.ttf` | treatment C, the condensed tower |
| `ArchivoBlack-Regular.ttf` | treatments A, B, D, E |

Check what the script actually resolved:

```
python3 render_shirt.py --list-fonts
```

Anything marked `NOT for sale` means it fell back to a system font. Fine for
comparing treatments on screen; not for uploading to Printify. Reasoning is in
`../README.md`.

The `.ttf` files themselves are not committed — Google Fonts is the source of
truth and re-downloading takes a minute.
