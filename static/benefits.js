/* Cards de benefícios: feedback de clique antes da navegação. Links funcionam sem JS. */
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
})();
