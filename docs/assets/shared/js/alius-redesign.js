(function () {
  'use strict';

  var PRESETS = {
    '/': [
      ['Welcome', 'home-welcome'],
      ['Overview', 'alius-overview'],
      ['Scientific Study', 'scientific-study'],
      ['Redefining ASCs', 'redefining-asc'],
      ['Models', 'models'],
      ['Scope', 'scope'],
      ['References', 'references']
    ],
    '/team/': [
      ['Coordinators', 'coordinators'],
      ['Research Members', 'research-members'],
      ['Martin Fortier', 'martinfortier']
    ],
    '/newsletter/': [
      ['Overview', 'newsletter-overview'],
      ['Sign Up', 'newsletter-signup'],
      ['Submit News', 'newsletter-submit-news']
    ]
  };

  function currentPath() {
    var path = window.location.pathname || '/';
    if (path !== '/' && !path.endsWith('/')) path += '/';
    return path;
  }

  function textOf(el) {
    return (el && el.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function ensureAnchor(id, beforeEl) {
    var existing = document.getElementById(id);
    if (existing) return existing;
    var anchor = document.createElement('div');
    anchor.id = id;
    anchor.className = 'alius-anchor-target';
    anchor.setAttribute('aria-hidden', 'true');
    if (beforeEl && beforeEl.parentNode) {
      beforeEl.parentNode.insertBefore(anchor, beforeEl);
    } else {
      var content = document.getElementById('wsite-content') || document.body;
      content.insertBefore(anchor, content.firstChild);
    }
    return anchor;
  }

  function harvestLegacySectionNav() {
    var legacy = document.querySelector('.section-nav');
    if (!legacy) return [];
    var links = Array.prototype.slice.call(legacy.querySelectorAll('a[href^="#"]'));
    return links.map(function (a) {
      return [textOf(a), (a.getAttribute('href') || '').replace(/^#/, '')];
    }).filter(function (item) {
      return item[0] && item[1];
    });
  }

  function headingAnchors() {
    var content = document.getElementById('wsite-content');
    if (!content) return [];
    var headings = Array.prototype.slice.call(content.querySelectorAll('h2, h3, .wsite-content-title'));
    var seen = {};
    return headings.map(function (h, index) {
      var label = textOf(h).replace(/\u200b/g, '');
      if (!label || label.length > 70) return null;
      if (!h.id) {
        var base = label.toLowerCase().replace(/&/g, ' and ').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || ('section-' + index);
        var id = base, n = 2;
        while (seen[id] || document.getElementById(id)) id = base + '-' + n++;
        h.id = id;
      }
      seen[h.id] = true;
      return [label, h.id];
    }).filter(Boolean).slice(0, 9);
  }

  function teamAnchors() {
    var filters = document.querySelector('.team-filters');
    var grid = document.querySelector('.team-grid');
    ensureAnchor('coordinators', filters || grid);
    ensureAnchor('research-members', grid);
    return PRESETS['/team/'];
  }

  function homeAnchors() {
    var hero = document.querySelector('.wsite-header-section') || document.getElementById('banner');
    ensureAnchor('home-welcome', hero);
    return PRESETS['/'];
  }

  function anchorsForPage() {
    var path = currentPath();
    if (path === '/') return homeAnchors();
    if (path === '/team/') return teamAnchors();
    if (path === '/journal-club/' || path === '/video-lectures/') return [];
    var legacy = harvestLegacySectionNav();
    if (legacy.length) return legacy;
    if (PRESETS[path]) return PRESETS[path];
    var headings = headingAnchors();
    return headings.length ? headings : [['Content', 'wsite-content']];
  }

  function buildAnchorNav(items) {
    if (!items.length || document.querySelector('.alius-anchor-nav')) return;
    var nav = document.createElement('nav');
    nav.className = 'alius-anchor-nav';
    nav.setAttribute('aria-label', 'Page sections');
    nav.innerHTML = '<p class="alius-anchor-nav__title">On this page</p><ol></ol>';
    var list = nav.querySelector('ol');
    items.forEach(function (item) {
      if (!document.getElementById(item[1])) return;
      var li = document.createElement('li');
      var a = document.createElement('a');
      a.href = '#' + item[1];
      a.textContent = item[0];
      li.appendChild(a);
      list.appendChild(li);
    });
    if (!list.children.length) return;
    var mount = document.getElementById('content-wrapper') || document.getElementById('wsite-content');
    if (mount && mount.parentNode) {
      mount.parentNode.insertBefore(nav, mount);
    } else {
      document.body.appendChild(nav);
    }
  }

  function wireSmoothScroll() {
    document.addEventListener('click', function (event) {
      var link = event.target.closest && event.target.closest('.alius-anchor-nav a[href^="#"]');
      if (!link) return;
      var id = link.getAttribute('href').slice(1);
      var target = document.getElementById(id);
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      history.replaceState(null, '', '#' + id);
    });
  }

  function wireActiveState() {
    var links = Array.prototype.slice.call(document.querySelectorAll('.alius-anchor-nav a[href^="#"]'));
    var targets = links.map(function (a) {
      return document.getElementById(a.getAttribute('href').slice(1));
    }).filter(Boolean);
    if (!links.length || !targets.length || !('IntersectionObserver' in window)) return;
    var byId = {};
    links.forEach(function (a) { byId[a.getAttribute('href').slice(1)] = a; });
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        links.forEach(function (a) { a.classList.remove('is-active'); });
        var active = byId[entry.target.id];
        if (active) active.classList.add('is-active');
      });
    }, { rootMargin: '-20% 0px -65% 0px', threshold: 0.01 });
    targets.forEach(function (target) { observer.observe(target); });
  }

  function initJournalFilters() {
    var filters = Array.prototype.slice.call(document.querySelectorAll('.journal-filter'));
    var talks = Array.prototype.slice.call(document.querySelectorAll('.journal-talk'));
    if (!filters.length || !talks.length) return;
    var active = new Set();

    function talkMatches(talk, showAll) {
      if (showAll) return true;
      var tags = (talk.getAttribute('data-tags') || '').split(/\s+/).filter(Boolean);
      var selected = [];
      active.forEach(function (tag) { selected.push(tag); });
      return selected.every(function (tag) { return tags.indexOf(tag) !== -1; });
    }

    function syncAnchorNav(showAll) {
      var links = Array.prototype.slice.call(document.querySelectorAll('.alius-anchor-nav a[href^="#"]'));
      links.forEach(function (link) {
        var id = link.getAttribute('href').slice(1);
        var talk = document.getElementById(id);
        var item = link.closest && link.closest('li');
        if (!item || !talk || !talk.classList.contains('journal-talk')) return;
        item.hidden = !talkMatches(talk, showAll);
      });
    }

    function apply() {
      var showAll = active.size === 0;
      filters.forEach(function (button) {
        var filter = button.getAttribute('data-filter');
        button.classList.toggle('is-active', showAll ? filter === '*' : active.has(filter));
      });
      talks.forEach(function (talk) {
        talk.classList.toggle('is-filtered-out', !talkMatches(talk, showAll));
      });
      syncAnchorNav(showAll);
    }

    filters.forEach(function (button) {
      button.addEventListener('click', function () {
        var filter = button.getAttribute('data-filter');
        if (filter === '*') active.clear();
        else if (active.has(filter)) active.delete(filter);
        else active.add(filter);
        apply();
      });
    });

    apply();
  }

  function restartAnimatedLogo() {
    var logos = Array.prototype.slice.call(document.querySelectorAll('.wsite-logo img'));
    if (!logos.length) return;
    var stamp = Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 7);
    logos.forEach(function (img) {
      img.src = '/assets/brand/alius-logo.svg?v=20260519-fast-growth-normal-sway-v04&restart=' + stamp;
    });
  }

  function init() {
    restartAnimatedLogo();
    buildAnchorNav(anchorsForPage());
    wireSmoothScroll();
    wireActiveState();
    initJournalFilters();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.addEventListener('pageshow', function (event) {
    if (event.persisted) restartAnimatedLogo();
  });
})();
