(() => {
  'use strict';
  const controls = document.querySelector('[data-archive-controls]');
  if (!controls) return;
  const labels = { all: '全部', teaching: '教学', research: '科研', service: '社会服务' };
  const filters = Array.from(controls.querySelectorAll('[data-filter]'));
  const input = controls.querySelector('input[type="search"]');
  const items = Array.from(document.querySelectorAll('.fact[data-category], .entries li[data-category]'));
  const groups = Array.from(document.querySelectorAll('.fact-group'));
  const output = controls.querySelector('.results-status');
  const empty = document.querySelector('.no-results');
  const normalize = (text) => text.normalize('NFKC').toLocaleLowerCase().replace(/\s+/g, ' ').trim();
  const indexes = items.map(item => normalize(['沈校亮', labels[item.dataset.category], item.textContent].join(' ')));
  let category = 'all';

  function readLocation() {
    const params = new URLSearchParams(location.search);
    const requested = params.get('category');
    category = filters.some(button => button.dataset.filter === requested) ? requested : 'all';
    if (input) input.value = params.get('q') || '';
  }

  function render(updateLocation) {
    const query = input ? input.value.trim() : '';
    const terms = normalize(query).split(' ').filter(Boolean);
    let visible = 0;
    items.forEach((item, i) => {
      item.hidden = (category !== 'all' && item.dataset.category !== category) ||
        !terms.every(term => indexes[i].includes(term));
      if (!item.hidden) visible += 1;
    });
    groups.forEach(group => { group.hidden = !group.querySelector('.fact:not([hidden])'); });
    filters.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === category)));
    if (output) output.textContent = '显示 ' + visible + ' 条' + (input ? '记录' : '动态');
    if (empty) empty.hidden = visible !== 0;
    if (updateLocation) {
      const url = new URL(location.href);
      if (category === 'all') url.searchParams.delete('category');
      else url.searchParams.set('category', category);
      if (query) url.searchParams.set('q', query);
      else url.searchParams.delete('q');
      url.hash = '';
      try { history.replaceState(null, '', url); } catch (_) { /* Local files can restrict history. */ }
    }
  }

  filters.forEach(button => button.addEventListener('click', () => {
    category = button.dataset.filter;
    render(true);
  }));
  if (input) input.addEventListener('input', () => render(true));
  const reset = document.querySelector('.reset-filters');
  if (reset) reset.addEventListener('click', () => {
    category = 'all';
    if (input) input.value = '';
    render(true);
    if (input) input.focus();
  });
  window.addEventListener('popstate', () => { readLocation(); render(false); });
  readLocation();
  controls.hidden = false;
  render(false);

  const dialog = document.querySelector('.copy-dialog');
  const feedback = document.getElementById('copy-status');
  document.querySelectorAll('.copy-record').forEach(button => {
    button.hidden = false;
    button.addEventListener('click', async () => {
      const item = button.closest('.fact');
      const text = selector => item.querySelector(selector).textContent.trim();
      const sources = Array.from(item.querySelectorAll('.fact-sources a'), a =>
        a.textContent.trim() + ' ' + new URL(a.getAttribute('href'), 'https://xlshen.cn/').href);
      const record = [
        text('.fact-date') + '｜' + labels[item.dataset.category] + ' · ' + text('.fact-tag'),
        text('.fact-title'), text('.fact-role'), text('.fact-detail'), ...sources,
      ].join('\n');
      try {
        await navigator.clipboard.writeText(record);
        feedback.textContent = '已复制' + text('.fact-title');
        button.textContent = '已复制';
        setTimeout(() => { button.textContent = '复制条目'; }, 1800);
      } catch (_) {
        const area = dialog.querySelector('textarea');
        area.value = record;
        if (typeof dialog.showModal === 'function') dialog.showModal();
        else dialog.setAttribute('open', '');
        area.focus();
        area.select();
        feedback.textContent = '已选中条目文字，可手动复制。';
      }
    });
  });
})();
