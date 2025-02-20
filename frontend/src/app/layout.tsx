import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import Layout from "@/components/layout/Layout";

const geist = Geist({
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Web Skeleton",
  description: "A modern web application skeleton",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={geist.className}>
      <body>
        <Layout>{children}</Layout>
      </body>
    </html>
  );
}
