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
      var normalized = typeof value === 'string' ? safeDiscordText(value) : value;
      if (normalized === '') return;
      if (payload[key]) {
        payload[key] = [].concat(payload[key], normalized);
      } else {
        payload[key] = normalized;
      }
    });
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

  function formatForFormBeeDiscord(form, payload) {
    var payloadKind = form.getAttribute('data-discord-payload');

    if (payloadKind === 'newsletter-signup') {
      return {
        Message: 'Please sign me up to the newsletter!',
        Name: payload.name || 'Anonymous',
        Email: payload.email || 'not provided'
      };
    }

    if (payloadKind !== 'news-item') return payload;

    return {
      Message: 'Please consider this item for the newsletter!',
      Title: payload.news_title || 'Untitled news item',
      'Item type': payload.news_type || 'not provided',
      Link: payload.news_url || 'not provided',
      'Submitted by': payload.submitter_name || 'Anonymous',
      'Submitter email': payload.submitter_email || 'not provided',
      Summary: payload.news_summary || 'No summary provided',
      'Why it matters': payload.relevance || 'No relevance note provided'
    };
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
      var payload = formatForFormBeeDiscord(form, collectPayload(form));
      var response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(String(response.status));
      }

      form.reset();
      setStatus(form, form.getAttribute('data-formbee-success') || 'Thank you. Your submission was received.', 'success');
    } catch (error) {
      var setupError = error && /^(404|405)$/.test(error.message || '');
      var rejectionError = error && /^(401|403)$/.test(error.message || '');
      setStatus(
        form,
        setupError
          ? 'This form still needs its FormBee webhook endpoint to be connected.'
          : rejectionError
            ? 'FormBee is rejecting this form. Check the API key and allowed domains.'
          : 'The submission could not be sent. Please try again later.',
        'error'
      );
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
