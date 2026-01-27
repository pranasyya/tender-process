'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/app/context/ThemeContext';

export function Header() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();

  const isActive = (path: string) => pathname === path;

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-cyan-500 flex items-center justify-center shadow-lg">
            <span className="text-primary-foreground font-bold text-lg">M</span>
          </div>
          <div className="flex flex-col hidden sm:block">
            <h1 className="text-lg font-bold text-foreground">Megha AI</h1>
            <p className="text-xs text-muted-foreground">Tender Discovery</p>
          </div>
        </div>

        <nav className="hidden md:flex items-center gap-8">
          <Link
            href="/upload"
            className={`text-sm font-medium transition-colors duration-200 pb-2 border-b-2 ${
              isActive('/upload')
                ? 'text-primary border-primary'
                : 'text-muted-foreground border-transparent hover:text-foreground'
            }`}
          >
            Upload
          </Link>
          <Link
            href="/dashboard"
            className={`text-sm font-medium transition-colors duration-200 pb-2 border-b-2 ${
              isActive('/dashboard')
                ? 'text-primary border-primary'
                : 'text-muted-foreground border-transparent hover:text-foreground'
            }`}
          >
            Dashboard
          </Link>
          <Link
            href="/chat"
            className={`text-sm font-medium transition-colors duration-200 pb-2 border-b-2 ${
              isActive('/chat')
                ? 'text-primary border-primary'
                : 'text-muted-foreground border-transparent hover:text-foreground'
            }`}
          >
            Chat
          </Link>
        </nav>

        <button
          onClick={toggleTheme}
          className="p-2 hover:bg-muted rounded-lg transition-colors duration-200 flex-shrink-0"
          aria-label="Toggle theme"
        >
          {theme === 'light' ? (
            <Moon className="w-5 h-5 text-muted-foreground hover:text-foreground transition-colors" />
          ) : (
            <Sun className="w-5 h-5 text-muted-foreground hover:text-foreground transition-colors" />
          )}
        </button>
      </div>

      <nav className="md:hidden px-4 py-2 border-t border-border flex gap-4 overflow-x-auto">
        <Link
          href="/upload"
          className={`text-xs font-medium transition-colors px-3 py-2 rounded-lg whitespace-nowrap ${
            isActive('/upload')
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted'
          }`}
        >
          Upload
        </Link>
        <Link
          href="/dashboard"
          className={`text-xs font-medium transition-colors px-3 py-2 rounded-lg whitespace-nowrap ${
            isActive('/dashboard')
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted'
          }`}
        >
          Dashboard
        </Link>
        <Link
          href="/chat"
          className={`text-xs font-medium transition-colors px-3 py-2 rounded-lg whitespace-nowrap ${
            isActive('/chat')
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-muted'
          }`}
        >
          Chat
        </Link>
      </nav>
    </header>
  );
}

export default Header;
