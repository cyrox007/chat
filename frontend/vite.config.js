import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

const versionFile = fileURLToPath(new URL('../VERSION', import.meta.url))
const projectVersion = process.env.PUBCHAT_VERSION
  || (existsSync(versionFile) ? readFileSync(versionFile, 'utf8').trim() : '0.0.0-alpha.0+unknown')

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(projectVersion),
  },
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})
