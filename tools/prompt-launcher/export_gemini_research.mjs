#!/usr/bin/env node
/*
Purpose: capture a completed Gemini Deep Research page and optionally trigger Export to Google Docs.
Date: 2026-07-08
Owner: codex
Status: TESTED only as script structure; live Gemini selectors may need tuning.
*/

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { spawnSync } from "node:child_process";
import readline from "node:readline/promises";

const researchUrl = process.argv[2] || "https://gemini.google.com/app/5066cf74c5e36b8d";
const shouldExportDocs = process.argv.includes("--docs");
const keepOpen = process.argv.includes("--keep-open");

const launcherDir = decodeURIComponent(path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/, "$1"));
const profileDir = path.join(launcherDir, ".playwright-profile");
const exportRoot = path.join(launcherDir, "research_exports");
const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const exportDir = path.join(exportRoot, stamp);

fs.mkdirSync(exportDir, { recursive: true });

const { chromium } = await import("playwright");

const context = await chromium.launchPersistentContext(profileDir, {
  headless: false,
  viewport: { width: 1440, height: 1000 },
});

const page = context.pages()[0] || await context.newPage();
await page.goto(researchUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(8000);

async function bodyText() {
  return (await page.locator("body").innerText({ timeout: 5000 }).catch(() => "")).trim();
}

async function pauseForLoginIfNeeded() {
  const text = await bodyText();
  const needsLogin =
    /\bSign in\b/i.test(text) &&
    /\bMeet Gemini\b/i.test(text) &&
    !/Share|Export to Docs|Export to Google Docs/i.test(text);

  if (!needsLogin) return false;

  console.log("");
  console.log("Gemini opened, but this Playwright browser is not signed in yet.");
  console.log("Use the browser window that just opened to sign in to Google/Gemini.");
  console.log("After the research page is visible, come back here and press Enter.");
  console.log("");

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    await rl.question("Press Enter after Gemini is signed in and the research page is open...");
  } catch (error) {
    rl.close();
    await context.close();
    if (error?.code === "ABORT_ERR") {
      console.log("\nGemini capture cancelled.");
      process.exit(1);
    }
    throw error;
  }
  rl.close();

  await page.goto(researchUrl, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => undefined);
  await page.waitForTimeout(8000);
  return true;
}

await pauseForLoginIfNeeded();

async function visibleText() {
  const selectors = [
    "main",
    "[role='main']",
    "article",
    ".conversation-container",
    "body",
  ];
  for (const selector of selectors) {
    const loc = page.locator(selector).first();
    try {
      if ((await loc.count()) > 0 && (await loc.isVisible())) {
        const text = (await loc.innerText({ timeout: 5000 })).trim();
        if (text.length > 500) return text;
      }
    } catch {
      // Try the next selector.
    }
  }
  return "";
}

const text = await visibleText();
const html = await page.content();
const url = page.url();
const title = await page.title();

const textPath = path.join(exportDir, "gemini_research_capture.txt");
const htmlPath = path.join(exportDir, "gemini_research_page.html");
const metaPath = path.join(exportDir, "metadata.json");
const shotPath = path.join(exportDir, "gemini_research_page.png");

fs.writeFileSync(textPath, text, "utf8");
fs.writeFileSync(htmlPath, html, "utf8");
fs.writeFileSync(metaPath, JSON.stringify({ url, title, captured_at: new Date().toISOString(), shouldExportDocs }, null, 2), "utf8");
await page.screenshot({ path: shotPath, fullPage: true }).catch(() => undefined);

if (text.length > 0) {
  spawnSync("powershell.exe", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "Set-Clipboard -LiteralPath $args[0]", textPath], {
    stdio: "ignore",
  });
}

async function clickUniqueByRole(name) {
  const loc = page.getByRole("button", { name, exact: false });
  const count = await loc.count().catch(() => 0);
  if (count !== 1) return false;
  await loc.click({});
  return true;
}

async function clickByTextCandidate(candidates) {
  for (const textCandidate of candidates) {
    const loc = page.getByText(textCandidate, { exact: false });
    const count = await loc.count().catch(() => 0);
    if (count === 1) {
      await loc.click({});
      return textCandidate;
    }
  }
  return null;
}

let docsExport = { attempted: false, status: "not_requested" };

if (shouldExportDocs) {
  docsExport = { attempted: true, status: "started" };
  const shareClicked =
    (await clickUniqueByRole("Share")) ||
    (await clickUniqueByRole("Share & export")) ||
    Boolean(await clickByTextCandidate(["Share", "Share & export", "Export"]));

  if (!shareClicked) {
    docsExport = { attempted: true, status: "share_button_not_found" };
  } else {
    await page.waitForTimeout(1500);
    const exportClicked = await clickByTextCandidate([
      "Export to Docs",
      "Export to Google Docs",
      "Google Docs",
      "Open in Docs",
      "Docs",
    ]);
    if (!exportClicked) {
      docsExport = { attempted: true, status: "docs_export_option_not_found" };
    } else {
      docsExport = { attempted: true, status: "clicked_docs_export", clicked: exportClicked };
      await page.waitForTimeout(90000);
      docsExport.final_url = page.url();
      docsExport.final_title = await page.title();
    }
  }
}

fs.writeFileSync(metaPath, JSON.stringify({ url, title, captured_at: new Date().toISOString(), shouldExportDocs, docsExport, textPath, htmlPath, shotPath }, null, 2), "utf8");

console.log("Gemini research captured.");
console.log(`Text: ${textPath}`);
console.log(`HTML: ${htmlPath}`);
console.log(`Screenshot: ${shotPath}`);
console.log(`Metadata: ${metaPath}`);
  console.log(text.length > 0 ? "Copied capture text to clipboard." : "No substantial text was found to copy.");
  console.log(`Docs export: ${docsExport.status}`);

if (!keepOpen) {
  await context.close();
}
