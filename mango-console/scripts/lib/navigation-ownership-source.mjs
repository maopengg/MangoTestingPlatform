import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

// Follow only the local normalizer actually passed to the list, not arbitrary unused imports.
export function ownershipFormattingSource(
  vuePath,
  vueSource,
  read = (file) => fs.readFileSync(file, 'utf8')
) {
  const scripts = [...vueSource.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)]
    .map((match) => match[1])
    .join('\n')
  const tree = ts.createSourceFile('page.ts', scripts, ts.ScriptTarget.Latest, true)
  const names = new Set()
  function visit(node) {
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      node.expression.text === 'useCaseLibraryList'
    ) {
      const config = node.arguments[0]
      if (config && ts.isObjectLiteralExpression(config)) {
        for (const property of config.properties) {
          if (
            ts.isPropertyAssignment(property) &&
            property.name.getText(tree) === 'normalize' &&
            ts.isIdentifier(property.initializer)
          )
            names.add(property.initializer.text)
          if (ts.isShorthandPropertyAssignment(property) && property.name.text === 'normalize')
            names.add(property.name.text)
        }
      }
    }
    ts.forEachChild(node, visit)
  }
  visit(tree)
  const sources = [vueSource]
  for (const node of tree.statements) {
    if (
      !ts.isImportDeclaration(node) ||
      !ts.isStringLiteral(node.moduleSpecifier) ||
      !node.moduleSpecifier.text.startsWith('.')
    )
      continue
    const bindings = node.importClause?.namedBindings
    if (!bindings || !ts.isNamedImports(bindings)) continue
    for (const binding of bindings.elements) {
      if (!names.has(binding.name.text)) continue
      const imported = binding.propertyName?.text ?? binding.name.text
      const file = path.resolve(path.dirname(vuePath), `${node.moduleSpecifier.text}.ts`)
      let source
      try {
        source = read(file)
      } catch {
        continue
      }
      const helper = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true)
      // The public formatters must be imported from the real shared formatter module.
      const imports = helper.statements.filter(
        (statement) =>
          ts.isImportDeclaration(statement) &&
          ts.isStringLiteral(statement.moduleSpecifier) &&
          statement.moduleSpecifier.text === '@/utils/business-format'
      )
      if (!imports.length) continue
      const declared = new Set(
        imports.flatMap((statement) => {
          const named = statement.importClause?.namedBindings
          return named && ts.isNamedImports(named)
            ? named.elements.filter((item) => !item.propertyName).map((item) => item.name.text)
            : []
        })
      )
      const definition = helper.statements.find(
        (statement) =>
          ts.isFunctionDeclaration(statement) &&
          statement.name?.text === imported &&
          statement.modifiers?.some((modifier) => modifier.kind === ts.SyntaxKind.ExportKeyword)
      )
      if (
        definition &&
        declared.has('formatProjectProductPath') &&
        declared.has('formatModulePath')
      )
        sources.push(definition.getText(helper))
    }
  }
  return sources.join('\n')
}

export function hasOwnershipFormatter(source, field) {
  const method = field === 'project_product' ? 'formatProjectProductPath' : 'formatModulePath'
  return new RegExp(`${method}\\((?:record|source)\\.${field}(?:_data)?\\)`).test(source)
}
