'use client';

import Link from 'next/link';
import '@/app/fonts.css';
import ApiStatus from './ApiStatus';

// Backend root URL (from .env). FastAPI serves /docs and /redoc at the root —
// not under /api — so these must be absolute links to the backend, not proxied.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

export default function Footer() {
  return (
    <footer className="mt-auto py-4 bg-gray-50">
      <div className="container mx-auto px-4">
        <div className="flex flex-col sm:flex-row justify-between items-center text-sm text-gray-600">
          <div className="flex items-center space-x-1">
            <span>Made by Coffee Man Labs</span>
            <span 
              role="img" 
              aria-label="coffee" 
              className="text-lg"
              style={{ fontFamily: '"Noto Emoji", sans-serif' }}
            >
              ☕
            </span>
          </div>
          <div className="flex items-center space-x-4 mt-2 sm:mt-0">
            <Link href="/privacy" className="hover:text-indigo-600 transition-colors">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-indigo-600 transition-colors">
              Terms
            </Link>
            <Link href="/support" className="hover:text-indigo-600 transition-colors">
              Support
            </Link>
            <a
              href="https://github.com/MXAYMxF/web-skeleton"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-indigo-600 transition-colors"
            >
              GitHub
            </a>
            <a
              href={`${API_URL}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-indigo-600 transition-colors"
            >
              API Docs
            </a>
            <a
              href={`${API_URL}/redoc`}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-indigo-600 transition-colors"
            >
              ReDoc
            </a>
            <ApiStatus />
          </div>
        </div>
      </div>
    </footer>
  );
}
