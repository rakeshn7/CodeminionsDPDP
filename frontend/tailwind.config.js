/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      boxShadow: {
        panel: '0 18px 50px rgba(15, 23, 42, 0.28)',
      },
      colors: {
        brand: {
          50: '#ecfeff',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#0f172a',
        },
      },
    },
  },
  plugins: [],
}
