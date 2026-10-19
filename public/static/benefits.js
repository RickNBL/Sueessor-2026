/* Carrosséis dos benefícios: sem dependências e com ciclo de 5 s.
   A mesma versão está em static/ e public/static/ para funcionar na Vercel. */
(() => {
  'use strict';
  function init() {
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    document.querySelectorAll('[data-benefit-card]').forEach((card) => {
      card.addEventListener('click', (event) => {
        if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        if (reducedMotion.matches) return;
        if (card.dataset.navigating === 'true') { event.preventDefault(); return; }
        event.preventDefault();
        card.dataset.navigating = 'true';
        card.classList.add('benefit-card-clicked');
        const target = card.href;
        window.setTimeout(() => window.location.assign(target), 370);
      });
    });

    document.querySelectorAll('[data-clinic-carousel]').forEach((root) => {
      const slides = [...root.querySelectorAll('[data-clinic-slide]')];
      const dots = [...root.querySelectorAll('[data-clinic-dot]')];
      if (!slides.length) return;

      const delay = Math.max(1500, Number(root.dataset.interval) || 5000);
      const prev = root.querySelector('[data-clinic-prev]');
      const next = root.querySelector('[data-clinic-next]');
      let active = 0;
      let timer = null;
      let hovered = false;
      let focused = false;
      let inView = !('IntersectionObserver' in window);

      const render = (index) => {
        active = (index + slides.length) % slides.length;
        slides.forEach((slide, n) => {
          const current = n === active;
          slide.classList.toggle('is-active', current);
          slide.setAttribute('aria-hidden', String(!current));
        });
        dots.forEach((dot, n) => {
          const current = n === active;
          dot.classList.toggle('is-active', current);
          dot.setAttribute('aria-pressed', String(current));
        });
      };

      const stop = () => {
        if (timer !== null) window.clearInterval(timer);
        timer = null;
      };
      const canPlay = () => slides.length > 1 && inView && !document.hidden && !reducedMotion.matches && !hovered && !focused;
      const start = () => {
        stop();
        if (canPlay()) timer = window.setInterval(() => render(active + 1), delay);
      };
      const move = (delta) => { render(active + delta); start(); };

      prev?.addEventListener('click', () => move(-1));
      next?.addEventListener('click', () => move(1));
      dots.forEach((dot, n) => dot.addEventListener('click', () => { render(n); start(); }));

      root.addEventListener('mouseenter', () => { hovered = true; stop(); });
      root.addEventListener('mouseleave', () => { hovered = false; start(); });
      root.addEventListener('focusin', () => { focused = true; stop(); });
      root.addEventListener('focusout', () => {
        window.setTimeout(() => { focused = root.contains(document.activeElement); start(); }, 0);
      });
      document.addEventListener('visibilitychange', start);
      reducedMotion.addEventListener?.('change', start);

      let touchX = null;
      root.addEventListener('touchstart', (event) => { touchX = event.changedTouches[0]?.clientX ?? null; }, {passive:true});
      root.addEventListener('touchend', (event) => {
        if (touchX === null) return;
        const distance = (event.changedTouches[0]?.clientX ?? touchX) - touchX;
        touchX = null;
        if (Math.abs(distance) >= 40) move(distance < 0 ? 1 : -1);
      }, {passive:true});

      if ('IntersectionObserver' in window) {
        new IntersectionObserver((entries) => {
          inView = entries.some(e => e.isIntersecting);
          start();
        }, { threshold: 0.15 }).observe(root);
      }
      render(0);
      start();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
})();
