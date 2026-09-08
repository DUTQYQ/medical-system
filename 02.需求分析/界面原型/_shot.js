const { chromium } = require('playwright-core');
const path = require('path');
const { pathToFileURL } = require('url');

const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const DIR = 'D:\\Desktop\\康养系统实训项目\\02.需求分析\\界面原型';

const targets = [
  ['P1_老人端首页.html',        '效果图_P1_老人端首页.png'],
  ['P2_AI健康咨询.html',        '效果图_P2_AI健康咨询.png'],
  ['P3_预警通知中心.html',      '效果图_P3_预警通知中心.png'],
  ['P4_护工端老人列表.html',    '效果图_P4_护工端老人列表.png'],
  ['P5_管理员预警规则配置.html','效果图_P5_管理员预警规则配置.png'],
];

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 2,
  });

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
