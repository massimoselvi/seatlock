import antfu from '@antfu/eslint-config'

export default antfu({
  type: 'app',
  antislop: true,
  vue: { a11y: true },
  typescript: true,
  ignores: ['dist', '**/*.css', 'index.html'],
})
