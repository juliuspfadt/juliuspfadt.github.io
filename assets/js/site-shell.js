(function () {
  var globalLastEdit = 'July 27, 2026';

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function isCurrentPage(href) {
    var pathname = window.location.pathname;
    if (!pathname) return href === '/';
    if (pathname === '/index.html') pathname = '/';
    return pathname === href;
  }

  function renderHeader() {
    var mount = document.getElementById('site-header');
    if (!mount) return;

    var siteTitle = document.body.getAttribute('data-site-title') || 'Julius M. Pfadt';
    var navLinks = [
      { href: '/publications.html', label: 'Publications' },
      { href: '/software.html', label: 'Software' },
      { href: '/talks.html', label: 'Talks' },
      { href: '/blog.html', label: 'Blog' }
    ];

    var navMarkup = navLinks.map(function (link) {
      var current = isCurrentPage(link.href);
      return '<a class="page-link" href="' + link.href + '"' +
        (current ? ' aria-current="page"' : '') +
        '>' + escapeHtml(link.label) + '</a>';
    }).join('');

    mount.outerHTML =
      '<header class="site-header" role="banner">' +
        '<div class="wrapper">' +
          '<a class="site-title" rel="author" href="/">' + escapeHtml(siteTitle) + '</a>' +
          '<nav class="site-nav">' +
            '<input type="checkbox" id="nav-trigger" class="nav-trigger">' +
            '<label for="nav-trigger">' +
              '<span class="menu-icon">' +
                '<svg viewBox="0 0 18 15" width="18px" height="15px">' +
                  '<path d="M18,1.484c0,0.82-0.665,1.484-1.484,1.484H1.484C0.665,2.969,0,2.304,0,1.484l0,0C0,0.665,0.665,0,1.484,0 h15.032C17.335,0,18,0.665,18,1.484L18,1.484z M18,7.516C18,8.335,17.335,9,16.516,9H1.484C0.665,9,0,8.335,0,7.516l0,0 c0-0.82,0.665-1.484,1.484-1.484h15.032C17.335,6.031,18,6.696,18,7.516L18,7.516z M18,13.516C18,14.335,17.335,15,16.516,15H1.484 C0.665,15,0,14.335,0,13.516l0,0c0-0.82,0.665-1.483,1.484-1.483h15.032C17.335,12.031,18,12.695,18,13.516L18,13.516z"/>' +
                '</svg>' +
              '</span>' +
            '</label>' +
            '<div class="trigger">' + navMarkup + '</div>' +
          '</nav>' +
        '</div>' +
      '</header>';
  }

  function renderFooter() {
    var mount = document.getElementById('site-footer');
    if (!mount) return;

    var lastEdit = globalLastEdit;
    var lastEditMarkup = lastEdit
      ? '<p class="contact-meta">last edit ' + escapeHtml(lastEdit) + '</p>'
      : '';

    mount.outerHTML =
      '<footer class="site-footer h-card">' +
        '<div class="wrapper">' +
          '<div class="footer-col-wrapper">' +
            '<div class="footer-col footer-col-1">' +
              '<ul class="contact-list">' +
                '<li class="p-name">' +
                  '<p class="contact-email"><b>julius.pfadt at gmail.com</b></p>' +
                  lastEditMarkup +
                '</li>' +
              '</ul>' +
            '</div>' +
            '<div class="footer-col footer-col-2">' +
              '<ul class="social-media-list">' +
                '<li><a href="https://github.com/juliuspfadt"><img alt="Github" src="/assets/images/github-mark.png" width="24" height="24"></a></li>' +
                '<li><a href="https://www.linkedin.com/in/julius-m-pfadt-8b8a45179"><img alt="LinkedIn" src="/assets/images/linkedin-logo.png" width="24" height="24"></a></li>' +
                '<li><a href="https://orcid.org/0000-0002-0758-5502"><img alt="ORCID" src="/assets/images/orcid.png" width="24" height="24"></a></li>' +
                '<li><a href="https://scholar.google.com/citations?user=Db1-WloAAAAJ&amp;hl=en"><img alt="Google Scholar" src="/assets/images/google-scholar_icon.png" width="24" height="24"></a></li>' +
                '<li><a href="https://www.researchgate.net/profile/Julius-Pfadt"><img alt="ResearchGate" src="/assets/images/researchgate.png" width="24" height="24"></a></li>' +
              '</ul>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</footer>';
  }

  renderHeader();
  renderFooter();
})();
