(function () {
  'use strict';

  var dialog = document.getElementById('upload-dataset-dialog');
  var openButton = document.querySelector('[data-upload-open]');
  var closeButtons = document.querySelectorAll('[data-upload-close]');
  var previousFocus = null;

  function openDialog() {
    if (!dialog || dialog.open) return;
    previousFocus = document.activeElement;
    dialog.showModal();
    var fileInput = dialog.querySelector('input[type="file"]');
    if (fileInput) fileInput.focus();
  }

  function closeDialog() {
    if (dialog && dialog.open) dialog.close();
  }

  if (openButton) openButton.addEventListener('click', openDialog);
  closeButtons.forEach(function (button) {
    button.addEventListener('click', closeDialog);
  });
  if (dialog) {
    dialog.addEventListener('close', function () {
      if (previousFocus && previousFocus.focus) previousFocus.focus();
    });
    if (dialog.hasAttribute('data-auto-open')) openDialog();
  }

  var chartWrap = document.querySelector('[data-chart-values]');
  var canvas = document.getElementById('sentiment-chart');
  if (!chartWrap || !canvas || typeof Chart === 'undefined') return;
  var values = chartWrap.dataset.chartValues.split(',').map(Number);
  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Positif', 'Netral', 'Negatif'],
      datasets: [{
        data: values,
        backgroundColor: ['#287a57', '#8a949e', '#a64040'],
        borderColor: '#ffffff',
        borderWidth: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '66%',
      plugins: {
        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 18 } },
        tooltip: {
          callbacks: {
            label: function (context) {
              var total = context.dataset.data.reduce(function (sum, value) { return sum + value; }, 0);
              var percent = total ? Math.round(context.raw / total * 100) : 0;
              return context.label + ': ' + context.raw + ' (' + percent + '%)';
            }
          }
        }
      }
    }
  });
})();
