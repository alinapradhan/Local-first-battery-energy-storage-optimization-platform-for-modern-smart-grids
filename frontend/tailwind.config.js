export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        grid: { bg: '#071014', panel: '#0c1b22', line: '#1a3a44', cyan: '#00e5ff', green: '#35f2a0', amber: '#ffb020' }
      },
      boxShadow: { glow: '0 0 32px rgba(0, 229, 255, 0.18)' }
    }
  },
  plugins: []
};
