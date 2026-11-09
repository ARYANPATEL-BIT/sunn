// Every language file has exactly en.js's keys, the same kind of value (text or list) and the
// same {slots}. Run with `npm test`.
import assert from 'node:assert/strict'
import { readdirSync } from 'node:fs'
import { test } from 'node:test'
import en from './en.js'
import { LANGUAGES, REVIEWED } from './languages.js'

// Every {slot} in a value, including the texts inside lists.
const slots = (value) => [...new Set(JSON.stringify(value).match(/\{\w+\}/g) || [])].sort()

const files = readdirSync(new URL('.', import.meta.url)).filter((f) => /^[a-z]{2}\.js$/.test(f))

test('every language in the picker has a file, and every file is in the picker', () => {
  assert.deepEqual(files.map((f) => f.slice(0, 2)).sort(), LANGUAGES.map((l) => l.code).sort())
  for (const code of REVIEWED) assert.ok(LANGUAGES.some((l) => l.code === code), code)
})

for (const file of files.filter((f) => f !== 'en.js')) {
  test(`${file} matches en.js`, async () => {
    const strings = (await import(`./${file}`)).default
    const missing = Object.keys(en).filter((k) => !(k in strings))
    const extra = Object.keys(strings).filter((k) => !(k in en))
    assert.deepEqual(missing, [], `${file} is missing keys`)
    assert.deepEqual(extra, [], `${file} has keys en.js doesn't have`)
    for (const [key, value] of Object.entries(en)) {
      assert.equal(Array.isArray(strings[key]), Array.isArray(value), `${file} ${key}: text or list`)
      assert.deepEqual(slots(strings[key]), slots(value), `${file} ${key}: placeholders`)
    }
  })
}
