/* Team-card click-to-expand using FLIP (First-Last-Invert-Play).
 *
 * Goal: the clicked card genuinely occupies 2×2 grid cells (a real square),
 * siblings physically reflow to new grid positions, and every card's
 * motion between old and new positions is animated simultaneously on the
 * same curve. This is a true layout animation, not a cosmetic scale.
 *
 * How FLIP works here:
 *   1. FIRST — capture every .team-card's getBoundingClientRect()
 *   2. Toggle classes so the grid reflows (clicked card becomes 2×2,
 *      siblings relocate)
 *   3. LAST — capture the new rects
 *   4. INVERT — apply transform: translate+scale that puts each card
 *      VISUALLY back at its FIRST position, with transition disabled
 *   5. Force reflow
 *   6. PLAY — remove the transforms with transition enabled; the browser
 *      animates from inverted (FIRST) to identity (LAST) for all cards
 *      simultaneously on the shared 1600ms cubic-bezier
 *
 * Bio un-clamp also animates via max-height (pretext-measured target)
 * on the same curve, so the clicked card's full bio reveals in lockstep
 * with the geometric growth.
 */
(function () {
  'use strict';

  var ANIM_MS = 1600;
  var EASE = 'cubic-bezier(0.22, 0.61, 0.36, 1)';
  var state = { expanded: null, measure: null };

  function init() {
    if (!document.querySelector('.team-card')) return;
    document.addEventListener('click', onDocClick, true);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') collapse();
    });

    // Best-effort pretext import for precise bio text measurement
    try {
      import(/* @vite-ignore */ 'https://esm.sh/@chenglou/pretext@0.0.4')
        .then(function (mod) {
          if (mod && mod.getMeasureContext) state.measure = makeMeasurer(mod);
        })
        .catch(function () {});
    } catch (_e) {}
  }

  function makeMeasurer(mod) {
    return function (text, fontSpec, availablePx, lineHeightPx) {
      try {
        var ctx = mod.getMeasureContext();
        ctx.font = fontSpec;
        var words = text.split(/\s+/);
        var lines = 1;
        var current = '';
        for (var i = 0; i < words.length; i++) {
          var candidate = current ? current + ' ' + words[i] : words[i];
          var w = ctx.measureText(candidate).width;
          if (w > availablePx && current) {
            lines++;
            current = words[i];
          } else {
            current = candidate;
          }
        }
        return Math.ceil(lines * lineHeightPx);
      } catch (_e) {
        return null;
      }
    };
  }

  function getComputedFont(el) {
    var s = getComputedStyle(el);
    return (s.fontStyle || '') + ' ' + (s.fontWeight || '') + ' ' +
           s.fontSize + ' / ' + s.lineHeight + ' ' + s.fontFamily;
  }

  function measureBioHeightAtWidth(card, widthPx) {
    var bio = card.querySelector('.team-card__bio');
    if (!bio) return 0;
    var text = (bio.textContent || '').trim();
    var cs = getComputedStyle(bio);
    var lineHeight = parseFloat(cs.lineHeight);
    if (!lineHeight || !isFinite(lineHeight)) lineHeight = parseFloat(cs.fontSize) * 1.7;
    if (state.measure && text && widthPx > 0) {
      var h = state.measure(text, getComputedFont(bio), widthPx, lineHeight);
      if (h) return h + 8;
    }
    // Fallback: offscreen clone at the target width
    var clone = bio.cloneNode(true);
    clone.style.cssText = (
      'position:absolute; left:-9999px; top:0; ' +
      'width:' + widthPx + 'px; max-height:none; ' +
      '-webkit-line-clamp:unset; display:block;'
    );
    document.body.appendChild(clone);
    var h2 = clone.scrollHeight;
    document.body.removeChild(clone);
    return h2 + 8;
  }

  function onDocClick(e) {
    var card = e.target.closest && e.target.closest('.team-card');
    if (!card) return;
    if (e.target.closest('.team-card__icon, .team-card__links a, .team-card__links span')) return;
    e.preventDefault();
    if (card === state.expanded) {
      collapse();
    } else {
      expand(card);
    }
  }

  function rectsMap(cards) {
    var m = new Map();
    for (var i = 0; i < cards.length; i++) m.set(cards[i], cards[i].getBoundingClientRect());
    return m;
  }

  function flipAnimate(cards, firstRects, lastRects) {
    // INVERT: disable transition, apply inverse transform per card
    for (var i = 0; i < cards.length; i++) {
      var c = cards[i];
      var f = firstRects.get(c), l = lastRects.get(c);
      if (!f || !l) continue;
      var dx = f.left - l.left;
      var dy = f.top - l.top;
      var sx = l.width === 0 ? 1 : (f.width / l.width);
      var sy = l.height === 0 ? 1 : (f.height / l.height);
      // Skip if nothing changed
      if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5 && Math.abs(sx - 1) < 0.001 && Math.abs(sy - 1) < 0.001) {
        continue;
      }
      c.style.transition = 'none';
      c.style.transformOrigin = 'top left';
      c.style.transform = 'translate(' + dx + 'px, ' + dy + 'px) scale(' + sx + ', ' + sy + ')';
    }
    // Force reflow so the browser records the inverted state as the starting point
    // eslint-disable-next-line no-unused-expressions
    cards[0] && cards[0].offsetWidth;

    // PLAY: re-enable transition, remove transform → animates to LAST
    requestAnimationFrame(function () {
      for (var j = 0; j < cards.length; j++) {
        var c2 = cards[j];
        c2.style.transition = 'transform ' + ANIM_MS + 'ms ' + EASE + ', max-height ' + ANIM_MS + 'ms ' + EASE + ', opacity ' + ANIM_MS + 'ms ease';
        c2.style.transform = '';
      }
    });

    // Clean up inline transition overrides after the animation
    setTimeout(function () {
      for (var k = 0; k < cards.length; k++) {
        cards[k].style.transition = '';
        cards[k].style.transform = '';
        cards[k].style.transformOrigin = '';
      }
    }, ANIM_MS + 40);
  }

  function expand(card) {
    var grid = card.closest('.team-grid');
    if (!grid) return;
    var cards = Array.from(grid.querySelectorAll('.team-card'));
    var previous = state.expanded;

    // STEP 1 · FIRST — record current positions/sizes
    var first = rectsMap(cards);

    // STEP 2 · Toggle classes (and uncollapse any previous expand)
    if (previous && previous !== card) previous.classList.remove('team-card--expanded');
    card.classList.add('team-card--expanded');
    grid.classList.add('team-grid--has-expanded');

    // Force a synchronous layout with the new classes applied
    // eslint-disable-next-line no-unused-expressions
    grid.offsetWidth;

    // STEP 3 · Now the clicked card has its new (wider) width — pretext-
    // measure the bio's natural height at this exact width and feed it
    // into the CSS var so the max-height transition has a real target.
    var bioEl = card.querySelector('.team-card__bio');
    var bioWidth = bioEl ? (bioEl.getBoundingClientRect().width - 2) : 0;
    if (bioWidth > 0) {
      var h = measureBioHeightAtWidth(card, bioWidth);
      card.style.setProperty('--expanded-bio-height', h + 'px');
    }

    // Another layout pass so the LAST rect includes the final bio height
    // eslint-disable-next-line no-unused-expressions
    grid.offsetWidth;

    // STEP 4 · LAST — record new positions/sizes after reflow
    var last = rectsMap(cards);

    // STEP 5-6 · INVERT + PLAY
    flipAnimate(cards, first, last);

    state.expanded = card;
  }

  function collapse() {
    if (!state.expanded) return;
    var prev = state.expanded;
    var grid = prev.closest('.team-grid');
    if (!grid) {
      prev.classList.remove('team-card--expanded');
      state.expanded = null;
      return;
    }
    var cards = Array.from(grid.querySelectorAll('.team-card'));

    var first = rectsMap(cards);
    prev.classList.remove('team-card--expanded');
    grid.classList.remove('team-grid--has-expanded');
    prev.style.removeProperty('--expanded-bio-height');

    // eslint-disable-next-line no-unused-expressions
    grid.offsetWidth;
    var last = rectsMap(cards);
    flipAnimate(cards, first, last);

    state.expanded = null;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
