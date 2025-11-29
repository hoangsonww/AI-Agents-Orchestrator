// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  // Disable server-side rendering for a full client-side experience
  ssr: false,

  // Global page headers: https://go.nuxtjs.dev/config-head
  app: {
    head: {
      title: 'AI Agents Orchestrator',
      htmlAttrs: {
        lang: 'en'
      },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { hid: 'description', name: 'description', content: 'A UI for managing AI agents orchestration.' }
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }
      ]
    },
  },

  // Global CSS: https://go.nuxtjs.dev/config-css
  css: [
    '~/src/style.css',
  ],

  // Plugins to run before rendering page: https://go.nuxtjs.dev/config-plugins
  plugins: [
  ],

  // Modules for dev and build (recommended): https://go.nuxtjs.dev/config-modules
  modules: [
    // https://go.nuxtjs.dev/tailwindcss
    '@nuxtjs/tailwindcss',
  ],

  // Build Configuration: https://go.nuxtjs.dev/config-build
  build: {
  },

  // Dev server configuration
  devServer: {
    port: 3000,
  },

  // Vite configuration
  vite: {
    // Vite specific options
  },
})
