import { Icon } from './icons.jsx'
import { Label } from './Label.jsx'

// Ranked rows on a panel: a mono rank (02, 03…), the phrase, a chevron, hairlines between.
export function RankedList({ title, children, className = '' }) {
  return (
    <section className={`ranked ${className}`}>
      {title && <Label k={title} inline className="ranked-title" />}
      <div className="ranked-rows">{children}</div>
    </section>
  )
}

export const rank = (n) => String(n).padStart(2, '0')

// The inside of one row; the caller decides whether the row is a button or a still picture.
export function RankedFace({ n, icon = 'chevronRight', children }) {
  return (
    <>
      <span className="rank" aria-hidden="true">
        {n == null ? '' : rank(n)}
      </span>
      <span className="ranked-body">{children}</span>
      <Icon name={icon} className="ranked-chevron" />
    </>
  )
}
