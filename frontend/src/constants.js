const CONDITION_MULTIPLIERS = {
  NM:  1.0,
  LP:  0.75,
  MP:  0.50,
  HP:  0.25,
  DMG: 0.10,
}

// Keep in step with backend/import_limits.py.
export const MAX_IMPORT_LINES = 1000
export const IMPORT_RATE_LIMITED_MESSAGE = 'Too many imports in a short time. Wait a minute and try again.'

export default CONDITION_MULTIPLIERS
