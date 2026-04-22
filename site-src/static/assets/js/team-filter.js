/* Team member topic filter.
 *
 * Filter pills above the grid let the user narrow the list by topic
 * (e.g. "Neuroscience", "Psychedelics", "VR"). Multiple pills can be
 * active at once — a member matches if ANY active filter is in their
 * `data-tags` attribute (OR logic).
 *
 * The "All" pill clears every filter and shows everyone.
 *
 * No dependencies — plain DOM API, defer-loaded.
 */
(function () {
  'use strict';

  function init() {
    var filters = document.querySelectorAll('.team-filter');
    if (!filters.length) return;
    var cards = Array.prototype.slice.call(document.querySelectorAll('.team-card'));
    var active = new Set();

    function apply() {
      if (active.size === 0) {
        document.querySelectorAll('.team-filter').forEach(function (b) {
          b.classList.toggle('is-active', b.getAttribute('data-filter') === '*');
        });
        cards.forEach(function (c) { c.classList.remove('is-filtered-out'); });
        return;
      }
      document.querySelectorAll('.team-filter').forEach(function (b) {
        b.classList.toggle('is-active', active.has(b.getAttribute('data-filter')));
      });
      cards.forEach(function (c) {
        var tags = (c.getAttribute('data-tags') || '').split(/\s+/).filter(Boolean);
        var match = false;
        for (var t = 0; t < tags.length; t++) if (active.has(tags[t])) { match = true; break; }
        c.classList.toggle('is-filtered-out', !match);
      });
    }

    filters.forEach(function (btn) {
      btn.addEventListener('click', function () {
        var f = btn.getAttribute('data-filter');
        if (f === '*') {
          active.clear();
        } else if (active.has(f)) {
          active.delete(f);
        } else {
          active.add(f);
        }
        apply();
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
