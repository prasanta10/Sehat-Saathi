import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import globals from 'globals'
import tseslint from 'typescript-eslint'

// User-facing text must go through i18n keys. These selectors reject visible
// string literals in JSX: text children and the attributes that screen readers or users see.
const noJsxLiterals = [
  {
    selector: 'JSXText[value=/[A-Za-z\\u0900-\\u097F]/]',
    message: 'User-facing text must use an i18n key (t("...")), not a JSX literal.',
  },
  {
    selector:
      'JSXAttribute[name.name=/^(aria-label|title|placeholder|alt|aria-description)$/] > Literal',
    message: 'User-facing attribute text must use an i18n key.',
  },
  {
    selector: 'JSXExpressionContainer > Literal[value=/[A-Za-z\\u0900-\\u097F]/]',
    message: 'User-facing text must use an i18n key (t("...")), not a string literal.',
  },
]

export default tseslint.config(
  { ignores: ['dist', 'node_modules', 'test-results', 'playwright-report', 'src/api/schema.d.ts'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: { ecmaVersion: 2023, globals: globals.browser },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
    },
  },
  {
    files: ['src/**/*.tsx'],
    rules: { 'no-restricted-syntax': ['error', ...noJsxLiterals] },
  },
)
