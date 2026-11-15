import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import fs from "fs";
import { ensureSharedAuthState, authStatePath } from "../helpers/auth";

test.beforeAll(async ({ baseURL }) => {
  await ensureSharedAuthState(baseURL!);
});

test.use({ storageState: authStatePath() });

/**
 * US6 fixtures are seeded through the JSON API so the scenarios start from a
 * known state instead of driving the UI twice (the search box and the tag
 * badges under test are the UI).
 */
async function seedProject(
  page: Page,
  name: string
): Promise<{ id: string; name: string }> {
  const uniqueName = `${name}-${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 6)}`;
  const res = await page.request.post("/api/v1/projects", {
    data: { name: uniqueName },
  });
  expect(res.ok(), `project create failed: ${res.status()}`).toBeTruthy();
  const body = await res.json();
  return { id: body.id as string, name: uniqueName };
}

async function seedTag(
  page: Page,
  projectId: string,
  name: string
): Promise<string> {
  const res = await page.request.post(`/api/v1/projects/${projectId}/tags`, {
    data: { name },
  });
  expect(res.ok(), `tag create failed: ${res.status()}`).toBeTruthy();
  return (await res.json()).id as string;
}

async function seedNote(
  page: Page,
  projectId: string,
  title: string,
  content: string,
  tagIds: string[] = []
): Promise<string> {
  const res = await page.request.post(`/api/v1/projects/${projectId}/notes`, {
    data: { title, content, tag_ids: tagIds },
  });
  expect(res.ok(), `note create failed: ${res.status()}`).toBeTruthy();
  return (await res.json()).id as string;
}

async function seedLink(
  page: Page,
  projectId: string,
  title: string,
  url: string,
  tagIds: string[] = []
): Promise<string> {
  const res = await page.request.post(`/api/v1/projects/${projectId}/links`, {
    data: { url, title },
  });
  expect(res.ok(), `link create failed: ${res.status()}`).toBeTruthy();
  const link = await res.json();

  // POST /links ignores tag_ids, so tags are attached through A17
  if (tagIds.length > 0) {
    const attach = await page.request.post(
      `/api/v1/projects/${projectId}/links/${link.id}/tags`,
      { data: { tag_ids: tagIds } }
    );
    expect(attach.ok(), `link tag attach failed: ${attach.status()}`).toBeTruthy();
  }

  return link.id as string;
}

test.describe("Search, tag filter and export (US6)", () => {
  test("search debounces 500ms, shows relevance-ordered results, and clearing clears them", async ({
    page,
  }) => {
    const project = await seedProject(page, "Search Box");
    const noteId = await seedNote(
      page,
      project.id,
      "Distributed systems primer",
      "gossip protocols and quorum reads"
    );
    const linkId = await seedLink(
      page,
      project.id,
      "Consistency handbook",
      "https://example.com/consistency"
    );

    const results = [
      {
        type: "note",
        id: noteId,
        title: "Distributed systems primer",
        snippet: "gossip protocols and quorum reads",
        rank: 0.42,
      },
      {
        type: "link",
        id: linkId,
        title: "Consistency handbook",
        snippet: "strong versus eventual consistency",
        rank: 0.17,
      },
    ];
    let searchCalls = 0;
    await page.route("**/api/v1/projects/*/search-collected*", (route) => {
      searchCalls += 1;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        json: results,
      });
    });

    await page.goto(`/projects/${project.id}`);

    const input = page.getByLabel("Search notes & links");
    const container = page.locator("#collected-search-results");

    // Typing pauses below the 500ms threshold, so a single request fires
    await input.pressSequentially("distributed systems", { delay: 40 });
    await expect(container).toBeVisible();
    expect(searchCalls).toBe(1);

    const items = container.locator("li");
    await expect(items).toHaveCount(2);
    await expect(items.nth(0).getByText("Note", { exact: true })).toBeVisible();
    await expect(
      items.nth(0).getByRole("link", { name: "Distributed systems primer" })
    ).toHaveAttribute("href", `/projects/${project.id}#note-${noteId}`);
    await expect(items.nth(1).getByText("Link", { exact: true })).toBeVisible();
    await expect(
      items.nth(1).getByRole("link", { name: "Consistency handbook" })
    ).toHaveAttribute(
      "href",
      `/projects/${project.id}/links/${linkId}/read`
    );
    await expect(items.nth(1)).toContainText(
      "strong versus eventual consistency"
    );

    // Clearing the input clears the results and fires no request
    await input.fill("");
    await expect(container).toHaveCount(0);
    expect(searchCalls).toBe(1);

    // Submitting skips the debounce wait
    await input.pressSequentially("consistency", { delay: 30 });
    await input.press("Enter");
    await expect(container).toBeVisible();
    expect(searchCalls).toBe(2);
  });

  test("clicking a tag badge filters notes and links above the tabs, and Clear filter restores the workspace", async ({
    page,
  }) => {
    const project = await seedProject(page, "Tag Filter");
    const tagId = await seedTag(page, project.id, "alpha");
    await seedNote(page, project.id, "Tagged note", "first note body", [
      tagId,
    ]);
    await seedNote(page, project.id, "Untagged note", "second note body");
    const linkId = await seedLink(
      page,
      project.id,
      "Tagged link",
      "https://example.com/tagged",
      [tagId]
    );

    await page.goto(`/projects/${project.id}`);
    await page.evaluate(() => {
      (window as unknown as { noReload?: number }).noReload = 1;
    });

    const filter = page.locator("#tag-filter-results");

    // Badge on a note in the Notes tab
    await page
      .locator("#notes-panel article")
      .filter({ hasText: "Tagged note" })
      .getByRole("button", { name: "alpha", exact: true })
      .click();

    await expect(filter).toBeVisible();
    await expect(filter).toContainText('Items tagged "alpha"');
    await expect(filter.getByText("Tagged note")).toBeVisible();
    await expect(filter.getByText("Tagged link")).toBeVisible();
    await expect(filter.getByText("Untagged note")).toHaveCount(0);
    await expect(
      filter.getByRole("link", { name: "Tagged link" })
    ).toHaveAttribute("href", `/projects/${project.id}/links/${linkId}/read`);

    // Rendered above the tablist in the DOM
    const aboveTabs = await page.evaluate(() => {
      const filterEl = document.getElementById("tag-filter-results");
      const tablist = document.querySelector('[role="tablist"]');
      if (!filterEl || !tablist) return false;
      return (
        (filterEl.compareDocumentPosition(tablist) &
          Node.DOCUMENT_POSITION_FOLLOWING) !==
        0
      );
    });
    expect(aboveTabs).toBe(true);

    // Clear filter restores the workspace without a reload
    await filter.getByRole("button", { name: "Clear filter" }).click();
    await expect(page.locator("#tag-filter-results")).toHaveCount(0);
    await expect(page).toHaveURL(new RegExp(`/projects/${project.id}$`));
    expect(
      await page.evaluate(
        () => (window as unknown as { noReload?: number }).noReload
      )
    ).toBe(1);

    // Badge on a link in the Links tab
    await page.getByRole("tab", { name: "Links" }).click();
    await page
      .locator("#links-panel article")
      .filter({ hasText: "Tagged link" })
      .getByRole("button", { name: "alpha", exact: true })
      .click();
    await expect(filter).toContainText('Items tagged "alpha"');
    await expect(filter.getByText("Tagged link")).toBeVisible();
    await filter.getByRole("button", { name: "Clear filter" }).click();

    // Tag name in the Tags tab
    await page.getByRole("tab", { name: "Tags" }).click();
    await page
      .locator("#tags-panel")
      .getByRole("button", { name: "alpha", exact: true })
      .click();
    await expect(filter).toContainText('Items tagged "alpha"');
    await expect(filter.getByText("Tagged note")).toBeVisible();
  });

  test("a tag with no matching items shows an empty state", async ({
    page,
  }) => {
    const project = await seedProject(page, "Empty Filter");
    await seedTag(page, project.id, "lonely");

    await page.goto(`/projects/${project.id}`);
    await page.getByRole("tab", { name: "Tags" }).click();
    await page
      .locator("#tags-panel")
      .getByRole("button", { name: "lonely", exact: true })
      .click();

    await expect(page.getByText('No items tagged "lonely" yet.')).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Clear filter" })
    ).toBeVisible();
  });

  test("export downloads one Markdown file with the project's notes and links", async ({
    page,
  }) => {
    const project = await seedProject(page, "Export Project");
    await seedNote(page, project.id, "Exported note", "Body of the note");
    await seedLink(
      page,
      project.id,
      "Exported link",
      "https://example.com/exported"
    );

    const downloads: string[] = [];
    page.on("download", (download) => {
      downloads.push(download.suggestedFilename());
    });

    await page.goto(`/projects/${project.id}`);
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: "Export as Markdown" }).click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toMatch(/\.md$/);
    expect(download.suggestedFilename()).toMatch(/^export-project/);

    const filePath = await download.path();
    expect(filePath).toBeTruthy();
    const content = fs.readFileSync(filePath!, "utf8");
    expect(content).toContain(project.name);
    expect(content).toContain("Exported note");
    expect(content).toContain("https://example.com/exported");

    expect(downloads).toHaveLength(1);
  });
});
