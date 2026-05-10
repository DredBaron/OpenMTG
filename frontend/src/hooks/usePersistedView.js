import { useState } from 'react'

export function usePersistedView(key, defaultValue) {
  const [value, setValue] = useState(() => localStorage.getItem(key) || defaultValue)
  const set = (v) => { setValue(v); localStorage.setItem(key, v) }
  return [value, set]
}
