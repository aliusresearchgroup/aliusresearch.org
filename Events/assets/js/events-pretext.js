const PRETEXT_URL = 'https://esm.sh/@chenglou/pretext@0.0.4';
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
  const size = Number.parseFloat(style.fontSize) || 15;
  return size * 1.58;
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
  return Math.max(result.height, lineHeightPx(bio)) + 8;
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
    'margin-top:10px',
    'overflow:visible'
  ].join(';');
  document.body.appendChild(clone);
  const height = clone.scrollHeight;
  clone.remove();
  return height + 8;
}

function setBioHeight(card) {
  const bio = card.querySelector('.event-speaker-card__bio');
  if (!bio) return;
  const width = Math.max(190, bio.getBoundingClientRect().width || card.getBoundingClientRect().width - 120);
  let pretextHeight = null;
  try {
    pretextHeight = measureWithPretext(bio, width);
  } catch (error) {
    pretextHeight = null;
  }
  const domHeight = measureWithDom(bio, width);
  const height = Math.max(pretextHeight || 0, domHeight) + 12;
  card.style.setProperty('--event-bio-height', `${Math.ceil(height)}px`);
}

function setHint(card, text) {
  const hint = card.querySelector('.event-speaker-card__hint');
  if (hint) hint.textContent = text;
}

function collapse() {
  if (!expandedCard) return;
  expandedCard.classList.remove('is-expanded');
  expandedCard.setAttribute('aria-expanded', 'false');
  expandedCard.style.removeProperty('--event-bio-height');
  setHint(expandedCard, 'Expand bio');
  expandedCard = null;
  clearTimeout(collapseTimer);
}

function expand(card) {
  if (expandedCard && expandedCard !== card) collapse();
  card.classList.add('is-expanded');
  card.setAttribute('aria-expanded', 'true');
  setBioHeight(card);
  setHint(card, 'Collapse bio');
  expandedCard = card;
  clearTimeout(collapseTimer);
  collapseTimer = window.setTimeout(collapse, COLLAPSE_AFTER_MS);
}

function toggle(card) {
  if (card === expandedCard) collapse();
  else expand(card);
}

function onClick(event) {
  const card = event.target.closest && event.target.closest('.event-speaker-card');
  if (!card) return;
  toggle(card);
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    collapse();
    return;
  }
  if (event.key !== 'Enter' && event.key !== ' ') return;
  const card = event.target.closest && event.target.closest('.event-speaker-card');
  if (!card) return;
  event.preventDefault();
  toggle(card);
}

async function loadPretext() {
  try {
    pretext = await import(PRETEXT_URL);
  } catch (error) {
    pretext = null;
  }
}

async function init() {
  const cards = Array.from(document.querySelectorAll('.event-speaker-card'));
  if (!cards.length) return;
  cards.forEach((card) => card.setAttribute('aria-expanded', 'false'));
  if (document.fonts && document.fonts.ready) {
    try { await document.fonts.ready; } catch (error) {}
  }
  await loadPretext();
  document.addEventListener('click', onClick, true);
  document.addEventListener('keydown', onKeydown);
  window.addEventListener('resize', () => {
    if (!expandedCard) return;
    setBioHeight(expandedCard);
  }, { passive: true });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
