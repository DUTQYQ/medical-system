const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');
const { pathToFileURL } = require('url');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DIR = 'D:\\Desktop\\康养系统实训项目\\02.需求分析\\界面原型';
const PAGES = path.join(DIR, 'pages');
const OUT = path.join(DIR, '效果图');

(async () => {
  const files = fs.readdirSync(PAGES).filter(f => f.endsWith('.html')).sort();
  fs.mkdirSync(OUT, { recursive: true });
  console.log(`found ${files.length} pages`);

  const browser = await chromium.launch({ executablePath: CHROME });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 2,
  });

  let ok = 0, fail = 0;
  for (const html of files) {
    const png = html.replace(/\.html$/, '.png');
    try {
      await page.goto(pathToFileURL(path.join(PAGES, html)).href, { waitUntil: 'networkidle' });
      await page.waitForTimeout(350);
      const el = await page.$('.page');
      if (!el) throw new Error('missing .page');
      const box = await el.boundingBox();
      await el.screenshot({ path: path.join(OUT, png) });
      console.log(`OK   ${png}  (${Math.round(box.width)}x${Math.round(box.height)} @2x)`);
      ok++;
    } catch (e) {
      console.error(`FAIL ${html}: ${e.message}`);
      fail++;
    }
  }

  await browser.close();
  console.log(`ALL DONE  ok=${ok} fail=${fail}`);
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
