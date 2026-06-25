const PRETEXT_URL = 'https://esm.sh/@chenglou/pretext@0.0.4';
const COLLAPSE_AFTER_MS = 30000;
const MIN_SIBLING_TRACK = 112;
const MIN_SQUARE_SIDE = 280;
const ACCORDION_WIDTH = 560;
const DORMANT_ROW_SIZE = 160;
const BIO_THREAD_INLINE_INSET = 16;
const INITIAL_EAGER_AVATARS = 12;
const AVATAR_PRELOAD_MARGIN = '1600px 0px';
const LAST_ORDER_STORAGE_KEY = 'alius-team-card-order-v1';

const DEFAULT_ACCENT = '#3d8b3d';
const TAG_ACCENTS = new Map([
  ['coordinators', '#8fbf4d'],
  ['in-memoriam', '#7b8c89'],
  ['psychedelics', '#6f8f3d'],
  ['dmt', '#2f8f83'],
  ['near-death-experiences', '#7c5aa6'],
  ['mystical-experiences', '#b68a35'],
  ['meditation', '#4f8a7b'],
  ['dreams-sleep', '#5b7fb8'],
  ['anthropology', '#a66a4c'],
  ['philosophy', '#6d6875'],
  ['neuroscience', '#2f7d62'],
  ['virtual-reality', '#4f6fb3'],
  ['hallucinations', '#9a6aa8'],
  ['psychiatry', '#8a6f3f'],
  ['computation', '#4d7f91'],
  ['interoception', '#b07156'],
  ['art-science', '#9a7a3f']
]);

let pretext = null;
let expandedCard = null;
let collapseTimer = 0;
let animationTimer = 0;
let resizeFrame = 0;
let layoutVersion = 0;
const preparedCache = new WeakMap();
const avatarDecodeCache = new WeakSet();

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

function hexToRgb(hex) {
  const match = String(hex || '').trim().match(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i);
  if (!match) return '61, 139, 61';
  return match.slice(1).map((part) => Number.parseInt(part, 16)).join(', ');
}

function cardAccent(card) {
  const tags = (card.getAttribute('data-tags') || '').split(/\s+/).filter(Boolean);
  const tag = tags.find((item) => TAG_ACCENTS.has(item));
  return TAG_ACCENTS.get(tag) || DEFAULT_ACCENT;
}

function applyCardAccent(card) {
  const accent = cardAccent(card);
  const rgb = hexToRgb(accent);
  card.style.setProperty('--team-accent', accent);
  card.style.setProperty('--team-accent-rgb', rgb);
  card.style.setProperty('--team-accent-soft', `rgba(${rgb}, 0.07)`);
}

function columnsFor(grid) {
  return trackList(getComputedStyle(grid).gridTemplateColumns).length || 1;
}

function visibleCards(grid) {
  return Array.from(grid.querySelectorAll('.team-card'))
    .filter((card) => !card.classList.contains('is-filtered-out'));
}

function randomFloat() {
  if (window.crypto && window.crypto.getRandomValues) {
    const values = new Uint32Array(1);
    window.crypto.getRandomValues(values);
    return values[0] / 0x100000000;
  }
  const seed = Date.now() + performance.now() + Math.random() * 1000000;
  return (Math.sin(seed) + 1) / 2;
}

function cardOrderKey(cards) {
  return cards
    .map((card) => card.id || card.querySelector('.team-card__name')?.textContent.trim() || '')
    .join('|');
}

function storedLastOrder() {
  try {
    return window.localStorage.getItem(LAST_ORDER_STORAGE_KEY);
  } catch (error) {
    return null;
  }
}

function rememberLastOrder(order) {
  try {
    window.localStorage.setItem(LAST_ORDER_STORAGE_KEY, order);
  } catch (error) {}
}

function shuffleCards(grid) {
  const cards = Array.from(grid.querySelectorAll('.team-card'));
  for (let index = cards.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(randomFloat() * (index + 1));
    [cards[index], cards[swapIndex]] = [cards[swapIndex], cards[index]];
  }
  if (cards.length > 1 && cardOrderKey(cards) === storedLastOrder()) {
    const rotation = Math.max(1, Math.floor(randomFloat() * cards.length));
    cards.push(...cards.splice(0, rotation));
  }
  cards.forEach((card) => grid.appendChild(card));
  rememberLastOrder(cardOrderKey(cards));
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
  const dormantRowSize = Number.parseFloat(style.getPropertyValue('--team-dormant-row-size')) || DORMANT_ROW_SIZE;
  const rect = grid.getBoundingClientRect();
  const available = Math.max(0, rect.width - paddingLeft - paddingRight - gap * Math.max(0, columns - 1));
  const base = Math.max(1, available / Math.max(1, columns));
  const rowBase = dormantRowSize;
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

function runWhenIdle(callback) {
  if ('requestIdleCallback' in window) {
    window.requestIdleCallback(callback, { timeout: 900 });
  } else {
    window.setTimeout(callback, 80);
  }
}

function prepareAvatarImage(img, priority = 'low') {
  if (!img || avatarDecodeCache.has(img)) return;
  avatarDecodeCache.add(img);

  img.loading = 'eager';
  img.decoding = 'async';
  img.setAttribute('fetchpriority', priority);
  if ('fetchPriority' in img) img.fetchPriority = priority;

  runWhenIdle(() => {
    if (img.decode) {
      img.decode().catch(() => {});
    }
  });
}

function initAvatarPreloading(cards) {
  const avatars = cards
    .map((card) => card.querySelector('.team-card__avatar img'))
    .filter(Boolean);
  if (!avatars.length) return;

  avatars.forEach((img, index) => {
    img.decoding = 'async';
    img.setAttribute('fetchpriority', index < INITIAL_EAGER_AVATARS ? 'high' : 'low');
  });

  avatars.slice(0, INITIAL_EAGER_AVATARS).forEach((img) => prepareAvatarImage(img, 'high'));

  if (!('IntersectionObserver' in window)) {
    runWhenIdle(() => avatars.slice(INITIAL_EAGER_AVATARS).forEach((img) => prepareAvatarImage(img)));
    return;
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      observer.unobserve(entry.target);
      prepareAvatarImage(entry.target);
    });
  }, { rootMargin: AVATAR_PRELOAD_MARGIN, threshold: 0 });

  avatars.slice(INITIAL_EAGER_AVATARS).forEach((img) => observer.observe(img));
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
    'box-sizing:border-box',
    'border-left:3px solid transparent',
    'padding:0 0 0 12px',
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
  const textWidth = Math.max(120, width - BIO_THREAD_INLINE_INSET);
  try {
    pretextHeight = measureWithPretext(bio, textWidth);
  } catch (error) {
    pretextHeight = null;
  }
  if (pretextHeight) return Math.ceil(pretextHeight + 2);
  return Math.ceil(measureWithDom(bio, width) + 2);
}

function setBioHeight(card, outerWidth) {
  const bio = card.querySelector('.team-card__bio');
  if (!bio) return;
  const innerWidth = inlineSizeInsideCard(card, outerWidth);
  card.style.setProperty('--expanded-bio-height', `${bioHeightAtWidth(card, innerWidth)}px`);
}

function setBioVisibility(card, visible) {
  const bio = card.querySelector('.team-card__bio');
  if (bio) bio.setAttribute('aria-hidden', visible ? 'false' : 'true');
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
  const lower = Math.ceil(Math.max(metrics.base, MIN_SQUARE_SIDE));
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
  setBioVisibility(card, false);
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
  setBioVisibility(card, true);

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
  document.querySelectorAll('.team-grid').forEach(shuffleCards);
  const cards = Array.from(document.querySelectorAll('.team-card'));
  if (!cards.length) return;
  cards.forEach((card) => {
    applyCardAccent(card);
    card.tabIndex = 0;
    card.setAttribute('aria-expanded', 'false');
    setBioVisibility(card, false);
  });
  initAvatarPreloading(cards);
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
