const PRETEXT_URL = 'https://esm.sh/@chenglou/pretext@0.0.4';
const EXPANDED_FR = 2.7;
const SHRUNK_FR = 0.65;
const COLLAPSE_AFTER_MS = 30000;

let pretext = null;
let expandedCard = null;
let collapseTimer = 0;
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

function columnsFor(grid) {
  return getComputedStyle(grid).gridTemplateColumns.split(/\s+/).filter(Boolean).length || 1;
}

function tracks(columns, selectedColumn) {
  return Array.from({ length: columns }, (_, index) => {
    const fr = index === selectedColumn ? EXPANDED_FR : SHRUNK_FR;
    return `minmax(0, ${fr}fr)`;
  }).join(' ');
}

function targetBioWidth(grid, columns) {
  const gridStyle = getComputedStyle(grid);
  const gap = Number.parseFloat(gridStyle.columnGap) || 0;
  const available = grid.getBoundingClientRect().width - gap * Math.max(0, columns - 1);
  const totalFr = EXPANDED_FR + SHRUNK_FR * Math.max(0, columns - 1);
  return Math.max(180, (available * EXPANDED_FR / totalFr) - 42);
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
    '-webkit-line-clamp:unset'
  ].join(';');
  document.body.appendChild(clone);
  const height = clone.scrollHeight;
  clone.remove();
  return height + 6;
}

function setBioHeight(card, grid, columns) {
  const bio = card.querySelector('.team-card__bio');
  if (!bio) return;
  const actualWidth = bio.getBoundingClientRect().width;
  const width = Math.max(180, actualWidth || targetBioWidth(grid, columns));
  let pretextHeight = null;
  try {
    pretextHeight = measureWithPretext(bio, width);
  } catch (error) {
    pretextHeight = null;
  }
  const domHeight = measureWithDom(bio, width);
  const height = Math.max(pretextHeight || 0, domHeight) + 24;
  card.style.setProperty('--expanded-bio-height', `${Math.ceil(height)}px`);
}

function collapse() {
  if (!expandedCard) return;
  const grid = expandedCard.closest('.team-grid');
  if (grid) {
    grid.style.removeProperty('grid-template-columns');
    grid.classList.remove('team-grid--has-expanded');
  }
  expandedCard.classList.remove('team-card--expanded');
  expandedCard.setAttribute('aria-expanded', 'false');
  expandedCard.style.removeProperty('--expanded-bio-height');
  expandedCard = null;
  clearTimeout(collapseTimer);
}

function expand(card) {
  const grid = card.closest('.team-grid');
  if (!grid) return;
  if (expandedCard && expandedCard !== card) collapse();
  const cards = Array.from(grid.querySelectorAll('.team-card'));
  const index = cards.indexOf(card);
  const columns = columnsFor(grid);
  if (columns > 1) {
    grid.style.gridTemplateColumns = tracks(columns, index % columns);
  }
  grid.classList.add('team-grid--has-expanded');
  card.classList.add('team-card--expanded');
  card.setAttribute('aria-expanded', 'true');
  setBioHeight(card, grid, columns);
  expandedCard = card;
  clearTimeout(collapseTimer);
  collapseTimer = window.setTimeout(collapse, COLLAPSE_AFTER_MS);
}

function onCardClick(event) {
  const card = event.target.closest('.team-card');
  if (!card || event.target.closest('a, .team-card__icon--email')) return;
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
      if (!match && card === expandedCard) collapse();
    });
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
  initFilters();
  document.addEventListener('click', onCardClick, true);
  document.addEventListener('keydown', onCardKeydown);
  window.addEventListener('resize', () => {
    if (!expandedCard) return;
    const card = expandedCard;
    collapse();
    requestAnimationFrame(() => expand(card));
  }, { passive: true });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
