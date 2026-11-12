(() => {
  'use strict';
  const dialog = document.getElementById('mango-case-dialog');
  const content = dialog.querySelector('.mango-case-content');
  const title = document.getElementById('mango-case-title');
  let returnHash = '#report';
  let fromList = false;
  let opener = null;
  let closing = false;

  function syncView() {
    closing = false;
    const target = /^#case-\d+-\d+$/.test(location.hash)
      ? document.getElementById(location.hash.slice(1)) : null;
    if (target instanceof HTMLTemplateElement) {
      content.replaceChildren(target.content.cloneNode(true));
      title.textContent = target.dataset.title || 'Case 详情';
      if (!dialog.open) dialog.showModal();
      document.body.classList.add('mango-case-open');
      content.scrollTop = 0;
      title.focus({ preventScroll: true });
    } else {
      if (dialog.open) dialog.close();
      document.body.classList.remove('mango-case-open');
      content.replaceChildren();
      fromList = false;
      if (opener?.isConnected) opener.focus({ preventScroll: true });
    }
  }

  function closeView() {
    if (!dialog.open || closing) return;
    closing = true;
    if (fromList) {
      fromList = false;
      history.back();
    } else {
      history.replaceState(null, '', returnHash);
      syncView();
    }
  }

  function selectTab(button) {
    const group = button.closest('[data-api-tabs]');
    group.querySelectorAll('[role="tab"]').forEach(tab => {
      const selected = tab === button;
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    group.querySelectorAll('[role="tabpanel"]').forEach(panel => {
      panel.hidden = panel.id !== button.getAttribute('aria-controls');
    });
  }

  document.addEventListener('click', event => {
    const link = event.target.closest('[data-case-open]');
    if (link && !event.ctrlKey && !event.metaKey && !event.shiftKey && event.button === 0) {
      returnHash = location.hash || '#report';
      opener = link;
      fromList = true;
    }
  });
  dialog.querySelector('[data-case-close]').addEventListener('click', closeView);
  dialog.addEventListener('cancel', event => { event.preventDefault(); closeView(); });
  dialog.addEventListener('click', event => {
    if (event.target === dialog) {
      const box = dialog.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) closeView();
    }
    const step = event.target.closest('[data-step-target]');
    if (step) {
      const workspace = step.closest('.mango-api-workspace');
      workspace.querySelectorAll('[data-step-target]').forEach(button => button.setAttribute('aria-pressed', String(button === step)));
      workspace.querySelectorAll('[data-api-step]').forEach(panel => { panel.hidden = panel.id !== step.dataset.stepTarget; });
      content.scrollTop = 0;
    }
    const tab = event.target.closest('[role="tab"]');
    if (tab) selectTab(tab);
  });
  dialog.addEventListener('keydown', event => {
    if (!event.target.matches('[role="tab"]') || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const tabs = [...event.target.closest('[role="tablist"]').querySelectorAll('[role="tab"]')];
    const index = tabs.indexOf(event.target);
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
      : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    selectTab(tabs[next]);
    tabs[next].focus();
  });
  window.addEventListener('hashchange', syncView);
  syncView();
})();
