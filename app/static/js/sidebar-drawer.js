/* Drawer sidebar mobile: default tertutup tiap halaman, dibuka dari tombol
 * hamburger, ditutup via backdrop, Escape, dan navigasi. Desktop tak berubah. */
(function () {
  'use strict';
  var toggle = document.getElementById('sidebar-toggle');
  var sidebar = document.getElementById('sidebar');
  var backdrop = document.getElementById('sidebar-backdrop');
  if (!toggle || !sidebar || !backdrop) return;
  function setOpen(open) {
    sidebar.classList.toggle('drawer-open', open);
    backdrop.hidden = !open;
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    toggle.setAttribute('aria-label', open ? 'Tutup menu' : 'Buka menu');
  }
  toggle.addEventListener('click', function () {
    setOpen(!sidebar.classList.contains('drawer-open'));
  });
  backdrop.addEventListener('click', function () { setOpen(false); });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') setOpen(false);
  });
  sidebar.addEventListener('click', function (event) {
    if (event.target.closest('a')) setOpen(false);
  });
  window.addEventListener('resize', function () {
    if (window.innerWidth > 760) setOpen(false);
  });
})();
