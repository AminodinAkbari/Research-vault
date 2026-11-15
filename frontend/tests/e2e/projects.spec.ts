import { test, expect } from "@playwright/test";

test.describe("Projects Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    // Register and login a fresh user for each test
    await page.goto("/register");
    const timestamp = Date.now();
    const email = `project-${timestamp}@example.com`;
    const password = "testpassword123";

    await page.fill('[name="email"]', email);
    await page.fill('[name="password"]', password);
    await page.fill('[name="confirm_password"]', password);
    await page.click('button[type="submit"]');

    // Should land on dashboard
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("empty state shows invitation to create first project", async ({ page }) => {
    await expect(page.locator("text=No projects yet")).toBeVisible();
    await expect(page.locator("text=Create your first project")).toBeVisible();
  });

  test("create project without reload shows new card immediately", async ({
    page,
  }) => {
    const projectName = "Test Project";
    const projectDescription = "A test description";

    // Fill and submit create form
    await page.fill('form [name="name"]', projectName);
    await page.fill('form [name="description"]', projectDescription);
    await page.click('button[type="submit"]:has-text("Create")');

    // Should not navigate away - still on dashboard
    await expect(page).toHaveURL(/\/dashboard/);

    // New project card appears immediately
    await expect(page.locator(`text=${projectName}`)).toBeVisible();
    await expect(page.locator(`text=${projectDescription}`)).toBeVisible();

    // Form resets
    const nameInput = page.locator('form [name="name"]');
    await expect(nameInput).toHaveValue("");

    const descInput = page.locator('form [name="description"]');
    await expect(descInput).toHaveValue("");
  });

  test("project list shows name, description, and creation date", async ({
    page,
  }) => {
    // Create two projects
    await page.fill('form [name="name"]', "Project One");
    await page.fill('form [name="description"]', "First description");
    await page.click('button[type="submit"]:has-text("Create")');
    await expect(page.locator('text="Project One"')).toBeVisible();

    await page.fill('form [name="name"]', "Project Two");
    await page.fill('form [name="description"]', "Second description");
    await page.click('button[type="submit"]:has-text("Create")');
    await expect(page.locator('text="Project Two"')).toBeVisible();

    // Both should be visible with descriptions
    await expect(page.locator('text="First description"')).toBeVisible();
    await expect(page.locator('text="Second description"')).toBeVisible();

    // Created date should be visible (today's date)
    const today = new Date().toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
    await expect(page.locator(`text=${today}`).first()).toBeVisible();
  });

  test("clicking project navigates to workspace", async ({ page }) => {
    const projectName = "Workspace Test";
    await page.fill('form [name="name"]', projectName);
    await page.click('button[type="submit"]:has-text("Create")');
    await expect(page.locator(`text=${projectName}`)).toBeVisible();

    // Click the project card
    await page.click(`text=${projectName} >> nth=0`);

    // Should navigate to project workspace
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]+/);

    // Workspace should have project header and four tabs
    await expect(page.getByRole("tab", { name: "Notes" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Links" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Web Search" })).toBeVisible();
    await expect(page.getByRole("tab", { name: "Tags" })).toBeVisible();
  });

  test("non-existent project ID shows not-found view", async ({ page }) => {
    const fakeId = "00000000-0000-0000-0000-000000000000";
    await page.goto(`/projects/${fakeId}`);

    // Should show not-found view
    await expect(page.getByRole("heading", { name: "Not found" })).toBeVisible();
    await expect(page.locator("text=back to dashboard")).toBeVisible();
  });

  test("another user's project shows forbidden view", async ({ page }) => {
    // Create a project first
    await page.fill('form [name="name"]', "Owned Project");
    await page.click('button[type="submit"]:has-text("Create")');

    // Get the project ID from URL after clicking
    await page.click('text="Owned Project"');
    await expect(page).toHaveURL(/\/projects\/([a-f0-9-]+)/);
    const projectUrl = page.url();

    // Logout
    await page.click('button:has-text("Log out")');
    await expect(page).toHaveURL(/\/login/);

    // Register a different user
    await page.goto("/register");
    const timestamp = Date.now();
    const email = `other-${timestamp}@example.com`;
    const password = "testpassword123";

    await page.fill('[name="email"]', email);
    await page.fill('[name="password"]', password);
    await page.fill('[name="confirm_password"]', password);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);

    // Try to access the first user's project
    await page.goto(projectUrl);

    // Should show not-found/forbidden view
    await expect(page.getByRole("heading", { name: "Not found" })).toBeVisible();
    await expect(page.locator("text=back to dashboard")).toBeVisible();
  });
});