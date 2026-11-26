(function () {
  'use strict';

  var wrap = document.querySelector('[data-prediction-values]');
  var canvas = document.getElementById('prediction-chart');
  if (!wrap || !canvas || typeof Chart === 'undefined') return;

  var values = wrap.dataset.predictionValues.split(',').map(Number);
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: ['Positif', 'Netral', 'Negatif'],
      datasets: [{
        data: values,
        backgroundColor: ['#10B981', '#F59E0B', '#EF4444'],
        borderRadius: 6,
        maxBarThickness: 64
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (context) {
              var total = context.dataset.data.reduce(function (sum, value) { return sum + value; }, 0);
              var percent = total ? Math.round(context.raw / total * 100) : 0;
              return context.label + ': ' + context.raw + ' (' + percent + '%)';
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { precision: 0 },
          grid: { color: 'rgba(23,27,32,.08)' }
        },
        x: { grid: { display: false } }
      }
    }
  });
})();
