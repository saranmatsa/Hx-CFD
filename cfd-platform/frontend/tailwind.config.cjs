/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        lab: {
          black: '#000000',
          canvas: '#030405',
          rail: '#050607',
          surface: '#0b0d0f',
          raised: '#121518',
          hover: '#181c20',
          line: '#242a30',
          strongLine: '#343c45',
          ink: '#f4f6f8',
          muted: '#a2aab3',
          dim: '#68717b',
          blue: '#2f72e8',
          blueHover: '#4385fa',
          green: '#22c55e',
          amber: '#f4b740',
          red: '#ef665b',
        },
      },
      boxShadow: {
        panel: 'inset 0 1px 0 rgba(255,255,255,.025)',
        floating: '0 18px 50px rgba(0,0,0,.48)',
      },
      fontFamily: {
        ui: ['Inter', 'Segoe UI', 'sans-serif'],
        data: ['IBM Plex Mono', 'Cascadia Mono', 'Consolas', 'monospace'],
      },
      transitionTimingFunction: {
        instrument: 'cubic-bezier(.2,0,0,1)',
      },
    },
  },
  plugins: [],
}
