import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test("redirects unauthenticated user from protected page to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });

  test("login with valid credentials lands on dashboard and session persists", async ({
    page,
  }) => {
    // First register a fresh account
    await page.goto("/register");
    const timestamp = Date.now();
    const email = `test-${timestamp}@example.com`;
    const password = "testpassword123";

    await page.fill('[name="email"]', email);
    await page.fill('[name="password"]', password);
    await page.fill('[name="confirm_password"]', password);
    await page.click('button[type="submit"]');

    // Should land on dashboard
    await expect(page).toHaveURL(/\/dashboard/);

    // Navigate away and back — session should persist
    await page.goto("/");
    await expect(page).toHaveURL(/\/dashboard/);

    // Refresh — session should still persist
    await page.reload();
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test("login with wrong credentials shows inline error and preserves form", async ({
    page,
  }) => {
    await page.goto("/login");

    const emailInput = page.locator('[name="email"]');
    const passwordInput = page.locator('[name="password"]');

    await emailInput.fill("wrong@example.com");
    await passwordInput.fill("wrongpassword");
    await page.click('button[type="submit"]');

    // Inline error message
    await expect(page.locator('[role="alert"]')).toContainText(
      "Invalid email or password."
    );

    // Form input preserved
    await expect(emailInput).toHaveValue("wrong@example.com");
    await expect(passwordInput).toHaveValue("wrongpassword");
  });

  test("register validation: password mismatch shows client-side error", async ({
    page,
  }) => {
    await page.goto("/register");

    await page.fill('[name="email"]', "test@example.com");
    await page.fill('[name="password"]', "password123");
    await page.fill('[name="confirm_password"]', "differentpassword");
    await page.click('button[type="submit"]');

    // Client-side error — no request sent (stays on /register)
    await expect(page).toHaveURL(/\/register/);
    await expect(page.locator('[role="alert"]')).toContainText(
      "Passwords do not match"
    );
  });

  test("register validation: password less than 8 chars shows client-side error", async ({
    page,
  }) => {
    await page.goto("/register");

    await page.fill('[name="email"]', "test@example.com");
    await page.fill('[name="password"]', "short");
    await page.fill('[name="confirm_password"]', "short");
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/\/register/);
    await expect(page.locator('[role="alert"]')).toContainText(
      "at least 8 characters"
    );
  });

  test("register with duplicate email shows server 409 error inline", async ({
    page,
  }) => {
    // First register
    await page.goto("/register");
    const timestamp = Date.now();
    const email = `dup-${timestamp}@example.com`;
    const password = "testpassword123";

    await page.fill('[name="email"]', email);
    await page.fill('[name="password"]', password);
    await page.fill('[name="confirm_password"]', password);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);

    // Logout
    await page.click('button:has-text("Log out")');
    await expect(page).toHaveURL(/\/login/);

    // Try to register with same email
    await page.goto("/register");
    await page.fill('[name="email"]', email);
    await page.fill('[name="password"]', password);
    await page.fill('[name="confirm_password"]', password);
    await page.click('button[type="submit"]');

    // Server 409 error shown inline
    await expect(page).toHaveURL(/\/register/);
    await expect(page.locator('[role="alert"]')).toContainText(
      /already|exists|registered/i
    );
  });

  test("logout destroys session and protects pages", async ({ page }) => {
    // Register and login
    await page.goto("/register");
    const timestamp = Date.now();
    const email = `logout-${timestamp}@example.com`;
    const password = "testpassword123";

    await page.fill('[name="email"]', email);
    await page.fill('[name="password"]', password);
    await page.fill('[name="confirm_password"]', password);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);

    // Logout
    await page.click('button:has-text("Log out")');
    await expect(page).toHaveURL(/\/login/);

    // Protected page should redirect to login
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });
});
