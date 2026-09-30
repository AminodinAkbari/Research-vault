import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { ensureSharedAuthState, authStatePath } from "../helpers/auth";

test.beforeAll(async ({ baseURL }) => {
  await ensureSharedAuthState(baseURL!);
});

test.use({ storageState: authStatePath() });

const ARTICLE_HTML =
  "<p>Extracted paragraph one about distributed systems.</p>" +
  "<p>Extracted paragraph two about consistency models.</p>";

const YELLOW = "rgb(255, 245, 157)";
const BLUE = "rgb(179, 229, 252)";

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

/**
 * Extraction runs in the background, so tests pin the reader's link state by
 * patching the single-link response (A15) instead of waiting on a worker.
 */
async function pinLinkState(
  page: Page,
  linkId: string,
  extraction_status: "pending" | "completed" | "failed",
  extracted_content: string | null
): Promise<void> {
  await page.route(`**/api/v1/projects/*/links/${linkId}`, async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({
      response,
      json: { ...body, extraction_status, extracted_content },
    });
  });
}

async function seedCompletedLink(
  page: Page,
  projectId: string,
  title: string,
  url: string
): Promise<string> {
  const linkId = await seedLink(page, projectId, title, url);
  await pinLinkState(page, linkId, "completed", ARTICLE_HTML);
  return linkId;
}

async function openReader(
  page: Page,
  projectId: string,
  linkId: string
): Promise<void> {
  await page.goto(`/projects/${projectId}/links/${linkId}/read`);
  await expect(
    page.getByRole("heading", { level: 1, name: "Reader Fixture Article" })
  ).toBeVisible();
}

async function selectParagraph(page: Page, index = 0): Promise<void> {
  const paragraph = page.locator("#reader-article p").nth(index);
  await paragraph.selectText();
  await paragraph.dispatchEvent("mouseup");
}

function popup(page: Page) {
  return page.locator("#highlight-popup");
}

test.describe("Reader and highlights (US5)", () => {
  test("shows title, source URL, extracted content, and a back link", async ({
    page,
  }) => {
    const projectId = await createProject(page, "Reader Content Project");
    const linkId = await seedCompletedLink(
      page,
      projectId,
      "Reader Fixture Article",
      "https://example.com/reader-fixture"
    );
    await page.goto(`/projects/${projectId}/links/${linkId}/read`);

    await expect(
      page.getByRole("heading", { level: 1, name: "Reader Fixture Article" })
    ).toBeVisible();

    const source = page.getByRole("link", {
      name: "https://example.com/reader-fixture",
    });
    await expect(source).toHaveAttribute("target", "_blank");
    await expect(source).toHaveAttribute("rel", /noopener/);

    await expect(page.locator("#reader-article")).toContainText(
      "Extracted paragraph one about distributed systems."
    );

    const back = page.getByRole("link", { name: /← Back to / });
    await expect(back).toBeVisible();
    await expect(back).toHaveAttribute("href", `/projects/${projectId}`);
    await expect(
      page.getByRole("link", { name: "+ Add note about this" })
    ).toBeVisible();
  });

  test("shows 'Content not yet extracted.' while extraction is incomplete", async ({
    page,
  }) => {
    const projectId = await createProject(page, "Reader Pending Project");
    const linkId = await seedLink(
      page,
      projectId,
      "Reader Fixture Article",
      "https://example.com/reader-fixture"
    );
    await pinLinkState(page, linkId, "pending", null);
    await page.goto(`/projects/${projectId}/links/${linkId}/read`);

    await expect(
      page.getByText("Content not yet extracted.")
    ).toBeVisible();
    await expect(page.locator("#reader-article")).toHaveCount(0);
  });

  test("selection opens a popup with annotation, six swatches, Save and close; outside click and close dismiss it", async ({
    page,
  }) => {
    const projectId = await createProject(page, "Reader Popup Project");
    const linkId = await seedCompletedLink(
      page,
      projectId,
      "Reader Fixture Article",
      "https://example.com/reader-fixture"
    );
    await openReader(page, projectId, linkId);

    await selectParagraph(page);
    await expect(popup(page)).toBeVisible();
    await expect(popup(page).locator("[data-color]")).toHaveCount(6);
    await expect(popup(page).getByLabel("Note (optional)")).toBeVisible();
    await expect(
      popup(page).getByRole("button", { name: "Save" })
    ).toBeVisible();
    await expect(
      popup(page).getByRole("button", { name: "Close" })
    ).toBeVisible();

    // Clicking outside the popup dismisses it (FR-023)
    await page.getByRole("heading", { level: 1 }).click();
    await expect(popup(page)).toHaveCount(0);

    // The close button dismisses it too, without saving
    await selectParagraph(page);
    await expect(popup(page)).toBeVisible();
    await popup(page).getByRole("button", { name: "Close" }).click();
    await expect(popup(page)).toHaveCount(0);
    await expect(
      page.locator("#reader-article mark.highlight")
    ).toHaveCount(0);
  });

  test("saving paints an instant mark that persists across a reload", async ({
    page,
  }) => {
    const projectId = await createProject(page, "Reader Persist Project");
    const linkId = await seedCompletedLink(
      page,
      projectId,
      "Reader Fixture Article",
      "https://example.com/reader-fixture"
    );
    await openReader(page, projectId, linkId);

    await expect(
      page.getByText("Select any text above to save it as a highlight.")
    ).toBeVisible();

    await selectParagraph(page);
    await expect(popup(page)).toBeVisible();
    await popup(page).getByRole("button", { name: "Save" }).click();

    const mark = page.locator("#reader-article mark.highlight");
    await expect(mark).toHaveCount(1);
    await expect(mark).toHaveText(
      "Extracted paragraph one about distributed systems."
    );
    await expect(mark).toHaveCSS("background-color", YELLOW);
    await expect(popup(page)).toHaveCount(0);
    await expect(
      page
        .locator("#highlights-list")
        .getByText("Extracted paragraph one about distributed systems.")
    ).toBeVisible();

    await page.reload();
    await expect(
      page.locator("#reader-article mark.highlight")
    ).toHaveCount(1);
    await expect(
      page.locator("#reader-article mark.highlight")
    ).toHaveCSS("background-color", YELLOW);
    await expect(
      page
        .locator("#highlights-list")
        .getByText("Extracted paragraph one about distributed systems.")
    ).toBeVisible();
  });

  test("lists highlights with quote, annotation, color, and confirmed Remove", async ({
    page,
  }) => {
    const projectId = await createProject(page, "Reader Panel Project");
    const linkId = await seedCompletedLink(
      page,
      projectId,
      "Reader Fixture Article",
      "https://example.com/reader-fixture"
    );
    await openReader(page, projectId, linkId);

    const emptyState = page.getByText(
      "Select any text above to save it as a highlight."
    );
    await expect(emptyState).toBeVisible();

    await selectParagraph(page);
    await popup(page).getByLabel("Note (optional)").fill("Remember this claim");
    // A swatch click selects the color and submits (FR-023)
    await popup(page).locator('[data-color="blue"]').click();

    const mark = page.locator("#reader-article mark.highlight");
    await expect(mark).toHaveCount(1);
    await expect(mark).toHaveCSS("background-color", BLUE);

    const item = page.locator("#highlights-list li");
    await expect(item).toHaveCount(1);
    await expect(item).toContainText(
      "Extracted paragraph one about distributed systems."
    );
    await expect(item).toContainText("Remember this claim");
    await expect(
      item.locator("[data-testid='highlight-color-swatch']").first()
    ).toHaveCSS("background-color", BLUE);

    await item.getByRole("button", { name: "Remove" }).click();
    await expect(page.locator("dialog")).toContainText(
      "Remove this highlight?"
    );
    await page
      .locator("dialog")
      .getByRole("button", { name: "Remove" })
      .click();

    await expect(page.locator("#reader-article mark.highlight")).toHaveCount(
      0
    );
    await expect(page.locator("#highlights-list li")).toHaveCount(0);
    await expect(emptyState).toBeVisible();
  });

  test("a failed save keeps the popup open with the input intact", async ({
    page,
  }) => {
    const projectId = await createProject(page, "Reader Failure Project");
    const linkId = await seedCompletedLink(
      page,
      projectId,
      "Reader Fixture Article",
      "https://example.com/reader-fixture"
    );
    await page.route(
      "**/api/v1/projects/*/links/*/highlights",
      async (route) => {
        if (route.request().method() === "POST") {
          await route.fulfill({
            status: 500,
            contentType: "application/json",
            json: { detail: "highlight write failed" },
          });
          return;
        }
        await route.continue();
      }
    );
    await openReader(page, projectId, linkId);

    await selectParagraph(page);
    await expect(popup(page)).toBeVisible();
    await popup(page).getByLabel("Note (optional)").fill("Keep this note");
    await popup(page).getByRole("button", { name: "Save" }).click();

    await expect(popup(page).getByRole("alert")).toContainText(
      "Failed to save highlight. Please try again."
    );
    await expect(popup(page)).toBeVisible();
    await expect(popup(page).getByLabel("Note (optional)")).toHaveValue(
      "Keep this note"
    );
    await expect(
      page.locator("#reader-article mark.highlight")
    ).toHaveCount(0);
  });

  test("'Add note about this' returns to Notes with the link preselected", async ({
    page,
  }) => {
    const projectId = await createProject(page, "Reader Add Note Project");
    const linkId = await seedCompletedLink(
      page,
      projectId,
      "Reader Fixture Article",
      "https://example.com/reader-fixture"
    );
    await openReader(page, projectId, linkId);

    await page.getByRole("link", { name: "+ Add note about this" }).click();

    await expect(page).toHaveURL(
      new RegExp(
        `/projects/${projectId}\\?source_link_id=${linkId}#notes-panel$`
      )
    );
    await expect(page.getByRole("tab", { name: "Notes" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    await expect(page.locator("#note-source-link")).toHaveValue(linkId);
  });
});
