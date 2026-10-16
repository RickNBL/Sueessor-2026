"use strict";
const moments = [
    { year: '2002', label: 'Fundação', title: 'O início de uma história coletiva', detail: 'Em 12 de abril, o SUEESSOR é fundado e começa a prestar atendimento odontológico aos associados.' },
    { year: '2005', label: 'Assistência ampliada', title: 'Mais serviços para a categoria', detail: 'O sindicato passa a oferecer apoio jurídico aos associados e amplia sua participação em seminários e palestras.' },
    { year: '2007', label: 'Sede própria', title: 'Uma conquista importante', detail: 'O sindicato conquista sua sede própria, fortalecendo as condições de organização e atendimento à categoria.' },
    { year: 'Hoje', label: 'Uma luta contínua', title: 'O compromisso permanece', detail: 'O SUEESSOR segue na defesa dos direitos e na representação dos trabalhadores da saúde de Osasco e região.' },
];
const root = document.querySelector('[data-timeline]');
if (root) {
    const markers = Array.from(root.querySelectorAll('[data-heritage-index]'));
    const year = root.querySelector('[data-heritage-year]');
    const title = root.querySelector('[data-heritage-title]');
    const detail = root.querySelector('[data-heritage-description]');
    const label = root.querySelector('[data-heritage-current]');
    const progress = root.querySelector('[data-heritage-progress]');
    const previous = root.querySelector('[data-heritage-prev]');
    const next = root.querySelector('[data-heritage-next]');
    let active = 0;
    const setMoment = (index) => {
        active = (index + moments.length) % moments.length;
        const moment = moments[active];
        if (year)
            year.textContent = moment.year;
        if (title)
            title.textContent = moment.title;
        if (detail)
            detail.textContent = moment.detail;
        if (label)
            label.textContent = moment.label;
        if (progress)
            progress.style.width = `calc((100% - 30px) * ${active / (moments.length - 1)})`;
        markers.forEach((button, i) => {
            const selected = i === active;
            button.classList.toggle('active', selected);
            button.setAttribute('aria-pressed', String(selected));
            button.tabIndex = selected ? 0 : -1;
        });
    };
    markers.forEach((button, index) => {
        button.addEventListener('click', () => setMoment(index));
        button.addEventListener('keydown', (event) => {
            if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
                event.preventDefault();
                const step = event.key === 'ArrowRight' ? 1 : -1;
                setMoment(index + step);
                markers[active]?.focus();
            }
            else if (event.key === 'Home') {
                event.preventDefault();
                setMoment(0);
                markers[0]?.focus();
            }
            else if (event.key === 'End') {
                event.preventDefault();
                setMoment(moments.length - 1);
                markers[active]?.focus();
            }
        });
    });
    previous?.addEventListener('click', () => setMoment(active - 1));
    next?.addEventListener('click', () => setMoment(active + 1));
    setMoment(0);
    // A linha progride suavemente quando a seção é vista pela primeira vez.
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reducedMotion && 'IntersectionObserver' in window) {
        const observer = new IntersectionObserver(entries => {
            if (entries.some(entry => entry.isIntersecting)) {
                root.classList.add('is-visible');
                observer.disconnect();
            }
        }, { threshold: 0.2 });
        observer.observe(root);
    }
    else {
        root.classList.add('is-visible');
    }
}
