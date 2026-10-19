/* Benefícios: feedback de clique e carrossel da clínica. */
(() => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  document.querySelectorAll('[data-benefit-card]').forEach((card) => {
    card.addEventListener('click', (event) => {
      if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      if (reduceMotion.matches) return;
      if (card.dataset.navigating === 'true') { event.preventDefault(); return; }
      event.preventDefault();
      card.dataset.navigating = 'true';
      card.classList.add('benefit-card-clicked');
      const target = card.href;
      window.setTimeout(() => { window.location.assign(target); }, 370);
    });
  });

  document.querySelectorAll('[data-clinic-carousel]').forEach((carousel) => {
    const slides = Array.from(carousel.querySelectorAll('[data-clinic-slide]'));
    const dots = Array.from(carousel.querySelectorAll('[data-clinic-dot]'));
    const nextBtn = carousel.querySelector('[data-clinic-next]');
    const prevBtn = carousel.querySelector('[data-clinic-prev]');
    const interval = Number(carousel.dataset.interval || 5000);
    if (!slides.length) return;

    let active = 0;
    let timer = null;
    let paused = false;

    const update = (index) => {
      active = (index + slides.length) % slides.length;
      slides.forEach((slide, slideIndex) => {
        const isActive = slideIndex === active;
        slide.classList.toggle('is-active', isActive);
        slide.setAttribute('aria-hidden', String(!isActive));
      });
      dots.forEach((dot, dotIndex) => {
        const isActive = dotIndex === active;
        dot.classList.toggle('is-active', isActive);
        dot.setAttribute('aria-selected', String(isActive));
      });
    };

    const start = () => {
      if (reduceMotion.matches || paused || slides.length < 2) return;
      stop();
      timer = window.setInterval(() => update(active + 1), interval);
    };

    const stop = () => {
      if (timer) window.clearInterval(timer);
      timer = null;
    };

    const pause = () => { paused = true; stop(); };
    const resume = () => { paused = false; start(); };

    nextBtn?.addEventListener('click', () => { update(active + 1); start(); });
    prevBtn?.addEventListener('click', () => { update(active - 1); start(); });
    dots.forEach((dot, index) => dot.addEventListener('click', () => { update(index); start(); }));
    carousel.addEventListener('mouseenter', pause);
    carousel.addEventListener('mouseleave', resume);
    carousel.addEventListener('focusin', pause);
    carousel.addEventListener('focusout', () => {
      const focusedInside = carousel.contains(document.activeElement);
      if (!focusedInside) resume();
    });

    let touchStartX = 0;
    let touchDeltaX = 0;
    carousel.addEventListener('touchstart', (event) => {
      touchStartX = event.changedTouches[0]?.clientX || 0;
      touchDeltaX = 0;
    }, {passive: true});
    carousel.addEventListener('touchmove', (event) => {
      touchDeltaX = (event.changedTouches[0]?.clientX || 0) - touchStartX;
    }, {passive: true});
    carousel.addEventListener('touchend', () => {
      if (Math.abs(touchDeltaX) > 45) {
        update(active + (touchDeltaX < 0 ? 1 : -1));
        start();
      }
    });

    const observer = 'IntersectionObserver' in window ? new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          if (!paused) start();
        } else {
          stop();
        }
      });
    }, {threshold: 0.45}) : null;

    if (observer) observer.observe(carousel);
    update(0);
    start();
  });
})();
