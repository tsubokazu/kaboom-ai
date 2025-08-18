"use client";
import React from "react";

export const IconBase = ({ size = 20, stroke = "currentColor", children }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>{children}</svg>
);

export const Bell = (p) => (<IconBase {...p}><path d="M18 8a6 6 0 10-12 0c0 7-3 7-3 7h18s-3 0-3-7"/><path d="M13.73 21a2 2 0 01-3.46 0"/></IconBase>);
export const Wifi = (p) => (<IconBase {...p}><path d="M5 12a9 9 0 0114 0"/><path d="M8.5 15.5a5 5 0 017 0"/><path d="M12 19h.01"/></IconBase>);
export const ChevronDown = (p) => (<IconBase {...p}><polyline points="6 9 12 15 18 9"/></IconBase>);
export const Sun = (p) => (<IconBase {...p}><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></IconBase>);
export const Moon = (p) => (<IconBase {...p}><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></IconBase>);
export const Search = (p) => (<IconBase {...p}><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></IconBase>);
export const Play = (p) => (<IconBase {...p}><polygon points="6 4 20 12 6 20 6 4"/></IconBase>);
export const Pause = (p) => (<IconBase {...p}><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></IconBase>);
export const Square = (p) => (<IconBase {...p}><rect x="4" y="4" width="16" height="16" rx="2"/></IconBase>);
export const RotateCcw = (p) => (<IconBase {...p}><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 108.49-11"/></IconBase>);
export const Download = (p) => (<IconBase {...p}><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></IconBase>);

export const Mascot = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="32" cy="32" r="28" fill="url(#g)" stroke="var(--kb-illustration-stroke)" strokeWidth="2"/>
    <defs>
      <linearGradient id="g" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
        <stop stopColor="#FB923C"/>
        <stop offset="1" stopColor="#F66B0E"/>
      </linearGradient>
    </defs>
    <rect x="22" y="14" width="20" height="6" rx="2" fill="#fff" opacity="0.8"/>
    <circle cx="24" cy="28" r="4" fill="#fff"/>
    <circle cx="40" cy="28" r="4" fill="#fff"/>
    <rect x="22" y="36" width="20" height="8" rx="4" fill="#fff"/>
  </svg>
);

