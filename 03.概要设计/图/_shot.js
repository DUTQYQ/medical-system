const { chromium } = require('playwright-core');
const path = require('path');
const { pathToFileURL } = require('url');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DIR = 'D:\\Desktop\\康养系统实训项目\\03.概要设计\\图';

const targets = [
  ['系统架构图.html', '系统架构图.png'],
];

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME });
  const page = await browser.newPage({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 2 });
  for (const [html, png] of targets) {
    const url = pathToFileURL(path.join(DIR, html)).href;
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForTimeout(400);
    const el = await page.$('.page');
    const box = await el.boundingBox();
    await el.screenshot({ path: path.join(DIR, png) });
    console.log(`OK  ${png}  (${Math.round(box.width)}x${Math.round(box.height)} @2x)`);
  }
  await browser.close();
  console.log('ALL DONE');
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
