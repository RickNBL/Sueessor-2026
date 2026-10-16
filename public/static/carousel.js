"use strict";
/** Destaques SUEESSOR: acessível, responsivo, com autoplay controlável e gesto de toque. */
const carousel = document.querySelector('[data-promo-carousel]');
if (carousel) {
    const slides = Array.from(carousel.querySelectorAll('[data-promo-slide]'));
    const dots = Array.from(carousel.querySelectorAll('[data-promo-dot]'));
    const prev = document.querySelector('[data-promo-prev]');
    const next = document.querySelector('[data-promo-next]');
    const zoom = carousel.querySelector('[data-promo-zoom]');
    const playButton = carousel.querySelector('[data-promo-play]');
    const playLabel = carousel.querySelector('[data-promo-play-label]');
    const announcement = carousel.querySelector('[data-promo-announcement]');
    const lightbox = document.querySelector('[data-promo-lightbox]');
    const zoomImage = lightbox?.querySelector('[data-promo-zoom-image]');
    const closeZoom = lightbox?.querySelector('[data-promo-close]');
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const intervalMs = 7500;
    let active = 0;
    let auto = !prefersReducedMotion;
    let inView = false;
    let hovered = false;
    let focused = false;
    let timer;
    let touchX = 0;
    let touchY = 0;
    let suppressClick = false;
    function setActive(index, announce = false) {
        active = (index + slides.length) % slides.length;
        slides.forEach((slide, i) => {
            const selected = i === active;
            slide.classList.toggle('is-active', selected);
            slide.setAttribute('aria-hidden', String(!selected));
            const link = slide.querySelector('a');
            if (link)
                link.tabIndex = selected ? 0 : -1;
        });
        dots.forEach((dot, i) => {
            dot.classList.toggle('is-active', i === active);
            dot.setAttribute('aria-pressed', String(i === active));
        });
        if (announce && announcement)
            announcement.textContent = slides[active].getAttribute('aria-label') || '';
    }
    function updatePlayButton() {
        if (!playButton || !playLabel)
            return;
        playLabel.textContent = auto ? 'Pausar' : 'Reproduzir';
        playButton.setAttribute('aria-label', auto ? 'Pausar passagem automática dos destaques' : 'Retomar passagem automática dos destaques');
        const symbol = playButton.querySelector('span[aria-hidden]');
        if (symbol)
            symbol.textContent = auto ? 'Ⅱ' : '▶';
    }
    function schedule() {
        window.clearTimeout(timer);
        if (!auto || !inView || document.hidden || hovered || focused || lightbox?.open)
            return;
        timer = window.setTimeout(() => { setActive(active + 1); schedule(); }, intervalMs);
    }
    function navigate(delta) {
        setActive(active + delta, true);
        schedule();
    }
    prev?.addEventListener('click', () => navigate(-1));
    next?.addEventListener('click', () => navigate(1));
    dots.forEach((dot, index) => dot.addEventListener('click', () => { setActive(index, true); schedule(); }));
    carousel.addEventListener('pointerenter', () => { hovered = true; schedule(); });
    carousel.addEventListener('pointerleave', () => { hovered = false; schedule(); });
    carousel.addEventListener('focusin', () => { focused = true; schedule(); });
    carousel.addEventListener('focusout', event => {
        if (!carousel.contains(event.relatedTarget)) {
            focused = false;
            schedule();
        }
    });
    carousel.addEventListener('keydown', event => {
        if (event.key === 'ArrowLeft') {
            event.preventDefault();
            navigate(-1);
        }
        if (event.key === 'ArrowRight') {
            event.preventDefault();
            navigate(1);
        }
    });
    carousel.addEventListener('touchstart', event => {
        touchX = event.changedTouches[0].clientX;
        touchY = event.changedTouches[0].clientY;
    }, { passive: true });
    carousel.addEventListener('touchend', event => {
        const dx = event.changedTouches[0].clientX - touchX;
        const dy = event.changedTouches[0].clientY - touchY;
        if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.3) {
            suppressClick = true;
            navigate(dx < 0 ? 1 : -1);
            window.setTimeout(() => { suppressClick = false; }, 400);
        }
    }, { passive: true });
    carousel.addEventListener('click', event => {
        if (suppressClick && event.target.closest('.promo-slide a')) {
            event.preventDefault();
            event.stopPropagation();
            suppressClick = false;
        }
    }, true);
    playButton?.addEventListener('click', () => { auto = !auto; updatePlayButton(); schedule(); });
    zoom?.addEventListener('click', () => {
        const image = slides[active].querySelector('img');
        if (!image || !zoomImage || !lightbox)
            return;
        zoomImage.src = image.currentSrc || image.src;
        zoomImage.alt = image.alt;
        lightbox.showModal();
        schedule();
    });
    closeZoom?.addEventListener('click', () => lightbox?.close());
    lightbox?.addEventListener('click', event => { if (event.target === lightbox)
        lightbox.close(); });
    lightbox?.addEventListener('close', schedule);
    document.addEventListener('visibilitychange', schedule);
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(entries => {
            inView = entries[0].isIntersecting;
            schedule();
        }, { threshold: 0.45 });
        observer.observe(carousel);
    }
    else {
        inView = true;
    }
    updatePlayButton();
    setActive(0);
    schedule();
}
