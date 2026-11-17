// A session's project, as a key that tells projects apart without saying
// which folder each is: the stored summaries and the pane carry the key, never
// the folder's path or name.

/** How many hex digits of the digest a key keeps: enough that a person's projects do not collide. */
const KEY_DIGITS = 10

const hex = (bytes: Uint8Array) => [...bytes].map(byte => byte.toString(16).padStart(2, '0')).join('')

/**
 * The key of a project folder under an install's salt: the first hex digits of
 * the SHA-256 digest of the salt and the folder's absolute path. One folder gets
 * one key however its path is spelled: with either slash, with or without a
 * trailing one, and, for a path with a drive letter (Windows, whose paths
 * ignore case), in any case. The same salt gives the same key on every run, so
 * a project's sessions add up across restarts; without the salt, a guessed
 * path cannot be checked against a key.
 */
export async function projectKey(folder: string, salt: string): Promise<string> {
  let path = folder.replace(/\\/g, '/').replace(/\/+$/, '')
  if (/^[A-Za-z]:/.test(path)) path = path.toLowerCase()
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(`${salt}\n${path}`))
  return hex(new Uint8Array(digest)).slice(0, KEY_DIGITS)
}

/** A new install's salt: 16 random bytes, as hex. */
export function newSalt(): string {
  return hex(crypto.getRandomValues(new Uint8Array(16)))
}
