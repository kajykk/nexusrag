import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.test.ts'],
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      // 防回退护栏：新代码不得整体拉低覆盖（当前基线见下），逐步补测后上调
      thresholds: {
        lines: 55,
        functions: 50,
        statements: 55,
        branches: 40,
      },
      exclude: [
        'src/main.ts',
        'src/**/*.d.ts',
        'tests/**',
        'api/**',
        'dist/**',
        'public/**',
      ],
    },
  },
})