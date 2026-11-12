// Fails if any i18n key exists in one language file but not the other, or a value is empty.
import { readFileSync } from 'node:fs'

const langs = ['en', 'hi']
const flat = (obj, prefix = '') =>
  Object.entries(obj).flatMap(([k, v]) =>
    typeof v === 'object' && v !== null ? flat(v, `${prefix}${k}.`) : [[`${prefix}${k}`, v]],
  )
const maps = Object.fromEntries(
  langs.map((l) => [
    l,
    new Map(flat(JSON.parse(readFileSync(new URL(`../src/i18n/${l}.json`, import.meta.url))))),
  ]),
)
const problems = []
const allKeys = new Set(langs.flatMap((l) => [...maps[l].keys()]))
for (const key of allKeys) {
  for (const l of langs) {
    const v = maps[l].get(key)
    if (v === undefined) problems.push(`${l}: missing key ${key}`)
    else if (typeof v !== 'string' || v.trim() === '') problems.push(`${l}: empty value for ${key}`)
  }
}
for (const p of problems) console.error(p)
console.log(`i18n check: ${allKeys.size} keys, ${problems.length} problem(s)`)
process.exit(problems.length ? 1 : 0)
