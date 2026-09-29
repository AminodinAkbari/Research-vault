import { test, expect, request as playwrightRequest } from "@playwright/test";
import type { Page, Locator } from "@playwright/test";
import path from "path";

const PASSWORD = "testpassword123";
const authStatePath = path.join(
  __dirname,
  `../fixtures/notes-auth-${process.pid}.json`
);

test.beforeAll(async ({ baseURL }) => {
  const api = await playwrightRequest.newContext({
    baseURL,
    storageState: { cookies: [], origins: [] },
  });
  try {
    const res = await api.post("/api/v1/auth/register", {
      data: {
        email: `notes-${Date.now()}-${process.pid}@example.com`,
        password: PASSWORD,
      },
    });
    expect(
      res.ok(),
      `register failed: ${res.status()} ${await res.text()}`
    ).toBeTruthy();
    await api.storageState({ path: authStatePath });
  } finally {
    await api.dispose();
  }
});

test.use({ storageState: authStatePath });

async function createProject(page: Page, name: string): Promise<string> {
  await page.goto("/dashboard");
  await page.fill('form [name="name"]', name);
  await page.click('button[type="submit"]:has-text("Create")');
  await expect(page.locator(`text=${name}`)).toBeVisible();
  await page.click(`text=${name} >> nth=0`);
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
  const res = await page.request.post(
    `/api/v1/projects/${projectId}/links`,
    { data: { url, title } }
  );
  expect(res.ok(), `link create failed: ${res.status()}`).toBeTruthy();
  const body = await res.json();
  return body.id as string;
}

function notesPanel(page: Page): Locator {
  return page.locator("#notes-panel");
}

async function createNote(
  page: Page,
  title: string,
  content: string
): Promise<Locator> {
  const panel = notesPanel(page);
  const form = panel.locator('form[aria-label="Create a new note"]');
  await form.locator('[name="title"]').fill(title);
  await form.locator('[name="content"]').fill(content);
  await panel.getByRole("button", { name: "Add note" }).click();
  const item = panel.locator("article").filter({ hasText: title });
  await expect(item).toBeVisible();
  return item;
}

test.describe("Notes and tags (US3)", () => {
  test("create note appends it to the list and resets the form", async ({
    page,
  }) => {
    await createProject(page, "Notes Create Project");
    const panel = notesPanel(page);
    const form = panel.locator('form[aria-label="Create a new note"]');

    await form.locator('[name="title"]').fill("First note");
    await form.locator('[name="content"]').fill("Some note content");
    await panel.getByRole("button", { name: "Add note" }).click();

    const item = panel.locator("article").filter({ hasText: "First note" });
    await expect(item).toBeVisible();
    await expect(item).toContainText("Some note content");

    await expect(form.locator('[name="title"]')).toHaveValue("");
    await expect(form.locator('[name="content"]')).toHaveValue("");
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+$/);
  });

  test("source link selector lists project links and preselects from ?source_link_id", async ({
    page,
  }) => {
    const projectId = await createProject(page, "Notes Source Project");
    const linkId = await seedLink(
      page,
      projectId,
      "Example Source Article",
      "https://example.com/source-article"
    );
    await page.reload();

    const panel = notesPanel(page);
    const select = panel.locator(
      'form[aria-label="Create a new note"] [name="source_link_id"]'
    );

    // All of the project's links are selectable
    await expect(select.locator("option")).toHaveCount(2);
    await expect(select.locator("option").nth(1)).toHaveText(
      "Example Source Article"
    );
    await expect(select).toHaveValue("");

    // Arriving from the reader's "Add note about this" preselects the link
    await page.goto(`/projects/${projectId}?source_link_id=${linkId}`);
    await expect(
      panel.locator(
        'form[aria-label="Create a new note"] [name="source_link_id"]'
      )
    ).toHaveValue(linkId);
    await expect(page.getByRole("tab", { name: "Notes" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
  });

  test("inline edit saves in place and cancel restores the previous view", async ({
    page,
  }) => {
    await createProject(page, "Notes Edit Project");
    const panel = notesPanel(page);
    await createNote(page, "Editable note", "Original body");

    const item = panel.locator("article").filter({ hasText: "Editable note" });
    await item.getByRole("button", { name: "Edit" }).click();

    const editForm = panel.locator('form[aria-label="Edit note"]');
    await expect(editForm.locator('[name="title"]')).toHaveValue(
      "Editable note"
    );
    await expect(editForm.locator('[name="content"]')).toHaveValue(
      "Original body"
    );

    await editForm.locator('[name="title"]').fill("Updated note");
    await editForm.getByRole("button", { name: "Save" }).click();

    await expect(
      panel.locator("article").filter({ hasText: "Updated note" })
    ).toBeVisible();
    await expect(panel.locator('form[aria-label="Edit note"]')).toHaveCount(0);

    // Cancel restores the previous view without saving
    const updatedItem = panel
      .locator("article")
      .filter({ hasText: "Updated note" });
    await updatedItem.getByRole("button", { name: "Edit" }).click();
    await panel
      .locator('form[aria-label="Edit note"] [name="title"]')
      .fill("Discarded title");
    await panel
      .locator('form[aria-label="Edit note"]')
      .getByRole("button", { name: "Cancel" })
      .click();

    await expect(panel.getByText("Discarded title")).toHaveCount(0);
    await expect(
      panel.locator("article").filter({ hasText: "Updated note" })
    ).toBeVisible();
  });

  test("delete with confirmation removes the note from the list", async ({
    page,
  }) => {
    await createProject(page, "Notes Delete Project");
    const panel = notesPanel(page);
    await createNote(page, "Doomed note", "To be deleted");

    const item = panel.locator("article").filter({ hasText: "Doomed note" });
    await item.getByRole("button", { name: "Delete" }).click();

    await expect(page.locator("dialog")).toContainText(
      "Delete this note? This cannot be undone."
    );
    await page.locator("dialog").getByRole("button", { name: "Delete" }).click();

    await expect(
      panel.locator("article").filter({ hasText: "Doomed note" })
    ).toHaveCount(0);
  });

  test("attaching and detaching a tag updates the note immediately", async ({
    page,
  }) => {
    await createProject(page, "Notes Tag Project");

    // Create a project tag from the Tags tab
    await page.getByRole("tab", { name: "Tags" }).click();
    const tagsPanel = page.locator("#tags-panel");
    await tagsPanel.locator('[name="name"]').fill("Research");
    await tagsPanel.getByRole("button", { name: "Add tag" }).click();
    await expect(tagsPanel.getByText("Research")).toBeVisible();

    // Attach it to a note from the Notes tab
    await page.getByRole("tab", { name: "Notes" }).click();
    await createNote(page, "Tagged note", "Body of tagged note");

    const item = notesPanel(page)
      .locator("article")
      .filter({ hasText: "Tagged note" });
    await item.getByRole("button", { name: "Attach tag" }).click();
    await item.getByRole("button", { name: "+ Research" }).click();

    // Attached badge appears immediately — no reload
    const badge = item.locator('[title^="Remove tag"]');
    await expect(badge).toBeVisible();
    await expect(badge).toHaveAttribute("title", 'Remove tag "Research"');

    // Detach via the badge — updates immediately, no reload
    await badge.click();
    await expect(item.locator('[title^="Remove tag"]')).toHaveCount(0);
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+$/);
  });

  test("shows a loading placeholder while fetching and an empty state when there are no notes", async ({
    page,
  }) => {
    const projectId = await createProject(page, "Notes Empty Project");
    const panel = notesPanel(page);

    await expect(panel.getByText("No notes yet")).toBeVisible();
    await expect(panel.getByText("Add your first note above.")).toBeVisible();

    const notesRoute = "**/api/v1/projects/*/notes**";
    await page.route(notesRoute, async (route) => {
      if (route.request().method() === "GET") {
        await new Promise((resolve) => setTimeout(resolve, 1500));
      }
      await route.continue();
    });

    await page.goto(`/projects/${projectId}`);
    await expect(page.getByText("Loading notes…")).toBeVisible();

    await page.unroute(notesRoute);
    await expect(panel.getByText("No notes yet")).toBeVisible();
  });
});
