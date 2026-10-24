const tailwindcss = require('tailwindcss')
const autoprefixer = require('autoprefixer')
const fluidRem = require('./scripts/postcss-fluid-rem.cjs')

module.exports = {
  plugins: [
    tailwindcss(),
    fluidRem(),
    autoprefixer({
      overrideBrowserslist: ['Android 4.1', 'iOS 7.1', 'Chrome > 31', 'ff > 31'],
      grid: true,
    }),
  ],
}
