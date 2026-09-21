import { expect, test } from '@playwright/test';

const PASSWORD = 'BrowserGate-2026!';

const projectHandle = (projectName) => {
  const suffix = Date.now().toString(36);
  const project = projectName.replace(/[^a-z0-9]/gi, '').toLowerCase().slice(0, 10);
  return `pw${project}${suffix}`.slice(0, 30);
};

const assertNoPersistedBearer = async (page) => {
  const persisted = await page.evaluate(() => ({
    accessToken: localStorage.getItem('access_token'),
    sessionToken: sessionStorage.getItem('access_token'),
  }));
  expect(persisted.accessToken).toBeNull();
  expect(persisted.sessionToken).toBeNull();
};

const logout = async (page) => {
  const routeProgress = page.locator('.route-progress');
  await expect(routeProgress).toHaveCount(0);

  const trigger = page.locator('.persona-trigger');
  await expect(trigger).toBeVisible();
  await trigger.focus();
  await trigger.press('Enter');
  await expect(trigger).toHaveAttribute('aria-expanded', 'true');

  const logoutItem = page.getByRole('menuitem', { name: 'Выйти' });
  await expect(logoutItem).toBeVisible();
  await logoutItem.focus();
  await logoutItem.press('Enter');
  await expect(page).toHaveURL(/\/login$/);
};

test('registration, refresh rotation, logout and login survive real browser cookie rules', async ({ page, context }, testInfo) => {
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(String(error)));

  await page.addInitScript(() => {
    window.__pubchatNotificationPermissionRequests = 0;
    if ('Notification' in window && typeof Notification.requestPermission === 'function') {
      Notification.requestPermission = async () => {
        window.__pubchatNotificationPermissionRequests += 1;
        return Notification.permission;
      };
    }
  });

  const handle = projectHandle(testInfo.project.name);
  const displayName = `Browser ${testInfo.project.name}`;

  await page.goto('/registration');
  await expect(page.getByRole('heading', { name: 'Создайте свой образ' })).toBeVisible();

  await page.getByLabel('Как вас называть?').fill(displayName);
  await page.getByLabel('Уникальный адрес').fill(handle);
  await page.getByRole('button', { name: 'Продолжить' }).click();

  await page.getByLabel('Пароль', { exact: true }).fill(PASSWORD);
  await page.getByLabel('Повторите пароль').fill(PASSWORD);
  await page.getByRole('button', { name: 'Войти в PubChat' }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator('.persona-trigger')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Найдите место, куда хочется вернуться' })).toBeVisible();
  await assertNoPersistedBearer(page);

  const refreshCookie = (await context.cookies()).find((item) => item.name === 'refresh_token');
  expect(refreshCookie).toBeTruthy();
  expect(refreshCookie.httpOnly).toBe(true);
  expect(refreshCookie.sameSite).toBe('Lax');

  // Full reload destroys the in-memory access token. The SPA must recover using
  // the HttpOnly refresh cookie plus a newly bootstrapped CSRF header proof.
  const refreshResponse = page.waitForResponse(
    (response) => response.url().includes('/api/identity/v2/refresh') && response.status() === 200,
  );
  await page.reload();
  await refreshResponse;
  await expect(page.locator('.persona-trigger')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Найдите место, куда хочется вернуться' })).toBeVisible();
  await assertNoPersistedBearer(page);

  // Core authenticated surfaces should remain routable after refresh recovery.
  await page.goto('/messenger');
  await expect(page).toHaveURL(/\/messenger$/);
  await expect(page.locator('a[href="/messenger"]:visible').first()).toBeVisible();

  // Browser defaults differ in headless environments, so permission state is not
  // a reliable prompt signal. Count direct requestPermission calls instead.
  const permissionRequests = await page.evaluate(
    () => window.__pubchatNotificationPermissionRequests || 0,
  );
  expect(permissionRequests).toBe(0);

  await logout(page);
  expect((await context.cookies()).some((item) => item.name === 'refresh_token')).toBe(false);
  await assertNoPersistedBearer(page);

  // Login itself is another unsafe request and must work without relying on a
  // mount-time race for CSRF bootstrap.
  await page.getByLabel('Логин или email').fill(handle);
  const loginPassword = page.getByLabel('Пароль');
  await loginPassword.fill(PASSWORD);
  await loginPassword.press('Enter');
  await expect(page).toHaveURL(/\/$/);
  await expect(page.locator('.persona-trigger')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Найдите место, куда хочется вернуться' })).toBeVisible();
  await assertNoPersistedBearer(page);

  expect(pageErrors).toEqual([]);
});
