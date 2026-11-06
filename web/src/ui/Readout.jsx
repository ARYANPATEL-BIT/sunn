import { Blob } from './Blob.jsx'
import { Label } from './Label.jsx'

// The dark window on the front of the device: a status line, the voice shape, then printed
// rows (heard, understood). Both themes show it dark, like a real screen.
export function Readout({ blobState, level, top, children, className = '', as: Tag = 'div', ...props }) {
  return (
    <Tag className={`readout ${className}`} {...props}>
      {top && <div className="readout-top">{top}</div>}
      <Blob state={blobState} level={level} />
      <div className="readout-rows">{children}</div>
    </Tag>
  )
}

// One printed row of the readout: its bilingual label, then what goes under it.
export function ReadoutRow({ label, className = '', children }) {
  return (
    <div className={`readout-row ${className}`}>
      <Label k={label} inline className="readout-label" />
      {children}
    </div>
  )
}
