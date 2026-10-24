const PX_PATTERN = /(-?\d*\.?\d+)px\b/g
const ROOT_VALUE = 16

function trimNumber(value) {
  return value.toFixed(6).replace(/\.?0+$/, '')
}

module.exports = function fluidRemPlugin() {
  return {
    postcssPlugin: 'mango-fluid-rem',
    Declaration(declaration) {
      const sourceFile = declaration.source?.input?.file || ''
      if (sourceFile.includes('node_modules') && !sourceFile.includes('@arco-design')) return
      if (declaration.prop === 'content' || declaration.value.includes('url(')) return

      declaration.value = declaration.value.replace(PX_PATTERN, (matched, rawValue) => {
        const value = Number(rawValue)
        // 1px 及以下主要用于边框和像素级绘制，保持清晰且避免小数边框。
        if (!Number.isFinite(value) || Math.abs(value) <= 1) return matched
        return `${trimNumber(value / ROOT_VALUE)}rem`
      })
    },
  }
}

module.exports.postcss = true
