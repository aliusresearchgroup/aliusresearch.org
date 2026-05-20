const PRETEXT_URL = 'https://esm.sh/@chenglou/pretext@0.0.4';
const COLLAPSE_AFTER_MS = 30000;
const MIN_SIBLING_TRACK = 112;
const MIN_SQUARE_SIDE = 280;
const ACCORDION_WIDTH = 560;
const COMPACT_ROW_SIZE = 236;

let pretext = null;
let expandedCard = null;
let collapseTimer = 0;
let animationTimer = 0;
let resizeFrame = 0;
let layoutVersion = 0;
const preparedCache = new WeakMap();

function cssFontFor(element) {
  const style = getComputedStyle(element);
  return [
    style.fontStyle,
    style.fontVariant,
    style.fontWeight,
    style.fontSize,
    style.fontFamily
  ].filter(Boolean).join(' ');
}

function lineHeightPx(element) {
  const style = getComputedStyle(element);
  const explicit = Number.parseFloat(style.lineHeight);
  if (Number.isFinite(explicit)) return explicit;
  const size = Number.parseFloat(style.fontSize) || 14;
  return size * 1.58;
}

function trackList(value) {
  return String(value || '').split(/\s+/).filter((track) => track && track !== 'none');
}

function columnsFor(grid) {
  return trackList(getComputedStyle(grid).gridTemplateColumns).length || 1;
}

function visibleCards(grid) {
  return Array.from(grid.querySelectorAll('.team-card'))
    .filter((card) => !card.classList.contains('is-filtered-out'));
}

function motionMs(grid) {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return 0;
  const value = getComputedStyle(grid).getPropertyValue('--team-motion-duration').trim();
  if (!value) return 860;
  if (value.endsWith('ms')) return Number.parseFloat(value) || 860;
  if (value.endsWith('s')) return (Number.parseFloat(value) || 0.86) * 1000;
  return Number.parseFloat(value) || 860;
}

function gridMetrics(grid) {
  const style = getComputedStyle(grid);
  const columns = columnsFor(grid);
  const gap = Number.parseFloat(style.columnGap) || 0;
  const paddingLeft = Number.parseFloat(style.paddingLeft) || 0;
  const paddingRight = Number.parseFloat(style.paddingRight) || 0;
  const rect = grid.getBoundingClientRect();
  const available = Math.max(0, rect.width - paddingLeft - paddingRight - gap * Math.max(0, columns - 1));
  const base = Math.max(1, available / Math.max(1, columns));
  const compactRows = columns <= 1 || window.innerWidth <= ACCORDION_WIDTH || base < 180;
  const rowBase = compactRows ? COMPACT_ROW_SIZE : base;
  return { columns, gap, available, base, rowBase };
}

function rowCountFor(grid, columns) {
  return Math.max(1, Math.ceil(visibleCards(grid).length / Math.max(1, columns)));
}

function rowTracks(count, base, selectedRow = -1, selectedSize = base) {
  return Array.from({ length: count }, (_, index) => {
    const size = index === selectedRow ? selectedSize : base;
    return `${Math.max(1, Math.round(size))}px`;
  }).join(' ');
}

function baseColumnTracks(metrics) {
  return Array.from({ length: metrics.columns }, () => {
    return `${Math.max(1, Math.round(metrics.base))}px`;
  }).join(' ');
}

function expandedColumnTracks(metrics, selectedColumn, selectedSize) {
  if (metrics.columns <= 1) return `${Math.max(1, Math.round(metrics.available))}px`;
  const siblingSize = Math.max(
    MIN_SIBLING_TRACK,
    (metrics.available - selectedSize) / (metrics.columns - 1)
  );
  return Array.from({ length: metrics.columns }, (_, index) => {
    const size = index === selectedColumn ? selectedSize : siblingSize;
    return `${Math.max(1, Math.round(size))}px`;
  }).join(' ');
}

function setBaseSize(grid, metrics = gridMetrics(grid)) {
  grid.style.setProperty('--team-card-base-size', `${Math.round(metrics.rowBase)}px`);
  return metrics;
}

function syncIdleGrid(grid) {
  const metrics = setBaseSize(grid);
  grid.style.gridTemplateRows = rowTracks(rowCountFor(grid, metrics.columns), metrics.rowBase);
  if (!expandedCard || expandedCard.closest('.team-grid') !== grid) {
    grid.style.removeProperty('grid-template-columns');
    grid.classList.remove('team-grid--has-expanded', 'team-grid--accordion-mode');
  }
}

function contentHost() {
  return document.getElementById('wsite-content') || document.body;
}

function inlineSizeInsideCard(card, outerWidth) {
  const style = getComputedStyle(card);
  const inset = ['paddingLeft', 'paddingRight', 'borderLeftWidth', 'borderRightWidth']
    .reduce((sum, prop) => sum + (Number.parseFloat(style[prop]) || 0), 0);
  return Math.max(120, outerWidth - inset);
}

function measureWithPretext(bio, width) {
  if (!pretext || !pretext.prepare || !pretext.layout) return null;
  const text = (bio.textContent || '').trim();
  if (!text) return null;
  const font = cssFontFor(bio);
  let record = preparedCache.get(bio);
  if (!record || record.font !== font || record.text !== text) {
    record = { font, text, prepared: pretext.prepare(text, font) };
    preparedCache.set(bio, record);
  }
  const result = pretext.layout(record.prepared, width, lineHeightPx(bio));
  return Math.max(result.height, lineHeightPx(bio)) + 6;
}

function measureWithDom(bio, width) {
  const clone = bio.cloneNode(true);
  clone.style.cssText = [
    'position:absolute',
    'left:-9999px',
    'top:0',
    `width:${width}px`,
    'max-height:none',
    'opacity:1',
    'display:block',
    'margin:16px 0 0',
    '-webkit-line-clamp:unset',
    'pointer-events:none'
  ].join(';');
  contentHost().appendChild(clone);
  const height = clone.scrollHeight;
  clone.remove();
  return height + 6;
}

function bioHeightAtWidth(card, width) {
  const bio = card.querySelector('.team-card__bio');
  if (!bio) return 0;
  let pretextHeight = null;
  try {
    pretextHeight = measureWithPretext(bio, width);
  } catch (error) {
    pretextHeight = null;
  }
  return Math.ceil(Math.max(pretextHeight || 0, measureWithDom(bio, width)) + 2);
}

function setBioHeight(card, outerWidth) {
  const bio = card.querySelector('.team-card__bio');
  if (!bio) return;
  const innerWidth = inlineSizeInsideCard(card, outerWidth);
  card.style.setProperty('--expanded-bio-height', `${bioHeightAtWidth(card, innerWidth)}px`);
}

function measureCardHeightAtSide(card, side) {
  const clone = card.cloneNode(true);
  clone.removeAttribute('id');
  clone.setAttribute('aria-hidden', 'true');
  clone.classList.add('team-card--expanded');
  clone.style.cssText = [
    'position:absolute',
    'left:-9999px',
    'top:0',
    `width:${side}px`,
    'height:auto',
    'min-height:0',
    'max-height:none',
    'overflow:visible',
    'opacity:0',
    'pointer-events:none',
    'transition:none',
    'z-index:-1'
  ].join(';');
  const bio = clone.querySelector('.team-card__bio');
  if (bio) {
    bio.style.maxHeight = 'none';
    bio.style.opacity = '1';
    bio.style.margin = '16px 0 0';
    bio.style.transition = 'none';
  }
  contentHost().appendChild(clone);
  const height = Math.ceil(clone.scrollHeight + 4);
  clone.remove();
  return height;
}

function squarePlan(card, grid, metrics) {
  const cards = visibleCards(grid);
  const index = cards.indexOf(card);
  const row = Math.floor(index / metrics.columns);
  const column = index % metrics.columns;
  const rows = rowCountFor(grid, metrics.columns);
  const basePlan = { row, column, rows };

  if (index < 0 || metrics.columns <= 1 || window.innerWidth <= ACCORDION_WIDTH || metrics.base < 180) {
    return { mode: 'accordion', ...basePlan };
  }

  const maxSide = Math.floor(metrics.available - MIN_SIBLING_TRACK * (metrics.columns - 1));
  const lower = Math.ceil(Math.max(metrics.base + 28, MIN_SQUARE_SIDE));
  if (maxSide < lower) return { mode: 'accordion', ...basePlan };

  if (measureCardHeightAtSide(card, maxSide) > maxSide) {
    return { mode: 'accordion', ...basePlan };
  }

  let lo = lower;
  let hi = maxSide;
  while (lo < hi) {
    const mid = Math.floor((lo + hi) / 2);
    if (measureCardHeightAtSide(card, mid) <= mid) hi = mid;
    else lo = mid + 1;
  }

  return {
    mode: 'square',
    side: Math.ceil(Math.max(lo, lower)),
    ...basePlan
  };
}

function deactivateCard(card) {
  if (!card) return;
  card.classList.remove('team-card--expanded');
  card.setAttribute('aria-expanded', 'false');
  card.style.removeProperty('--expanded-bio-height');
}

function markAnimating(grid, callback) {
  clearTimeout(animationTimer);
  const version = ++layoutVersion;
  grid.classList.add('team-grid--is-animating');
  animationTimer = window.setTimeout(() => {
    if (version !== layoutVersion) return;
    grid.classList.remove('team-grid--is-animating');
    if (callback) callback();
  }, motionMs(grid) + 40);
}

function collapse() {
  if (!expandedCard) return;
  const card = expandedCard;
  const grid = card.closest('.team-grid');
  clearTimeout(collapseTimer);
  expandedCard = null;
  deactivateCard(card);

  if (!grid) return;
  const metrics = setBaseSize(grid);
  grid.classList.remove('team-grid--accordion-mode', 'team-grid--has-expanded');
  grid.style.gridTemplateColumns = baseColumnTracks(metrics);
  grid.style.gridTemplateRows = rowTracks(rowCountFor(grid, metrics.columns), metrics.rowBase);
  markAnimating(grid, () => syncIdleGrid(grid));
}

function expand(card) {
  const grid = card.closest('.team-grid');
  if (!grid) return;

  if (expandedCard && expandedCard !== card) deactivateCard(expandedCard);

  const metrics = setBaseSize(grid);
  const plan = squarePlan(card, grid, metrics);
  const baseRows = rowTracks(plan.rows, metrics.rowBase);
  grid.classList.add('team-grid--has-expanded');
  grid.classList.toggle('team-grid--accordion-mode', plan.mode === 'accordion');

  expandedCard = card;
  card.setAttribute('aria-expanded', 'true');

  if (plan.mode === 'accordion') {
    grid.style.removeProperty('grid-template-columns');
    grid.style.removeProperty('grid-template-rows');
    setBioHeight(card, Math.max(metrics.base, card.getBoundingClientRect().width || metrics.base));
    card.classList.add('team-card--expanded');
  } else {
    grid.style.gridTemplateColumns = baseColumnTracks(metrics);
    grid.style.gridTemplateRows = baseRows;
    grid.getBoundingClientRect();

    setBioHeight(card, plan.side);
    card.classList.add('team-card--expanded');
    markAnimating(grid);

    requestAnimationFrame(() => {
      if (expandedCard !== card) return;
      grid.style.gridTemplateColumns = expandedColumnTracks(metrics, plan.column, plan.side);
      grid.style.gridTemplateRows = rowTracks(plan.rows, metrics.rowBase, plan.row, plan.side);
    });
  }

  clearTimeout(collapseTimer);
  collapseTimer = window.setTimeout(collapse, COLLAPSE_AFTER_MS);
}

function refreshExpandedCard() {
  if (expandedCard && expandedCard.classList.contains('is-filtered-out')) {
    collapse();
    return;
  }
  if (expandedCard) expand(expandedCard);
  else document.querySelectorAll('.team-grid').forEach(syncIdleGrid);
}

function onCardClick(event) {
  const card = event.target.closest('.team-card');
  if (!card || event.target.closest('a, button, .team-card__icon, .team-card__links')) return;
  event.preventDefault();
  if (card === expandedCard) collapse();
  else expand(card);
}

function onCardKeydown(event) {
  if (event.key === 'Escape') {
    collapse();
    return;
  }
  if (event.key !== 'Enter' && event.key !== ' ') return;
  if (event.target.closest('a, button, .team-card__icon, .team-card__links')) return;
  const card = event.target.closest('.team-card');
  if (!card) return;
  event.preventDefault();
  if (card === expandedCard) collapse();
  else expand(card);
}

async function loadPretext() {
  try {
    pretext = await import(PRETEXT_URL);
  } catch (error) {
    pretext = null;
  }
}

function initFilters() {
  const filters = Array.from(document.querySelectorAll('.team-filter'));
  const cards = Array.from(document.querySelectorAll('.team-card'));
  if (!filters.length || !cards.length) return;
  const active = new Set();

  function apply() {
    const showAll = active.size === 0;
    filters.forEach((button) => {
      const filter = button.getAttribute('data-filter');
      button.classList.toggle('is-active', showAll ? filter === '*' : active.has(filter));
    });
    cards.forEach((card) => {
      const tags = (card.getAttribute('data-tags') || '').split(/\s+/).filter(Boolean);
      const match = showAll || tags.some((tag) => active.has(tag));
      card.classList.toggle('is-filtered-out', !match);
    });
    requestAnimationFrame(refreshExpandedCard);
  }

  filters.forEach((button) => {
    button.addEventListener('click', () => {
      const filter = button.getAttribute('data-filter');
      if (filter === '*') active.clear();
      else if (active.has(filter)) active.delete(filter);
      else active.add(filter);
      apply();
    });
  });
}

function onResize() {
  cancelAnimationFrame(resizeFrame);
  resizeFrame = requestAnimationFrame(refreshExpandedCard);
}

async function init() {
  const cards = Array.from(document.querySelectorAll('.team-card'));
  if (!cards.length) return;
  cards.forEach((card) => {
    card.tabIndex = 0;
    card.setAttribute('aria-expanded', 'false');
  });
  if (document.fonts && document.fonts.ready) {
    try { await document.fonts.ready; } catch (error) {}
  }
  await loadPretext();
  document.querySelectorAll('.team-grid').forEach(syncIdleGrid);
  initFilters();
  document.addEventListener('click', onCardClick, true);
  document.addEventListener('keydown', onCardKeydown);
  window.addEventListener('resize', onResize, { passive: true });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
