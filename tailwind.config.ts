import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'y2k-yellow': '#ffe100',
        'y2k-orange': '#ff7f00',
        'y2k-magenta': '#ff00c8',
        'y2k-gray': '#e0e0e0',
        'forest-green': '#0a2810',
        'gold': '#c4a164',
        'light-gold': '#e6d5b8',
        'emerald': '#50c878',
      },
      fontFamily: {
        orbitron: ['var(--font-orbitron)', 'sans-serif'],
        cinzel: ['var(--font-cinzel-decorative)', 'cursive'],
      },
    },
  },
  plugins: [],
};

export default config; 