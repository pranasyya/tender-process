'use client';

import React from "react"

import { Header } from '@/components/Header';

export function LayoutContent({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Header />
      {children}
    </>
  );
}
