/* AJR — medição de contatos (GA4 + Pixel da Meta)
   Conta como contato todo clique em link do WhatsApp (wa.me) e do Instagram.
   Para ligar o Pixel da Meta, preencha META_PIXEL_ID com o número do conjunto de dados. */
(function () {
  var GA_ID = 'G-MK8HJ8QF9G';
  var META_PIXEL_ID = '1456763829228525'; // conjunto de dados "AJR Site" (conta Aldemir01)

  // GA4: carrega só se a página ainda não tiver a tag
  if (typeof window.gtag !== 'function') {
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    document.head.appendChild(s);
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { dataLayer.push(arguments); };
    gtag('js', new Date());
    gtag('config', GA_ID);
  }

  // Pixel da Meta
  if (META_PIXEL_ID) {
    !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
    n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
    n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
    t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
    document,'script','https://connect.facebook.net/en_US/fbevents.js');
    fbq('init', META_PIXEL_ID);
    fbq('track', 'PageView');
  }

  function pagina() {
    var p = location.pathname.replace(/^\/|\.html$/g, '');
    return p || 'index';
  }

  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('a[href]');
    if (!a) return;
    var href = a.getAttribute('href') || '';
    var texto = (a.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 80);
    var plano = a.getAttribute('data-plan') || 'geral';
    var origem = a.getAttribute('data-source') || a.className || 'link';

    if (/wa\.me|api\.whatsapp\.com/i.test(href)) {
      gtag('event', 'whatsapp_click', {
        plan: plano, source: origem, link_text: texto, page: pagina(),
        transport_type: 'beacon'
      });
      if (window.fbq) fbq('track', 'Contact', { content_name: plano, content_category: pagina() });
    } else if (/instagram\.com/i.test(href)) {
      gtag('event', 'instagram_click', { source: origem, page: pagina(), transport_type: 'beacon' });
    }
  }, true);
})();
