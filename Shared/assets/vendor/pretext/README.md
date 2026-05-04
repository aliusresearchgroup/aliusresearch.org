# Pretext Vendor Policy

The ALIUS site uses @chenglou/pretext as progressive enhancement for text measurement on the Team grid. The runtime imports a pinned browser ESM build and falls back to DOM measurement if the network import fails.

Implementation constraints from the installed Pretext skills:
- call prepare(text, font), never prepare(font, text)
- pass line-height as absolute CSS pixels
- wait for fonts before measurement when possible
- cache prepared handles per member bio/font pair
- do not use Pretext for CSS-only layout problems
