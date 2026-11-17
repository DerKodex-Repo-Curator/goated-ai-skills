// A session's project, as a key that tells projects apart without saying
// which folder each is: the stored summaries and the pane carry the key, never
// the folder's path or name.

/** How many hex digits of the digest a key keeps: enough that a person's projects do not collide. */
const KEY_DIGITS = 10

/**
 * The key of a project folder: the first hex digits of the SHA-256 digest of
 * its absolute path. One folder gets one key however its path is spelled: with
 * either slash, with or without a trailing one, and, for a path with a drive
 * letter (Windows, whose paths ignore case), in any case. The key is the same
 * on every run, so sessions of one project add up across restarts; it hides
 * the path from a reader of the store, though anyone who guesses a path can
 * check the guess.
 */
export async function projectKey(folder: string): Promise<string> {
  let path = folder.replace(/\\/g, '/').replace(/\/+$/, '')
  if (/^[A-Za-z]:/.test(path)) path = path.toLowerCase()
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(path))
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('').slice(0, KEY_DIGITS)
}
