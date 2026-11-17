// Mike Johnson for Logan — menu and forms.
(function () {
  var btn = document.querySelector('.menu-btn');
  var nav = document.getElementById('main-nav');
  if (btn && nav) {
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.textContent = open ? 'Close' : 'Menu';
    });
  }

  // Forms send without leaving the page (Web3Forms)
  document.querySelectorAll('form[data-ajax]').forEach(function (form) {
    if (!window.fetch) return;
    var status = form.querySelector('.form-status');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var b = form.querySelector('button[type="submit"]');
      var label = b.textContent;
      b.disabled = true; b.textContent = 'Sending…';
      fetch(form.action, { method: 'POST', body: new FormData(form), headers: { Accept: 'application/json' } })
        .then(function (r) { return r.json(); })
        .then(function (j) {
          if (!j.success) throw new Error(j.message || 'Error');
          form.reset();
          status.className = 'form-status ok';
          status.textContent = form.getAttribute('data-thanks') || 'Thank you!';
        })
        .catch(function () {
          status.className = 'form-status err';
          status.textContent = 'Sorry, something went wrong. Please email MikeForLogan@gmail.com or call 435-764-4241.';
        })
        .then(function () { b.disabled = false; b.textContent = label; });
    });
  });
})();
