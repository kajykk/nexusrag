/**
 * ESLint flat config
 * @type {import('eslint').Linter.Config[]}
 */
import tsPlugin from '@typescript-eslint/eslint-plugin'
import tsParser from '@typescript-eslint/parser'
import vuePlugin from 'eslint-plugin-vue'
import vueParser from 'vue-eslint-parser'

export default [
  {
    ignores: [
      'node_modules/**',
      'dist/**',
      'data/**',
      'ai-analytics-workbench/**',
      '**/*.config.js',
      '**/*.config.ts',
    ],
  },
  {
    files: ['**/*.ts'],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        sourceType: 'module',
        ecmaVersion: 2022,
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      // 允许未使用以 _ 开头的参数/变量（约定为有意忽略）
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
      // 允许 any（项目迁移期渐进收紧）
      '@typescript-eslint/no-explicit-any': 'off',
      // 允许空 catch（已在代码中加注释）
      '@typescript-eslint/no-empty-object-type': 'off',
    },
  },
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        sourceType: 'module',
        ecmaVersion: 2022,
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
      vue: vuePlugin,
    },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      ...vuePlugin.configs['vue3-recommended'].rules,
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-explicit-any': 'off',
      // Vue 单文件组件相关：允许多根节点、允许 v-html（Markdown 渲染需要）
      'vue/no-multiple-template-root': 'off',
      'vue/no-v-html': 'off',
      // 允许单词组件名（如 HomePage）
      'vue/multi-word-component-names': 'off',
    },
  },
]
