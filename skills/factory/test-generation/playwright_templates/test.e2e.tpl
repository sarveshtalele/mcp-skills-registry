import {{ test, expect }} from '@playwright/test';

test('{module} e2e', async ({{ page }}) => {{
  await page.goto('/');
  // TODO: drive {module}
}});
