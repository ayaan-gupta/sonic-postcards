'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { InfoIcon, MapIcon, MicIcon, NearbyIcon, SentIcon } from './icons'

const TABS = [
  { href: '/', label: 'Map', icon: MapIcon },
  { href: '/nearby', label: 'Nearby', icon: NearbyIcon },
  { href: '/record', label: 'Record', icon: MicIcon, primary: true },
  { href: '/latest', label: 'Latest', icon: SentIcon },
  { href: '/about', label: 'About', icon: InfoIcon },
] as const

export function TabBar() {
  const pathname = usePathname()
  return (
    <nav className="tabbar glass" aria-label="Main">
      {TABS.map((tab) => {
        const current = tab.href === '/' ? pathname === '/' : pathname.startsWith(tab.href)
        const TabIcon = tab.icon
        if ('primary' in tab) {
          return (
            <Link key={tab.href} href={tab.href} className="tabbar__record" aria-label="Record a postcard" aria-current={current ? 'page' : undefined}>
              <TabIcon />
            </Link>
          )
        }
        return (
          <Link key={tab.href} href={tab.href} className="tabbar__item" aria-current={current ? 'page' : undefined}>
            <TabIcon />
            {tab.label}
          </Link>
        )
      })}
    </nav>
  )
}
