import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { ensureSharedAuthState, authStatePath } from "../helpers/auth";

test.beforeAll(async ({ baseURL }) => {
  await ensureSharedAuthState(baseURL!);
});

test.use({ storageState: authStatePath() });

const SEARCH_RESULTS = [
  {
    title: "Python's Official Website",
    url: "https://www.python.org/",
    snippet: "Python is a programming language that lets you work quickly.",
    engine: "searxng",
  },
  {
    title: "Real Python Tutorials",
    url: "https://realpython.com/",
    snippet: "Hands-on tutorials for modern Python.",
    engine: "duckduckgo",
  },
];

async function createProject(page: Page, name: string): Promise<string> {
  // Shared E2E account — keep names unique so project cards never collide
  const uniqueName = `${name}-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 6)}`;
  await page.goto("/dashboard");
  await page.fill('form [name="name"]', uniqueName);
  await page.click('button[type="submit"]:has-text("Create")');
  await expect(page.locator(`text=${uniqueName}`)).toBeVisible();
  await page.click(`text=${uniqueName} >> nth=0`);
  await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+/);
  const match = page.url().match(/\/projects\/([0-9a-f-]+)/);
  if (!match) throw new Error(`Could not extract project id from ${page.url()}`);
  return match[1];
}

async function seedLink(
  page: Page,
  projectId: string,
  title: string,
  url: string
): Promise<string> {
  const res = await page.request.post(`/api/v1/projects/${projectId}/links`, {
    data: { url, title },
  });
  expect(res.ok(), `link create failed: ${res.status()}`).toBeTruthy();
  const body = await res.json();
  return body.id as string;
}

async function runSearch(page: Page, query: string): Promise<void> {
  const panel = page.locator("#websearch-panel");
  await panel.locator('[name="query"]').fill(query);
  await panel.getByRole("button", { name: "Search" }).click();
}

test.describe("Web search and saved links (US4)", () => {
  test("results show title opening in a new tab, snippet, and engine", async ({
    page,
  }) => {
    await createProject(page, "Search Results Project");
    await page.route("**/api/v1/projects/*/search", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        json: SEARCH_RESULTS,
      })
    );

    await page.getByRole("tab", { name: "Web Search" }).click();
    await runSearch(page, "python tutorials");

    const panel = page.locator("#websearch-panel");
    const first = panel.locator("article").filter({
      hasText: "Python's Official Website",
    });
    await expect(first).toBeVisible();

    const titleLink = first.getByRole("link", {
      name: "Python's Official Website",
    });
    await expect(titleLink).toHaveAttribute("target", "_blank");
    await expect(titleLink).toHaveAttribute(
      "href",
      "https://www.python.org/"
    );

    await expect(first).toContainText(
      "Python is a programming language that lets you work quickly."
    );
    await expect(first.getByText("searxng", { exact: true })).toBeVisible();
    await expect(first.getByRole("button", { name: "Save" })).toBeVisible();

    const second = panel
      .locator("article")
      .filter({ hasText: "Real Python Tutorials" });
    await expect(second.getByText("duckduckgo", { exact: true })).toBeVisible();
  });

  test("saving a result confirms Saved and adds it to the Links tab", async ({
    page,
  }) => {
    await createProject(page, "Search Save Project");
    await page.route("**/api/v1/projects/*/search", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        json: SEARCH_RESULTS,
      })
    );

    await page.getByRole("tab", { name: "Web Search" }).click();
    await runSearch(page, "python tutorials");

    const panel = page.locator("#websearch-panel");
    const first = panel
      .locator("article")
      .filter({ hasText: "Python's Official Website" });
    await first.getByRole("button", { name: "Save" }).click();

    // Success confirmation (FR-017)
    await expect(first.getByRole("button", { name: "Saved" })).toBeDisabled();
    await expect(page.getByText("Saved to your links.")).toBeVisible();

    // Appears in the Links tab without a reload
    await page.getByRole("tab", { name: "Links" }).click();
    const linksPanel = page.locator("#links-panel");
    await expect(
      linksPanel
        .locator("article")
        .filter({ hasText: "Python's Official Website" })
    ).toBeVisible();
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+$/);
  });

  test("empty results and search service failure show distinct states", async ({
    page,
  }) => {
    await createProject(page, "Search States Project");
    const searchRoute = "**/api/v1/projects/*/search";

    await page.route(searchRoute, (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        json: [],
      })
    );
    await page.getByRole("tab", { name: "Web Search" }).click();
    await runSearch(page, "zzqwertynothing123");
    const panel = page.locator("#websearch-panel");
    await expect(panel.getByText("No results found.")).toBeVisible();

    // Backend reports SearXNG failure as 502
    await page.unroute(searchRoute);
    await page.route(searchRoute, (route) =>
      route.fulfill({
        status: 502,
        contentType: "application/json",
        json: { detail: "SearXNG returned an error: 503" },
      })
    );
    await runSearch(page, "python");
    await expect(panel.getByText("SearXNG is unavailable.")).toBeVisible();

    // Network-level failure maps to the same copy
    await page.unroute(searchRoute);
    await page.route(searchRoute, (route) => route.abort("failed"));
    await runSearch(page, "python again");
    await expect(panel.getByText("SearXNG is unavailable.")).toBeVisible();
  });

  test("extraction status badge becomes Completed without a manual refresh", async ({
    page,
  }) => {
    const projectId = await createProject(page, "Auto Refresh Project");
    await seedLink(
      page,
      projectId,
      "Pending Article",
      "https://example.com/pending-article"
    );

    let listCalls = 0;
    await page.route("**/api/v1/projects/*/links", async (route) => {
      if (route.request().method() !== "GET") {
        await route.continue();
        return;
      }
      listCalls += 1;
      const response = await route.fetch();
      const body = await response.json();
      const json = body.map((link: { extraction_status: string }) =>
        listCalls <= 1 ? link : { ...link, extraction_status: "completed" }
      );
      await route.fulfill({ response, json });
    });

    await page.goto(`/projects/${projectId}`);
    await page.getByRole("tab", { name: "Links" }).click();

    const linksPanel = page.locator("#links-panel");
    const item = linksPanel
      .locator("article")
      .filter({ hasText: "Pending Article" });
    await expect(item.getByText("Pending", { exact: true })).toBeVisible();
    await expect(item.getByText("Completed", { exact: true })).toBeVisible({
      timeout: 12000,
    });
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+$/);
  });

  test("deleting a saved link asks for confirmation and removes it", async ({
    page,
  }) => {
    const projectId = await createProject(page, "Delete Link Project");
    await seedLink(
      page,
      projectId,
      "Disposable Link",
      "https://example.com/disposable"
    );

    await page.goto(`/projects/${projectId}`);
    await page.getByRole("tab", { name: "Links" }).click();

    const linksPanel = page.locator("#links-panel");
    const item = linksPanel
      .locator("article")
      .filter({ hasText: "Disposable Link" });
    await expect(item).toBeVisible();

    await item.getByRole("button", { name: "Delete" }).click();
    await expect(page.locator("dialog")).toContainText(
      "Delete this saved link?"
    );
    await page
      .locator("dialog")
      .getByRole("button", { name: "Delete" })
      .click();

    await expect(
      linksPanel.locator("article").filter({ hasText: "Disposable Link" })
    ).toHaveCount(0);
  });
});
