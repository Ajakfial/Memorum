import { hueToBackground, initials, STATUS_COLOR } from "../lib/color";

interface Props {
  name: string;
  hue: number;
  size?: number;
  status?: string;
}

export function HexAvatar({ name, hue, size = 38, status }: Props) {
  return (
    <div
      className="hex-avatar"
      style={{ width: size, height: size, background: hueToBackground(hue), fontSize: size * 0.36 }}
    >
      {initials(name)}
      {status && <span className="status-dot" style={{ background: STATUS_COLOR[status] }} />}
    </div>
  );
}
