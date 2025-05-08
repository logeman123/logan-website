import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'accent': 'var(--accent)',
      },
      spacing: {
        '128': '32rem',
        '144': '36rem',
      },
      container: {
        center: true,
        padding: {
          DEFAULT: '1rem',
          sm: '2rem',
          lg: '4rem',
          xl: '5rem',
          '2xl': '6rem',
        },
        screens: {
          sm: '640px',
          md: '768px',
          lg: '1024px',
          xl: '1280px',
          '2xl': '1536px',
        },
      },
      fontFamily: {
        sans: ['var(--font-helvetica)', 'system-ui', 'sans-serif'],
      },
      letterSpacing: {
        'wider': '.1em',
        'widest': '.25em',
      },
    },
  },
  plugins: [],
};

export default config; 