import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'DictSQLite',
  description: 'Fast, safe SQLite-backed Python dictionaries',
  base: '/',
  cleanUrls: true,
  themeConfig: {
    nav: [
      { text: 'ホーム', link: '/' },
      { text: 'ガイド', link: '/guide' },
      { text: 'API', link: '/api' },
      { text: 'Benchmark', link: '/performance' },
      { text: 'Release', link: '/release' }
    ],
    sidebar: [
      {
        text: 'DictSQLite',
        items: [
          { text: 'ガイド', link: '/guide' },
          { text: 'API', link: '/api' },
          { text: '保存形式と永続化', link: '/storage' },
          { text: '非同期 API', link: '/async' },
          { text: '安全性', link: '/security' },
          { text: 'パフォーマンス', link: '/performance' },
          { text: 'リリース', link: '/release' },
          { text: '変更履歴', link: '/changelog' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/disnana/DictSQLite' }
    ]
  },
  locales: {
    root: {
      label: '日本語',
      lang: 'ja-JP'
    },
    en: {
      label: 'English',
      lang: 'en-US',
      link: '/en/',
      themeConfig: {
        nav: [
          { text: 'Home', link: '/en/' },
          { text: 'Guide', link: '/en/guide' },
          { text: 'API', link: '/en/api' },
          { text: 'Benchmark', link: '/en/performance' },
          { text: 'Release', link: '/en/release' }
        ],
        sidebar: [
          {
            text: 'DictSQLite',
            items: [
              { text: 'Guide', link: '/en/guide' },
              { text: 'API', link: '/en/api' },
              { text: 'Storage and Persistence', link: '/en/storage' },
              { text: 'Async API', link: '/en/async' },
              { text: 'Safety', link: '/en/security' },
              { text: 'Performance', link: '/en/performance' },
              { text: 'Release', link: '/en/release' },
              { text: 'Changelog', link: '/en/changelog' }
            ]
          }
        ]
      }
    }
  }
})
