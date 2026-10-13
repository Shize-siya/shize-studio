// 无头 Chrome + CDP 交互冒烟测试：验证懒加载、inert 切换、灯箱焦点与键盘路径。
// 用法: node _smoke.mjs <页面绝对路径file://URL>
const { spawn } = require('node:child_process');
const fs = require('node:fs');

const URL_TARGET = process.argv[2];
const PORT = 9333;
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PROFILE = 'C:/Users/83492/WorkBuddy/2026-09-28-10-12-40/shize-studio/.build/_cdp2';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

(async () => {
  fs.rmSync(PROFILE, { recursive: true, force: true });
  const chrome = spawn(CHROME, [
    '--headless=new', '--disable-gpu', '--no-first-run',
    `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
    '--window-size=1280,800', 'about:blank',
  ], { stdio: 'ignore' });

  let ws, msgId = 0;
  const pending = new Map();
  const errors = [];

  function send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++msgId;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });
  }

  try {
    // 等调试端口起来
    let list = null;
    for (let i = 0; i < 40; i++) {
      await sleep(250);
      try {
        const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
        list = await res.json();
        if (list && list.length) break;
      } catch (e) { /* 端口未就绪 */ }
    }
    const page = list.find(t => t.type === 'page');
    if (!page) throw new Error('找不到 page target');

    ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    ws.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.id && pending.has(m.id)) {
        const { resolve, reject } = pending.get(m.id);
        pending.delete(m.id);
        m.error ? reject(new Error(m.error.message)) : resolve(m.result);
        return;
      }
      if (m.method === 'Runtime.exceptionThrown')
        errors.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
      if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error')
        errors.push(m.params.entry.text);
    };

    await send('Runtime.enable');
    await send('Log.enable');
    await send('Page.enable');
    await send('Page.navigate', { url: URL_TARGET });

    const ev = async (expr) => {
      const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || 'evaluate 失败');
      return r.result.value;
    };

    await sleep(800);                                   // 初始化脚本跑完
    const early = await ev(`JSON.stringify({
      eagerLoaded: [...document.querySelectorAll('.card img')].filter(i => i.src).length,
      gridLoaded: [...document.querySelectorAll('#gridRows img')].filter(i => i.src).length,
      total: document.querySelectorAll('.card').length,
    })`);
    console.log('加载门槛(应为 8/8/21):', early);

    await sleep(6500);                                  // 等开场结束
    console.log('揭示后:', await ev(`JSON.stringify({
      revealed: document.body.classList.contains('revealed'),
      cardLoaded: [...document.querySelectorAll('.card img')].filter(i => i.src).length,
      gridLoaded: [...document.querySelectorAll('#gridRows img')].filter(i => i.src).length,
    })`));

    console.log('初始 inert:', await ev(`JSON.stringify({
      grid: document.getElementById('grid').hasAttribute('inert'),
      menu: document.getElementById('menu').hasAttribute('inert'),
      devlog: document.getElementById('devlog').hasAttribute('inert'),
      lit: document.getElementById('lit').hasAttribute('inert'),
    })`));

    // 打开网格
    await ev(`document.getElementById('gridBtn').click()`);
    await sleep(700);
    console.log('打开网格:', await ev(`JSON.stringify({
      gridview: document.body.classList.contains('gridview'),
      gridInert: document.getElementById('grid').hasAttribute('inert'),
    })`));

    // 键盘打开第一个网格条目
    await ev(`document.querySelector('#gridRows figure').focus()`);
    await ev(`document.querySelector('#gridRows figure').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))`);
    await sleep(800);
    console.log('回车开灯箱:', await ev(`JSON.stringify({
      lit: document.body.classList.contains('lit'),
      litInert: document.getElementById('lit').hasAttribute('inert'),
      focusOnClose: document.activeElement && document.activeElement.textContent,
      title: document.getElementById('litTitle').textContent,
      imgAlt: document.getElementById('litImg').alt,
    })`));

    // Esc 关闭 → 焦点应还原
    await ev(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);
    await sleep(900);
    console.log('Esc 关闭后:', await ev(`JSON.stringify({
      lit: document.body.classList.contains('lit'),
      litInert: document.getElementById('lit').hasAttribute('inert'),
      focusBack: document.activeElement === document.querySelector('#gridRows figure'),
    })`));

    // Esc 再关网格
    await ev(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);
    await sleep(700);
    console.log('Esc 关网格:', await ev(`JSON.stringify({
      gridview: document.body.classList.contains('gridview'),
      gridInert: document.getElementById('grid').hasAttribute('inert'),
    })`));

    // 菜单开关
    await ev(`document.getElementById('menuBtn').click()`);
    await sleep(900);
    console.log('打开菜单:', await ev(`JSON.stringify({
      menuopen: document.body.classList.contains('menuopen'),
      menuInert: document.getElementById('menu').hasAttribute('inert'),
    })`));
    await ev(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);
    await sleep(500);
    console.log('Esc 关菜单:', await ev(`JSON.stringify({
      menuopen: document.body.classList.contains('menuopen'),
      menuInert: document.getElementById('menu').hasAttribute('inert'),
    })`));

    // 渲染循环是否真的静止（间隔取两个 transform 应完全一致）
    const t1 = await ev(`document.getElementById('world').style.transform`);
    await sleep(1200);
    const t2 = await ev(`document.getElementById('world').style.transform`);
    console.log('静止帧冻结:', t1 === t2 ? 'OK（两帧一致）' : '仍在写入: ' + t1 + ' | ' + t2);

    console.log('页面 JS 异常/错误:', errors.length ? errors.slice(0, 5) : '无');
  } catch (e) {
    console.error('SMOKE FAIL:', e.message);
    process.exitCode = 1;
  } finally {
    try { ws && ws.close(); } catch (e) {}
    chrome.kill();
  }
})();
