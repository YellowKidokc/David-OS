import { defineConfig } from 'vite';
import { fileURLToPath, URL } from 'node:url';

export default defineConfig({
  resolve: {
    alias: {
      'lucide-react': fileURLToPath(new URL('./src/vendor/lucide-react.jsx', import.meta.url)),
    },
  },
});
