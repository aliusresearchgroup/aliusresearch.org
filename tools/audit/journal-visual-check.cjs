const http = require("node:http");
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const { chromium } = require("C:/Users/cogpsy-vrlab/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");

const repoRoot = path.resolve(__dirname, "../..");
const docsRoot = path.join(repoRoot, "docs");
const outputDir = path.join(repoRoot, "output", "playwright");

const mimeTypes = new Map([
  [".html", "text/html; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".gif", "image/gif"],
  [".svg", "image/svg+xml"],
  [".pdf", "application/pdf"],
  [".woff", "font/woff"],
  [".woff2", "font/woff2"],
  [".ttf", "font/ttf"],
]);

function staticServer() {
  return http.createServer(async (req, res) => {
    try {
      const url = new URL(req.url || "/", "http://127.0.0.1");
      let pathname = decodeURIComponent(url.pathname);
      if (pathname.endsWith("/")) pathname += "index.html";

      let candidate = path.resolve(docsRoot, pathname.replace(/^\/+/, ""));
      if (!candidate.startsWith(path.resolve(docsRoot))) {
        res.writeHead(403).end("Forbidden");
        return;
      }

      if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
        candidate = path.join(candidate, "index.html");
      } else if (!fs.existsSync(candidate) && !path.extname(candidate)) {
        candidate += ".html";
      }

      const data = await fsp.readFile(candidate);
      res.writeHead(200, {
        "content-type": mimeTypes.get(path.extname(candidate).toLowerCase()) || "application/octet-stream",
      });
      res.end(data);
    } catch (error) {
      res.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
      res.end(error && error.message ? error.message : String(error));
    }
  });
}

function rectObject(rect) {
  if (!rect) return null;
  return {
    left: Math.round(rect.left),
    right: Math.round(rect.right),
    top: Math.round(rect.top),
    bottom: Math.round(rect.bottom),
    width: Math.round(rect.width),
    height: Math.round(rect.height),
  };
}

async function run() {
  await fsp.mkdir(outputDir, { recursive: true });
  const server = staticServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  const browser = await chromium.launch({ headless: true });

  const viewports = [
    { name: "desktop-top", width: 1440, height: 1000, scrollY: 0 },
    { name: "desktop-talks", width: 1440, height: 1000, scrollY: 1050 },
    { name: "tablet", width: 900, height: 1000, scrollY: 760 },
    { name: "mobile-top", width: 390, height: 900, scrollY: 0 },
    { name: "mobile-talks", width: 390, height: 900, scrollY: 1900 },
  ];

  const results = [];
  for (const viewport of viewports) {
    const page = await browser.newPage({
      viewport: { width: viewport.width, height: viewport.height },
      deviceScaleFactor: 1,
    });
    const consoleErrors = [];
    page.on("console", (message) => {
      if (message.type() === "error") consoleErrors.push(message.text());
    });
    page.on("pageerror", (error) => consoleErrors.push(error.message));

    await page.goto(`http://127.0.0.1:${port}/journal-club/`, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
    if (viewport.scrollY) {
      await page.evaluate((scrollY) => window.scrollTo(0, scrollY), viewport.scrollY);
      await page.waitForTimeout(250);
    }

    const metrics = await page.evaluate(() => {
      const rect = (element) => {
        if (!element) return null;
        const r = element.getBoundingClientRect();
        return {
          left: r.left,
          right: r.right,
          top: r.top,
          bottom: r.bottom,
          width: r.width,
          height: r.height,
        };
      };

      const anchors = document.querySelector(".alius-anchor-nav");
      const content = document.querySelector(".journal-page");
      const talks = Array.from(document.querySelectorAll(".journal-talk"));
      const images = Array.from(document.images).map((image) => image.getAttribute("src") || "");
      const iframes = Array.from(document.querySelectorAll(".journal-video iframe"));
      const anchorRect = rect(anchors);
      const contentRect = rect(content);
      const visibleContentElements = Array.from(
        document.querySelectorAll(
          ".journal-page h1, .journal-page h2, .journal-page h3, .journal-page p, .journal-video, .journal-youtube-link",
        ),
      );
      const overlappingElements = visibleContentElements.filter((element) => {
        const elementRect = rect(element);
        return (
          anchorRect &&
          elementRect &&
          elementRect.width > 0 &&
          elementRect.height > 0 &&
          !(
            anchorRect.right <= elementRect.left ||
            anchorRect.left >= elementRect.right ||
            anchorRect.bottom <= elementRect.top ||
            anchorRect.top >= elementRect.bottom
          )
        );
      });

      return {
        title: document.title,
        talkCount: talks.length,
        iframeCount: iframes.length,
        nonLogoImages: images.filter((src) => !src.includes("1477332210.png")).length,
        accordionLike: document.querySelectorAll('[class*="accordion"], [class*="dropdown"], details, summary').length,
        anchorNav: anchorRect,
        content: contentRect,
        navOverlapsContent: overlappingElements.length > 0,
        overlappingElementCount: overlappingElements.length,
        horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        headingOverflow: Array.from(document.querySelectorAll(".journal-talk h2")).filter(
          (heading) => heading.scrollWidth > heading.clientWidth + 1,
        ).length,
        paragraphOverflow: Array.from(document.querySelectorAll(".journal-page p")).filter(
          (paragraph) => paragraph.scrollWidth > paragraph.clientWidth + 1,
        ).length,
        lastTalkId: talks[talks.length - 1] && talks[talks.length - 1].id,
      };
    });

    const normalizedMetrics = {
      ...metrics,
      anchorNav: rectObject(metrics.anchorNav),
      content: rectObject(metrics.content),
    };
    const screenshotPath = path.join(outputDir, `journal-${viewport.name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: false });

    results.push({
      viewport,
      screenshotPath,
      metrics: normalizedMetrics,
      consoleErrors: consoleErrors
        .filter((error) => !/youtube|googlevideo|ERR_BLOCKED_BY_CLIENT|compute-pressure/i.test(error))
        .slice(0, 8),
    });
    await page.close();
  }

  await browser.close();
  await new Promise((resolve) => server.close(resolve));

  const failures = results.flatMap((result) => {
    const problems = [];
    if (result.metrics.talkCount !== 14) problems.push("expected 14 talk sections");
    if (result.metrics.iframeCount !== 14) problems.push("expected 14 video embeds");
    if (result.metrics.nonLogoImages !== 0) problems.push("unexpected non-logo images");
    if (result.metrics.accordionLike !== 0) problems.push("accordion/dropdown elements remain");
    if (result.metrics.headingOverflow !== 0) problems.push("heading overflow");
    if (result.metrics.paragraphOverflow !== 0) problems.push("paragraph overflow");
    if (result.metrics.navOverlapsContent) problems.push("left nav overlaps content");
    if (result.metrics.horizontalOverflow) problems.push("horizontal overflow");
    if (result.consoleErrors.length) problems.push("console errors");
    return problems.map((problem) => `${result.viewport.name}: ${problem}`);
  });

  console.log(JSON.stringify({ results, failures }, null, 2));
  if (failures.length) process.exitCode = 1;
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
