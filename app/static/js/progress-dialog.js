/* Loading/progress dialog for every action button.
 *
 * Buttons opt in with data-progress="Judul". Form submits and job watchers
 * then open one native <dialog> and keep it in sync with the server-side job
 * registry, so the progress numbers are the worker's real counters.
 */
(function () {
  'use strict';

  var dialog = document.getElementById('progress-dialog');
  var title = document.getElementById('progress-title');
  var message = document.getElementById('progress-message');
  var bar = document.getElementById('progress-bar');
  var closeButton = document.getElementById('progress-close');
  if (!dialog || !title || !message || !bar) {
    return;
  }

  var pollTimer = null;

  function show(heading, text) {
    title.textContent = heading || 'Memproses';
    message.textContent = text || 'Menyiapkan permintaan…';
    bar.hidden = true;
    bar.value = 0;
    bar.max = 100;
    if (closeButton) {
      closeButton.disabled = true;
    }
    if (!dialog.open) {
      if (typeof dialog.showModal === 'function') {
        dialog.showModal();
      } else {
        dialog.setAttribute('open', '');
      }
    }
  }

  function finish(text, failed) {
    message.textContent = text;
    bar.hidden = true;
    if (closeButton) {
      closeButton.disabled = false;
    }
    if (failed) {
      title.textContent = 'Gagal';
    }
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function describe(job) {
    if (job.status === 'queued') {
      return job.message || 'Menunggu antrean…';
    }
    var total = job.total || 0;
    var done = job.done || 0;
    if (!total) {
      return job.message || 'Memproses…';
    }
    var percent = Math.round((done / total) * 100);
    return done + ' dari ' + total + ' (' + percent + '%)';
  }

  function watch(jobId, heading) {
    show(heading, 'Menunggu antrean…');
    bar.hidden = false;
    bar.max = 100;
    bar.value = 0;
    stopPolling();

    function tick() {
      fetch('/preprocessing/jobs/' + encodeURIComponent(jobId), {
        headers: { Accept: 'application/json' },
        credentials: 'same-origin'
      })
        .then(function (response) {
          if (!response.ok) {
            throw new Error('job ' + response.status);
          }
          return response.json();
        })
        .then(function (job) {
          message.textContent = describe(job);
          if (job.total) {
            bar.max = job.total;
            bar.value = job.done || 0;
          }
          if (job.status === 'completed') {
            stopPolling();
            message.textContent = 'Selesai. Memuat ulang halaman…';
            // Drop the job parameter first, otherwise the reloaded page would
            // watch the same finished job and reload again, forever.
            var next = new URL(window.location.href);
            next.searchParams.delete('job');
            window.location.replace(next.toString());
          } else if (job.status === 'failed') {
            stopPolling();
            finish(job.message || 'Job gagal diproses.', true);
          }
        })
        .catch(function () {
          stopPolling();
          finish('Status job tidak dapat dibaca. Muat ulang halaman untuk melihat hasilnya.', true);
        });
    }

    tick();
    pollTimer = setInterval(tick, 800);
  }

  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!form || form.dataset.noProgress === 'true') {
      return;
    }
    var button = form.querySelector('[data-progress]');
    var heading = button ? button.dataset.progress : (form.dataset.progress || 'Memproses');
    show(heading, form.method && form.method.toLowerCase() === 'get'
      ? 'Memuat data…'
      : 'Mengirim permintaan…');
  });

  var watcher = document.querySelector('[data-job-watch]');
  if (watcher) {
    watch(watcher.dataset.jobWatch, watcher.dataset.jobHeading || 'Memproses dataset');
  }

  window.hermesProgress = { show: show, watch: watch, finish: finish };
})();
