#!/usr/bin/env node
/**
 * Guardián del sistema de diseño.
 *
 * Las pantallas (src/features, App.tsx, main.tsx) no pueden definir estilos propios:
 * los colores, tamaños y formas viven en src/styles/theme.css y en src/design-system.
 * Falla si encuentra, en las pantallas:
 *   - el atributo style={...}
 *   - valores arbitrarios de Tailwind, como w-[200px] o bg-[#fff]
 *   - colores crudos de la paleta de Tailwind, como bg-red-500 (usa los tokens: bg-destructive)
 * Y en cualquier archivo de src, salvo theme.css: colores hexadecimales sueltos.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const SRC = fileURLToPath(new URL('../src', import.meta.url))

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    return statSync(path).isDirectory() ? walk(path) : [path]
  })
}

const files = walk(SRC).filter((f) => /\.(tsx?|css)$/.test(f))
const isScreen = (rel) =>
  /\.tsx?$/.test(rel) &&
  !/\.test\.tsx?$/.test(rel) &&
  (rel.startsWith(`features${sep}`) || rel === 'App.tsx' || rel === 'main.tsx')

const PALETTE =
  /\b(?:bg|text|border|ring|fill|stroke|from|to|via|outline|divide|decoration)-(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3}\b/

const screenRules = [
  { re: /\bstyle\s*=\s*\{/, msg: 'No uses style={...}: usa un componente del sistema de diseño.' },
  { re: /[\w:-]-\[[^\]\s]+\]/, msg: 'No uses valores arbitrarios de Tailwind (ej. w-[200px]).' },
  { re: PALETTE, msg: 'No uses colores crudos de Tailwind: usa los tokens (bg-primary, text-destructive...).' },
]
const globalRules = [{ re: /#[0-9a-fA-F]{3,8}\b/, msg: 'No uses colores hexadecimales: defínelos en theme.css.' }]

const problems = []
for (const file of files) {
  const rel = relative(SRC, file)
  const lines = readFileSync(file, 'utf8').split(/\r?\n/)
  const rules = [
    ...(isScreen(rel) ? screenRules : []),
    ...(rel.endsWith('theme.css') ? [] : globalRules),
  ]
  lines.forEach((line, i) => {
    const code = line.replace(/\/\/.*$/, '').replace(/\/\*.*?\*\//g, '')
    for (const { re, msg } of rules) {
      if (re.test(code)) problems.push(`${rel}:${i + 1}  ${msg}\n    ${line.trim()}`)
    }
  })
}

if (problems.length) {
  console.error(`\nSistema de diseño: ${problems.length} problema(s)\n`)
  console.error(problems.join('\n'))
  process.exit(1)
}
console.log('Sistema de diseño: sin problemas.')
