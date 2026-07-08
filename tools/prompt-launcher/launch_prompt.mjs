#!/usr/bin/env node
/*
Purpose: optionally open an online coding/research page and fill it with a stored David-OS prompt.
Date: 2026-07-07
Owner: codex
Status: UNTESTED against live pages; selectors are configured locally.
*/

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const promptPath = process.argv[2];
const shouldSubmit = process.argv.includes("--submit");

if (!promptPath) {
  console.error("Usage: node launch_prompt.mjs <prompt-file> [--submit]");
  process.exit(1);
}

const launcherDir = path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/, "$1");
const localConfigPath = path.join(launcherDir, "config.local.json");
const exampleConfigPath = path.join(launcherDir, "config.example.json");
const configPath = fs.existsSync(localConfigPath) ? localConfigPath : exampleConfigPath;
const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
const promptText = fs.readFileSync(promptPath, "utf8");
const targetMatch = promptText.match(/^Target:\s*([a-zA-Z0-9_-]+)/m);
const targetName = targetMatch?.[1] || "coding";
const target = config.targets?.[targetName];

if (!target) {
  console.error(`No target named "${targetName}" in ${configPath}.`);
  process.exit(2);
}

let chromium;
try {
  ({ chromium } = await import("playwright"));
} catch (error) {
  const fallbackModule = "C:\\Users\\David\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules\\playwright\\index.js";
  if (fs.existsSync(fallbackModule)) {
    ({ chromium } = await import(pathToFileURL(fallbackModule).href));
  } else {
    console.error("Playwright is not installed in this Node environment.");
    console.error("Install it for this repo with: npm install -D playwright");
    console.error("The prompt was already copied to your clipboard by launch_prompt.bat.");
    process.exit(3);
  }
}

const profileDir = path.resolve(launcherDir, config.browserProfileDir || ".playwright-profile");
const context = await chromium.launchPersistentContext(profileDir, {
  headless: false,
  viewport: { width: 1400, height: 950 }
});

const page = context.pages()[0] || await context.newPage();
await page.goto(target.targetUrl, { waitUntil: "domcontentloaded" });

let promptBox = null;
for (const selector of target.promptSelectors || []) {
  const candidate = page.locator(selector).first();
  try {
    await candidate.waitFor({ state: "visible", timeout: 5000 });
    promptBox = candidate;
    break;
  } catch {
    // Try the next configured selector.
  }
}

if (!promptBox) {
  console.error("Could not find a prompt box. Update config.local.json promptSelectors.");
  console.error("The browser is open; you can paste manually from the clipboard.");
  process.exit(4);
}

await promptBox.click();
await promptBox.fill(promptText);

if (shouldSubmit) {
  let submitted = false;
  for (const selector of target.submitSelectors || []) {
    const candidate = page.locator(selector).first();
    try {
      await candidate.waitFor({ state: "visible", timeout: 3000 });
      await candidate.click();
      submitted = true;
      break;
    } catch {
      // Try the next configured selector.
    }
  }
  if (!submitted) {
    console.error("Prompt filled, but no submit button matched. Submit manually or update config.local.json.");
    process.exit(5);
  }
}

console.log(shouldSubmit ? "Prompt filled and submitted." : "Prompt filled. Review it, then submit manually.");
