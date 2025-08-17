interface MascotProps {
  size?: number;
}

export function Mascot({ size = 28 }: MascotProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <circle
        cx="32"
        cy="32"
        r="28"
        fill="url(#g)"
        stroke="var(--kb-illustration-stroke)"
        strokeWidth="2"
      />
      <defs>
        <linearGradient
          id="g"
          x1="8"
          y1="8"
          x2="56"
          y2="56"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#FB923C" />
          <stop offset="1" stopColor="#F66B0E" />
        </linearGradient>
      </defs>
      <rect
        x="22"
        y="14"
        width="20"
        height="6"
        rx="2"
        fill="#fff"
        opacity="0.8"
      />
      <circle cx="24" cy="28" r="4" fill="#fff" />
      <circle cx="40" cy="28" r="4" fill="#fff" />
      <rect x="22" y="36" width="20" height="8" rx="4" fill="#fff" />
    </svg>
  );
}
