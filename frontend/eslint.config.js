import antfu from '@antfu/eslint-config'

export default antfu({
  type: 'app',
  antislop: true,
  vue: { a11y: true },
  typescript: true,
  ignores: ['dist', '**/*.css', 'index.html'],
}, {
  rules: {
    // A label is valid with either nesting or a matching id; the default demands both.
    'vue-a11y/label-has-for': ['error', { required: { some: ['nesting', 'id'] } }],
  },
})
