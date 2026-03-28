import { useState, useEffect } from 'react'

// Matches touch/pointer-based devices regardless of screen resolution.
// Uses (pointer: coarse) rather than a pixel-width breakpoint so that
// high-DPI phones with large logical viewports still get the mobile layout.
const MOBILE_QUERY = '(pointer: coarse)'

export function useIsMobile() {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia(MOBILE_QUERY).matches)

  useEffect(() => {
    const mq = window.matchMedia(MOBILE_QUERY)
    const handler = e => setIsMobile(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  return isMobile
}
