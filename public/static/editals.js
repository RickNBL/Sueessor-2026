/* Editais SUEESSOR — filtros, grupos de ano e linhas acessíveis. */
(() => {
  const root = document.querySelector('[data-edital-groups]');
  if (!root) return;

  const search = document.querySelector('[data-edital-search]');
  const year = document.querySelector('[data-edital-year]');
  const name = document.querySelector('[data-edital-name]');
  const count = document.querySelector('[data-edital-count]');
  const empty = document.querySelector('[data-edital-empty]');
  const groups = Array.from(root.querySelectorAll('[data-edital-group]'));
  const normalize = (value) => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR').trim();
  let lastFilterActive = false;

  const applyFilters = () => {
    const term = normalize(search.value);
    const selectedYear = year.value;
    const selectedName = normalize(name.value);
    const filtering = Boolean(term || selectedYear || selectedName);
    let visibleTotal = 0;

    groups.forEach((group) => {
      const rows = Array.from(group.querySelectorAll('[data-edital-row]'));
      let visible = 0;
      rows.forEach((row) => {
        const detail = row.nextElementSibling;
        const match = (!selectedYear || row.dataset.year === selectedYear)
          && (!selectedName || normalize(row.dataset.name) === selectedName)
          && (!term || normalize(row.dataset.search).includes(term));
        row.hidden = !match;
        if (!match && detail?.matches('[data-edital-detail]')) detail.hidden = true;
        if (!match) {
          const toggle = row.querySelector('[data-edital-toggle]');
          if (toggle) toggle.setAttribute('aria-expanded', 'false');
        }
        if (match) visible++;
      });
      group.hidden = visible === 0;
      visibleTotal += visible;
      const label = group.querySelector('[data-edital-year-count]');
      if (label) label.textContent = `${visible} ${visible === 1 ? 'documento' : 'documentos'}`;
      if (filtering && visible) group.open = true;
      else if (!filtering && lastFilterActive) group.open = group === groups[0];
    });

    if (count) count.textContent = `Mostrando ${visibleTotal} ${visibleTotal === 1 ? 'documento' : 'documentos'}`;
    if (empty) empty.hidden = visibleTotal !== 0;
    lastFilterActive = filtering;
  };

  const reset = () => {
    search.value = '';
    year.value = '';
    name.value = '';
    applyFilters();
    search.focus();
  };

  search.addEventListener('input', applyFilters);
  year.addEventListener('change', applyFilters);
  name.addEventListener('change', applyFilters);
  document.querySelector('[data-edital-clear]')?.addEventListener('click', reset);
  document.querySelector('[data-edital-empty-clear]')?.addEventListener('click', reset);
  document.querySelector('[data-expand-all]')?.addEventListener('click', () => {
    groups.filter((group) => !group.hidden).forEach((group) => { group.open = true; });
  });
  document.querySelector('[data-collapse-all]')?.addEventListener('click', () => {
    groups.forEach((group) => { group.open = false; });
  });

  root.addEventListener('click', (event) => {
    const button = event.target.closest('[data-edital-toggle]');
    if (!button) return;
    const row = button.closest('[data-edital-row]');
    const detail = row?.nextElementSibling;
    if (!detail?.matches('[data-edital-detail]')) return;
    detail.hidden = !detail.hidden;
    const expanded = !detail.hidden;
    button.setAttribute('aria-expanded', String(expanded));
    button.setAttribute('aria-label', `${expanded ? 'Recolher' : 'Expandir'} detalhes de ${row.querySelector('strong')?.textContent || 'edital'}`);
  });

  applyFilters();
})();
