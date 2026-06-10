import type { Metadata } from "next";
import "./globals.css";
import { Geist, Geist_Mono } from "next/font/google";
import { RootProvider } from "fumadocs-ui/provider/next";
import { MotionProvider } from "@/components/aceternity/motion-provider";
import { cn } from "@/lib/utils";
import { SITE_NAME, SITE_URL } from "@/lib/site";

const geistSans = Geist({ subsets: ["latin"], variable: "--font-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "ArxivDigest",
  description: "Autonomous daily AI digest of arxiv papers",
  metadataBase: new URL(SITE_URL),
  alternates: {
    types: {
      "application/rss+xml": [{ url: "/feed.xml", title: `${SITE_NAME} — RSS` }],
    },
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={cn("font-sans", geistSans.variable, geistMono.variable)}
      suppressHydrationWarning
    >
      <body className="flex min-h-screen flex-col">
        <MotionProvider>
          <RootProvider>{children}</RootProvider>
        </MotionProvider>
      </body>
    </html>
  );
}
