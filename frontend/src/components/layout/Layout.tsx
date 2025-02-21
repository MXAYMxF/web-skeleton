'use client';

import { Toaster } from 'react-hot-toast';
import Navbar from './Navbar';
import Footer from './Footer';

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 flex-grow">
        {children}
      </main>
      <Footer />
      <Toaster position="top-right" />
    </div>
  );
}
