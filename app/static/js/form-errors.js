/* Fokus aksesibilitas setelah submit gagal: ke ringkasan error global bila
 * ada, jika tidak ke field invalid pertama. Error per field tetap inline. */
(function () {
  'use strict';
  var summary = document.querySelector('[data-error-summary]');
  if (summary) {
    summary.focus();
    return;
  }
  var firstInvalid = document.querySelector('[aria-invalid=true]');
  if (firstInvalid && firstInvalid.focus) firstInvalid.focus();
})();
