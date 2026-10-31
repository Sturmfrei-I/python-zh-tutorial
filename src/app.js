// 页面内容由 build.py 生成，这里只负责交互。
// 单文件预览版把所有页面放在 <template> 里，由 go() 切换；正式网站每章是独立页面，链接就是普通跳转。
(() => {
  'use strict';

  const root = document.documentElement;
  const $ = (id) => document.getElementById(id);
  const main = $('main');
  const { root: siteRoot = '', base: BASE, search: searchUrl } = main.dataset;
  const single = Boolean(document.querySelector('template[data-page]'));
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

  root.lang = 'zh-CN';

  // ---------- 本地偏好（读写失败时使用默认值） ----------

  const load = (key, fallback) => {
    try {
      const raw = localStorage.getItem(`pyvs.${key}`);
      return raw === null ? fallback : JSON.parse(raw);
    } catch {
      return fallback;
    }
  };
  const save = (key, value) => {
    try {
      localStorage.setItem(`pyvs.${key}`, JSON.stringify(value));
    } catch { /* 隐私窗口里可能不可写 */ }
  };

  const state = {
    lang: load('lang', null),
    done: new Set(load('done', [])),
    last: load('last', null),
    theme: load('theme', 'auto'),
  };

  const esc = (text) => String(text).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const pageUrl = (page, frag) => `${siteRoot}${page === 'home' ? '' : `${page}/`}${frag ? `#${frag}` : ''}` || './';

  // ---------- 代码高亮 ----------

  // 逐行包裹高亮结果，行结构和 render.py 的 code_lines 相同。跨行的 span 要在行尾闭合、下一行重开
  const toLines = (code, html) => {
    const raw = code.split('\n');
    const open = [];
    return html.split('\n').map((line, i) => {
      const prefix = open.join('');
      for (const [tag] of line.matchAll(/<span[^>]*>|<\/span>/g)) {
        if (tag === '</span>') open.pop(); else open.push(tag);
      }
      const indent = raw[i].length - raw[i].trimStart().length;
      const newline = i < raw.length - 1 ? '\n' : '';
      // 行首空格单独包一层，否则浏览器会在缩进后换行，留下一个空行
      const body = line.replace(/^ +/, (spaces) => `<span class="ind">${spaces}</span>`);
      return `<span class="ln" style="--i:${indent}">${prefix}${body}${'</span>'.repeat(open.length)}${newline}</span>`;
    }).join('');
  };

  function highlightAll(scope = document) {
    const lib = window.hljs;
    if (!lib) return;
    scope.querySelectorAll('code[data-hl]').forEach((el) => {
      const name = el.dataset.hl;
      el.removeAttribute('data-hl');
      if (!lib.getLanguage(name)) return;
      const code = el.textContent;
      // `=>` 结果注释作为一个整体换行，并用单独的颜色标出
      const html = lib.highlight(code, { language: name, ignoreIllegals: true }).value
        .replace(/<span class="hljs-comment">((?:\/\/|#) =&gt; )/g, '<span class="hljs-comment res">$1');
      el.innerHTML = toLines(code, html);
    });
  }

  // ---------- 语言切换 ----------

  function syncLangs(scope = document) {
    scope.querySelectorAll('[data-langs]').forEach((el) => {
      const langs = el.dataset.langs.split(',').filter(Boolean);
      const active = langs.includes(state.lang) ? state.lang : langs[0];
      el.querySelectorAll('[data-col]').forEach((node) => {
        node.hidden = node.dataset.col !== BASE && node.dataset.col !== active;
      });
      el.querySelectorAll('.seg').forEach((seg) => {
        const tabs = [...seg.querySelectorAll('button')];
        seg.style.setProperty('--i', tabs.findIndex((tab) => tab.dataset.lang === active));
        tabs.forEach((tab) => {
          const on = tab.dataset.lang === active;
          tab.setAttribute('aria-selected', String(on));
          tab.tabIndex = on ? 0 : -1;
          // 标签放不下时，把选中的标签滚到可见位置
          if (on && seg.parentElement.scrollWidth > seg.parentElement.clientWidth) {
            seg.parentElement.scrollLeft = tab.offsetLeft - (seg.parentElement.clientWidth - tab.offsetWidth) / 2;
          }
        });
      });
      el.querySelectorAll('.lang-pick select').forEach((select) => { select.value = active; });
    });
    const pick = $('lang-pick');
    if (state.lang && [...pick.options].some((option) => option.value === state.lang)) pick.value = state.lang;
  }

  function setLang(id, trigger) {
    if (id === state.lang) return;
    // 切换后卡片高度会变，把视线所在的卡片钉在原位
    const barBottom = $('bar').getBoundingClientRect().bottom;
    const anchor = trigger?.closest('.vs')
      ?? [...document.querySelectorAll('.vs')].find((el) => el.getBoundingClientRect().bottom > barBottom);
    const before = anchor?.getBoundingClientRect().top;
    state.lang = id;
    save('lang', id);
    syncLangs();
    if (anchor) window.scrollBy({ top: anchor.getBoundingClientRect().top - before, behavior: 'instant' });
  }

  // ---------- 阅读进度 ----------

  let sectionSpy;
  let endSpy;

  function markProgress() {
    document.querySelectorAll('.side-ch').forEach((item) => {
      item.classList.toggle('is-done', state.done.has(item.dataset.ch));
    });
    document.querySelectorAll('.toc a').forEach((link) => {
      const read = state.done.has(link.dataset.page);
      const [left, done] = link.querySelectorAll('.toc-meta');
      left.hidden = read;
      done.hidden = !read;
    });
  }

  function paintCta() {
    const cta = $('cta-start');
    if (!cta || !state.last) return;
    const [page, frag] = state.last.split('#');
    const title = document.querySelector(`.side-ch[data-ch="${page}"] .t`)?.textContent;
    if (!title) return;
    cta.textContent = `继续：${title}`;
    cta.href = pageUrl(page, frag);
    cta.dataset.page = page;
    if (frag) cta.dataset.frag = frag;
  }

  function watchChapter() {
    sectionSpy?.disconnect();
    endSpy?.disconnect();
    if (root.dataset.view !== 'chapter') return;

    const page = root.dataset.page;
    if (!state.last?.startsWith(`${page}#`)) {
      state.last = page;
      save('last', page);
    }
    const sections = [...main.querySelectorAll('.sec')];
    const links = document.querySelectorAll(`.side-ch[data-ch="${page}"] .side-secs a`);
    const seen = new Map();
    sectionSpy = new IntersectionObserver((entries) => {
      for (const entry of entries) seen.set(entry.target.id, entry.isIntersecting);
      const current = sections.find((section) => seen.get(section.id));
      if (!current) return;
      links.forEach((a) => a.classList.toggle('is-on', a.dataset.sec === current.id));
      state.last = `${page}#${current.id}`;
      save('last', state.last);
    }, { rootMargin: '-18% 0px -74% 0px' });
    sections.forEach((section) => sectionSpy.observe(section));

    endSpy = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting) || state.done.has(page)) return;
      state.done.add(page);
      save('done', [...state.done]);
      markProgress();
    });
    const pager = $('pager');
    if (pager) endSpy.observe(pager);
  }

  function updateProgress() {
    const range = root.scrollHeight - window.innerHeight;
    const ratio = root.dataset.view === 'chapter' && range > 0 ? Math.min(1, Math.max(0, window.scrollY / range)) : 0;
    $('progress').style.setProperty('--p', ratio.toFixed(4));
  }

  // ---------- 单文件预览版的页面切换 ----------
  // 链接里的定位符只能用字母、数字、点和连字符，所以写成 page.frag

  function revealAnchor(id) {
    if (id) $(id)?.closest('details')?.setAttribute('open', '');
  }

  function scrollToAnchor(id, smooth) {
    const target = $(id);
    if (!target) return;
    revealAnchor(id);
    target.scrollIntoView({ block: 'start', behavior: smooth && !reduced ? 'smooth' : 'instant' });
  }

  function renderTemplate(template) {
    const { page, view, title } = template.dataset;
    root.dataset.view = view;
    root.dataset.page = page;
    document.title = title;
    main.replaceChildren(template.content.cloneNode(true));
    document.querySelectorAll('.side-ch').forEach((item) => {
      item.classList.toggle('is-active', item.dataset.ch === page);
    });
    document.querySelectorAll('.side-secs a.is-on').forEach((a) => a.classList.remove('is-on'));
    afterRender();
    highlightAll(main);
  }

  const swapView = (update) => {
    if (!document.startViewTransition || reduced) {
      update();
      return Promise.resolve();
    }
    const transition = document.startViewTransition(update);
    transition.ready.catch(() => {});
    return transition.updateCallbackDone;
  };

  const findTemplate = (page) => document.querySelector(`template[data-page="${page}"]`)
    ?? document.querySelector('template[data-page="home"]');

  function go(page, frag, { push = true } = {}) {
    const template = findTemplate(page);
    const changing = template.dataset.page !== root.dataset.page;
    closeDrawer();
    if ($('spot').open) $('spot').close();
    const after = () => {
      if (frag) scrollToAnchor(frag, !changing);
      else if (changing) window.scrollTo({ top: 0, behavior: 'instant' });
      updateProgress();
    };
    if (changing) swapView(() => renderTemplate(template)).then(after);
    else after();
    if (push) {
      const token = template.dataset.page === 'home' ? '' : `#${template.dataset.page}${frag ? `.${frag}` : ''}`;
      try {
        history.pushState(null, '', token || location.pathname + location.search);
      } catch { /* 受限环境下保持页内状态 */ }
    }
  }

  function navigate(page, frag) {
    if (single) {
      go(page, frag);
    } else if (page === root.dataset.page) {
      $('spot').close();
      if (frag) location.hash = frag;
      revealAnchor(frag);
    } else {
      location.href = pageUrl(page, frag);
    }
  }

  // ---------- 速查表过滤 ----------

  function filterSheet(query) {
    const needle = query.trim().toLowerCase();
    let any = false;
    document.querySelectorAll('.sheet-group').forEach((group) => {
      let groupHit = false;
      group.querySelectorAll('.map').forEach((table) => {
        let tableHit = false;
        table.querySelectorAll('tbody tr').forEach((row) => {
          const hit = !needle || row.textContent.toLowerCase().includes(needle);
          row.hidden = !hit;
          tableHit ||= hit;
        });
        table.hidden = !tableHit;
        groupHit ||= tableHit;
      });
      group.hidden = !groupHit;
      any ||= groupHit;
    });
    $('sheet-empty').hidden = any;
  }

  // ---------- 搜索 ----------

  let searchIndex = null;

  async function loadIndex() {
    if (searchIndex) return searchIndex;
    const inline = $('search-data');
    if (inline) {
      searchIndex = JSON.parse(inline.textContent);
    } else {
      const response = await fetch(searchUrl);
      if (!response.ok) throw new Error(String(response.status));
      searchIndex = await response.json();
    }
    return searchIndex;
  }

  const mark = (text, needle) => {
    const at = text.toLowerCase().indexOf(needle);
    if (!needle || at < 0) return esc(text);
    return `${esc(text.slice(0, at))}<mark>${esc(text.slice(at, at + needle.length))}</mark>${esc(text.slice(at + needle.length))}`;
  };

  function search(query) {
    const needle = query.trim().toLowerCase();
    if (!needle) return searchIndex.filter((item) => item.kind === '章节').map((item) => ({ item, line: null }));
    const hits = [];
    const taken = new Set();
    for (const item of searchIndex) {
      const inTitle = item.title.toLowerCase().indexOf(needle);
      const inSub = item.sub.toLowerCase().indexOf(needle);
      const inText = item.text.toLowerCase().indexOf(needle);
      if (inTitle < 0 && inSub < 0 && inText < 0) continue;
      const key = `${item.kind}|${item.page}|${item.frag}|${item.title}`;
      if (taken.has(key)) continue;
      taken.add(key);
      const line = inTitle < 0 && inText >= 0
        ? item.text.split('\n').find((l) => l.toLowerCase().includes(needle))?.trim().slice(0, 120)
        : null;
      const score = (inTitle === 0 ? 30 : inTitle > 0 ? 20 : inSub >= 0 ? 10 : 0) + item.rank;
      hits.push({ item, line, score });
    }
    return hits.sort((a, b) => b.score - a.score).slice(0, 40);
  }

  let spotResults = [];
  let spotIndex = 0;

  async function paintSpot(query) {
    const list = $('spot-list');
    try {
      await loadIndex();
    } catch {
      spotResults = [];
      list.innerHTML = '<p class="spot-none">搜索索引加载失败，请检查网络后重新打开搜索。</p>';
      return;
    }
    const needle = query.trim().toLowerCase();
    spotResults = search(query);
    spotIndex = 0;
    if (!spotResults.length) {
      list.innerHTML = '<p class="spot-none">没有找到结果。可以试试其他语言的类名、关键字。</p>';
      return;
    }
    list.innerHTML = spotResults.map(({ item, line }, i) => `<a class="spot-item ${i === 0 ? 'is-on' : ''}" role="option" href="${esc(pageUrl(item.page, item.frag))}" data-i="${i}" aria-selected="${i === 0}">
      <span class="spot-kind">${item.kind}</span>
      <span class="spot-title">${mark(item.title, needle)}</span>
      <span class="spot-sub">${mark(line ?? item.sub, needle)}</span>
    </a>`).join('');
    list.scrollTop = 0;
  }

  function moveSpot(delta) {
    if (!spotResults.length) return;
    spotIndex = (spotIndex + delta + spotResults.length) % spotResults.length;
    document.querySelectorAll('.spot-item').forEach((el, i) => {
      el.classList.toggle('is-on', i === spotIndex);
      el.setAttribute('aria-selected', String(i === spotIndex));
      if (i === spotIndex) el.scrollIntoView({ block: 'nearest' });
    });
  }

  function openSpot() {
    if ($('spot').open) return;
    $('spot-q').value = '';
    $('spot').showModal();
    $('spot-q').focus();
    paintSpot('');
  }

  function chooseSpot(index) {
    const hit = spotResults[index];
    if (hit) navigate(hit.item.page, hit.item.frag);
  }

  // ---------- 目录开关与主题 ----------

  const isNarrow = () => matchMedia('(max-width: 960px)').matches;

  function closeDrawer() {
    delete root.dataset.drawer;
  }

  function toggleSide() {
    if (isNarrow()) {
      if (root.dataset.drawer) closeDrawer();
      else root.dataset.drawer = 'open';
      return;
    }
    const closed = root.dataset.side === 'closed';
    if (closed) delete root.dataset.side;
    else root.dataset.side = 'closed';
    save('side', closed ? 'open' : 'closed');
  }

  const THEME_LABEL = { auto: '跟随系统', light: '浅色', dark: '深色' };

  function paintTheme() {
    const button = $('theme-toggle');
    button.dataset.mode = state.theme;
    button.setAttribute('aria-label', `外观：${THEME_LABEL[state.theme]}，点击切换`);
    button.title = `外观：${THEME_LABEL[state.theme]}`;
  }

  function cycleTheme() {
    const order = ['auto', 'light', 'dark'];
    state.theme = order[(order.indexOf(state.theme) + 1) % order.length];
    save('theme', state.theme);
    if (state.theme === 'auto') delete root.dataset.theme;
    else root.dataset.theme = state.theme;
    paintTheme();
  }

  // ---------- 事件 ----------

  async function copyCode(button) {
    const code = button.closest('.code, .vs-pane').querySelector('pre:not([hidden]) code');
    const label = button.querySelector('span');
    const flash = (text) => {
      label.textContent = text;
      button.classList.add('is-done');
      setTimeout(() => {
        label.textContent = '拷贝';
        button.classList.remove('is-done');
      }, 1400);
    };
    try {
      await navigator.clipboard.writeText(code.textContent);
      flash('已拷贝');
    } catch {
      const range = document.createRange();
      range.selectNodeContents(code);
      const selection = getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      flash('已选中');
    }
  }

  document.addEventListener('click', (event) => {
    const tab = event.target.closest('.seg button');
    if (tab) {
      setLang(tab.dataset.lang, tab);
      return;
    }
    const copy = event.target.closest('.copy');
    if (copy) {
      copyCode(copy);
      return;
    }
    const spotItem = event.target.closest('.spot-item');
    if (spotItem && !event.metaKey && !event.ctrlKey) {
      event.preventDefault();
      chooseSpot(Number(spotItem.dataset.i));
      return;
    }
    const link = event.target.closest('a[data-page]');
    if (single && link && !event.metaKey && !event.ctrlKey && !event.shiftKey) {
      event.preventDefault();
      go(link.dataset.page, link.dataset.frag);
    }
  });

  document.addEventListener('change', (event) => {
    const picker = event.target.closest('.vs .lang-pick select');
    if (picker) setLang(picker.value, picker);
  });

  document.addEventListener('input', (event) => {
    if (event.target.id === 'sheet-q') filterSheet(event.target.value);
  });

  document.addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      openSpot();
      return;
    }
    const tab = event.target.closest?.('.seg button');
    if (tab && (event.key === 'ArrowLeft' || event.key === 'ArrowRight')) {
      event.preventDefault();
      const tabs = [...tab.parentElement.querySelectorAll('button')];
      const next = tabs[(tabs.indexOf(tab) + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
      setLang(next.dataset.lang, next);
      next.focus();
      return;
    }
    const typing = event.target.closest?.('input, textarea, select, [contenteditable]');
    if (typing || $('spot').open || event.metaKey || event.ctrlKey || event.altKey) return;
    if (event.key === '/') {
      event.preventDefault();
      openSpot();
    } else if (event.key === 'ArrowLeft') {
      $('pager')?.querySelector('.prev')?.click();
    } else if (event.key === 'ArrowRight') {
      $('pager')?.querySelector('.next')?.click();
    }
  });

  $('spot-q').addEventListener('input', (event) => paintSpot(event.target.value));
  $('spot-q').addEventListener('keydown', (event) => {
    if (event.isComposing) return;
    if (event.key === 'ArrowDown') { event.preventDefault(); moveSpot(1); }
    else if (event.key === 'ArrowUp') { event.preventDefault(); moveSpot(-1); }
    else if (event.key === 'Enter') { event.preventDefault(); chooseSpot(spotIndex); }
  });
  $('spot').addEventListener('click', (event) => {
    if (event.target === $('spot')) $('spot').close();
  });

  $('search-open').addEventListener('click', openSpot);
  $('side-toggle').addEventListener('click', toggleSide);
  $('scrim').addEventListener('click', closeDrawer);
  $('theme-toggle').addEventListener('click', cycleTheme);
  $('lang-pick').addEventListener('change', (event) => setLang(event.target.value));

  let ticking = false;
  window.addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
      updateProgress();
      ticking = false;
    });
  }, { passive: true });
  window.addEventListener('resize', updateProgress, { passive: true });

  // 跳转页面时保持目录的滚动位置
  const side = $('side');
  window.addEventListener('pagehide', () => {
    try { sessionStorage.setItem('pyvs.sideTop', String(side.scrollTop)); } catch { /* 受限环境 */ }
  });

  // ---------- 启动 ----------

  function afterRender() {
    syncLangs();
    markProgress();
    paintCta();
    watchChapter();
    updateProgress();
  }

  const tokenFromHash = () => decodeURIComponent(location.hash.slice(1)).split('.');

  paintTheme();
  try {
    side.scrollTop = Number(sessionStorage.getItem('pyvs.sideTop')) || 0;
  } catch { /* 受限环境 */ }

  if (single) {
    try { history.scrollRestoration = 'manual'; } catch { /* 受限环境 */ }
    const [page, frag] = tokenFromHash();
    renderTemplate(findTemplate(page));
    if (frag) scrollToAnchor(frag, false);
    window.addEventListener('popstate', () => {
      const [nextPage, nextFrag] = tokenFromHash();
      go(nextPage, nextFrag, { push: false });
    });
  } else {
    afterRender();
    revealAnchor(location.hash.slice(1));
    window.addEventListener('hashchange', () => revealAnchor(location.hash.slice(1)));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => highlightAll());
  } else {
    highlightAll();
  }
})();
