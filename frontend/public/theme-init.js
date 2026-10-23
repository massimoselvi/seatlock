// Set the theme before first paint. The key and values match VueUse's useDark.
try {
  const stored = localStorage.getItem('vueuse-color-scheme')
  if (stored === 'dark' || (stored !== 'light' && matchMedia('(prefers-color-scheme: dark)').matches))
    document.documentElement.classList.add('dark')
}
catch {}
