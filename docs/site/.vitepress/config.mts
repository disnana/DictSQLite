import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'ValidKit',
  description: 'Lightweight Python validation library',
  base: '/',
  themeConfig: {
nav: [
  { text: 'ホーム', link: '/' },
  { text: 'ガイド', link: '/guide' },
  { text: 'API', link: '/api' },
  { text: 'Benchmark', link: '/performance' }
],
sidebar: [
  {
    text: 'はじめに',
    items: [
      { text: 'ガイド', link: '/guide' },
      { text: 'チュートリアル', link: '/tutorial' },
      { text: '変更履歴', link: '/changelog' }
    ]
  },
  {
    text: '機能',
    items: [
      { text: 'バリデーション', link: '/validation' },
      { text: '事前コンパイル', link: '/compile' },
      { text: 'エラーハンドリング', link: '/error_handling' },
      { text: 'ベストプラクティス', link: '/best_practices' }
    ]
  },
  {
    text: 'リファレンス',
    items: [
      { text: 'API', link: '/api' },
      { text: 'パフォーマンス', link: '/performance' }
    ]
  }
],
socialLinks: [
  { icon: 'github', link: 'https://github.com/disnana/ValidKit' }
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
      { text: 'Benchmark', link: '/en/performance' }
    ],
    sidebar: [
      {
        text: 'Getting Started',
        items: [
          { text: 'Guide', link: '/en/guide' },
          { text: 'Tutorial', link: '/en/tutorial' },
          { text: 'Changelog', link: '/en/changelog' }
        ]
      },
      {
        text: 'Features',
        items: [
          { text: 'Validation', link: '/en/validation' },
          { text: 'Precompiled Validation', link: '/en/compile' },
          { text: 'Error Handling', link: '/en/error_handling' },
          { text: 'Best Practices', link: '/en/best_practices' }
        ]
      },
      {
        text: 'Reference',
        items: [
          { text: 'API', link: '/en/api' },
          { text: 'Performance', link: '/en/performance' }
        ]
      }
    ]
  }
}
  }
})
