import Link from 'next/link'

export function Brand() {
  return (
    <Link href="/" className="brand">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/art/brand/logo.png" alt="" width={30} height={30} />
      Sonic Postcards
    </Link>
  )
}
