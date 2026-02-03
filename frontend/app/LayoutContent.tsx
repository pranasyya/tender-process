'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';
import {
  LayoutGrid,
  FileSearch,
  BarChart3,
  ShieldCheck,
  Search,
  Sparkles,
  Moon,
  Sun,
} from 'lucide-react';
import { useTheme } from '@/app/context/ThemeContext';
import { useTender } from '@/app/context/TenderContext';

const navItems = [
  { href: '/upload', label: 'Command Center', icon: LayoutGrid },
  { href: '/dashboard', label: 'Tender Analysis', icon: FileSearch },
  { href: '/chat', label: 'Market Insights', icon: BarChart3 },
  { href: '/dashboard?view=compliance', label: 'Compliance Log', icon: ShieldCheck },
];

export function LayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const { filters, setFilters } = useTender();
  const [searchValue, setSearchValue] = useState('');

  useEffect(() => {
    if (pathname === '/dashboard') {
      setSearchValue(filters.searchQuery);
    }
  }, [filters.searchQuery, pathname]);

  const handleSearchChange = (value: string) => {
    setSearchValue(value);
    if (pathname === '/dashboard') {
      setFilters({ searchQuery: value });
    }
  };

  const isActive = (href: string) => pathname === href;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="md:grid md:grid-cols-[280px_1fr]">
        {/* Sidebar */}
        <aside className="hidden md:flex flex-col justify-between border-r border-sidebar-border bg-sidebar text-sidebar-foreground min-h-screen">
          <div>
            <div className="px-6 py-6 flex items-center gap-3">
              <div className="h-12 w-12 rounded-2xl bg-sidebar-accent flex items-center justify-center shadow-lg">
                <Image src="/meghaai.png" alt="MeghaAI" width={36} height={36} className="object-contain" />
              </div>
              <div>
                <p className="text-lg font-display font-semibold">MeghaAI</p>
                <p className="text-xs text-sidebar-foreground/70">Tender Intelligence</p>
              </div>
            </div>

            <nav className="px-4 space-y-2">
              {navItems.map(item => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                      active
                        ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-md'
                        : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-foreground'
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="px-6 pb-6 space-y-4">
            <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-sidebar-accent">
              <div>
                <p className="text-sm font-semibold">John Doe</p>
                <p className="text-xs text-sidebar-foreground/70">Senior Bid Manager</p>
              </div>
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg bg-sidebar-primary/20 hover:bg-sidebar-primary/30 transition-colors"
                aria-label="Toggle theme"
              >
                {theme === 'light' ? (
                  <Moon className="w-4 h-4 text-sidebar-foreground" />
                ) : (
                  <Sun className="w-4 h-4 text-sidebar-foreground" />
                )}
              </button>
            </div>
          </div>
        </aside>

        {/* Main Area */}
        <div className="flex flex-col min-h-screen">
          {/* Top Bar */}
          <div className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
            <div className="px-4 sm:px-6 py-4 flex flex-wrap items-center gap-4 justify-between">
              <div className="flex items-center gap-3 md:hidden">
                <div className="h-10 w-10 rounded-2xl bg-muted flex items-center justify-center">
                  <Image src="/meghaai.png" alt="MeghaAI" width={28} height={28} className="object-contain" />
                </div>
                <div>
                  <p className="text-base font-display font-semibold">MeghaAI</p>
                  <p className="text-xs text-muted-foreground">Tender Intelligence</p>
                </div>
              </div>

              <div className="flex-1 min-w-[220px] max-w-xl relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  value={searchValue}
                  onChange={e => handleSearchChange(e.target.value)}
                  placeholder="Search tenders, documents..."
                  className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-border bg-card focus:outline-none focus:ring-2 focus:ring-primary/40"
                />
              </div>

              <div className="flex items-center gap-3">
                <Link
                  href="/upload"
                  className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary text-primary-foreground font-semibold shadow-md hover:shadow-lg transition"
                >
                  <Sparkles className="w-4 h-4" />
                  Ingest Tender
                </Link>
                <button
                  onClick={toggleTheme}
                  className="md:hidden p-2 rounded-lg border border-border bg-card"
                  aria-label="Toggle theme"
                >
                  {theme === 'light' ? (
                    <Moon className="w-4 h-4 text-muted-foreground" />
                  ) : (
                    <Sun className="w-4 h-4 text-muted-foreground" />
                  )}
                </button>
              </div>
            </div>

            {/* Mobile Nav */}
            <div className="md:hidden px-4 pb-4 flex gap-2 overflow-x-auto">
              {navItems.map(item => {
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    className={`px-3 py-2 rounded-lg text-xs font-semibold whitespace-nowrap ${
                      active ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>

          <main className="flex-1 px-4 sm:px-6 lg:px-10 py-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
