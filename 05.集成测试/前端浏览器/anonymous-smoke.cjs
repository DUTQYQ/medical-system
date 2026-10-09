process.chdir(__dirname);
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
 const browser = await chromium.launch({headless:true, executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const page = await browser.newPage({ viewport:{width:1440,height:1000} });
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:5173/login');
 await page.getByText('智能康养系统',{exact:true}).waitFor();
 if(await page.getByText('密码任意',{exact:false}).count()) throw Error('Old fake login hint remains');
 await page.screenshot({path:'login.png',fullPage:true});
 await page.goto('http://127.0.0.1:5173/elder/home');
 await page.waitForURL('**/login?redirect=**');
 if(errors.length)throw Error(errors.join('\n'));
 console.log(JSON.stringify({login_rendered:true,anonymous_guard:true,page_errors:errors.length}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
