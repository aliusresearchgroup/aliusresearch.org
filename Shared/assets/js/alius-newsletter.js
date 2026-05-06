(function () {
  'use strict';

  var endpoints = window.ALIUS_FORMBEE_ENDPOINTS || {};
  var placeholderPattern = /REPLACE_WITH_|YOUR_|FORMBEE_/i;

  function fieldValue(form, name) {
    var field = form.elements[name];
    return field && field.value ? field.value.trim() : '';
  }

  function normalizeEmail(value) {
    return String(value || '').trim().toLowerCase();
  }

  function safeDiscordText(value) {
    return String(value || '')
      .replace(/@(everyone|here)/gi, '@ $1')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function endpointFor(form) {
    var key = form.getAttribute('data-formbee-key') || '';
    return (key && endpoints[key]) || form.getAttribute('action') || '';
  }

  function setStatus(form, message, tone) {
    var status = form.querySelector('[data-form-status]');
    if (!status) return;
    status.textContent = message;
    status.setAttribute('data-tone', tone || '');
  }

  function setBusy(form, busy) {
    var button = form.querySelector('button[type="submit"]');
    if (!button) return;
    button.disabled = busy;
    button.textContent = busy ? 'Sending...' : (button.getAttribute('data-label') || 'Submit');
  }

  function collectPayload(form) {
    var data = new FormData(form);
    var payload = {};
    data.forEach(function (value, key) {
      if (key === 'website') return;
      if (key === 'email_confirm') return;
      var normalized = typeof value === 'string' ? value.trim() : value;
      if (normalized === '') return;
      if (payload[key]) {
        payload[key] = [].concat(payload[key], normalized);
      } else {
        payload[key] = normalized;
      }
    });
    payload.submitted_at = new Date().toISOString();
    payload.source_url = window.location.href;
    return payload;
  }

  function validateEmailConfirmation(form) {
    if (!form.elements.email_confirm) return true;

    var email = normalizeEmail(fieldValue(form, 'email'));
    var emailConfirm = normalizeEmail(fieldValue(form, 'email_confirm'));
    if (email && emailConfirm && email === emailConfirm) return true;

    setStatus(form, 'Please type the same email address in both fields.', 'error');
    return false;
  }

  function addDiscordMessage(form, payload) {
    var payloadKind = form.getAttribute('data-discord-payload');

    if (payloadKind === 'newsletter-signup') {
      var signupName = safeDiscordText(payload.name || 'Anonymous');
      var signupEmail = safeDiscordText(payload.email || 'not provided');
      payload.content = [
        '**Newsletter email signup**',
        '**Name:** ' + signupName,
        '**Email:** ' + signupEmail
      ].join('\n').slice(0, 1900);
      payload.allowed_mentions = { parse: [] };
      return payload;
    }

    if (payloadKind !== 'news-item') return payload;

    var title = safeDiscordText(payload.news_title || 'Untitled news item');
    var submitter = safeDiscordText(payload.submitter_name || 'Anonymous');
    var email = safeDiscordText(payload.submitter_email || 'not provided');
    var itemUrl = safeDiscordText(payload.news_url || 'not provided');
    var summary = safeDiscordText(payload.news_summary || 'No summary provided');
    var relevance = safeDiscordText(payload.relevance || 'No relevance note provided');

    payload.content = [
      '**Newsletter news item submission**',
      '**Title:** ' + title,
      '**Submitted by:** ' + submitter + ' (' + email + ')',
      '**Link:** ' + itemUrl,
      '**Summary:** ' + summary,
      '**Why it matters:** ' + relevance
    ].join('\n').slice(0, 1900);
    payload.allowed_mentions = { parse: [] };
    return payload;
  }

  async function submitForm(form) {
    var endpoint = endpointFor(form);
    if (!endpoint || placeholderPattern.test(endpoint)) {
      setStatus(form, 'This form is waiting for its FormBee endpoint.', 'error');
      return;
    }

    if (fieldValue(form, 'website')) {
      form.reset();
      setStatus(form, form.getAttribute('data-formbee-success') || 'Thank you.', 'success');
      return;
    }

    if (!validateEmailConfirmation(form)) return;

    setBusy(form, true);
    setStatus(form, '', '');

    try {
      var payload = addDiscordMessage(form, collectPayload(form));
      var response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error('FormBee returned ' + response.status);
      }

      form.reset();
      setStatus(form, form.getAttribute('data-formbee-success') || 'Thank you. Your submission was received.', 'success');
    } catch (error) {
      setStatus(form, 'The submission could not be sent. Please try again later.', 'error');
    } finally {
      setBusy(form, false);
    }
  }

  function init() {
    var forms = Array.prototype.slice.call(document.querySelectorAll('[data-formbee-form]'));
    forms.forEach(function (form) {
      var button = form.querySelector('button[type="submit"]');
      if (button) button.setAttribute('data-label', button.textContent);
      form.addEventListener('submit', function (event) {
        event.preventDefault();
        submitForm(form);
      });

      Array.prototype.slice.call(form.querySelectorAll('[data-no-paste]')).forEach(function (field) {
        ['paste', 'drop'].forEach(function (eventName) {
          field.addEventListener(eventName, function (event) {
            event.preventDefault();
            setStatus(form, 'Please type the email address manually.', 'error');
          });
        });
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
