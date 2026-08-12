import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { TypebotBubble } from "@/components/TypebotBubble";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "4SEO | SEO para e-commerce com Inteligência Artificial",
  description:
    "Otimize produtos, supere concorrentes e alcance o topo das buscas. Plataforma de SEO para e-commerce desenvolvida pela 4Scale.",
  keywords: [
    "SEO",
    "e-commerce",
    "inteligência artificial",
    "4SEO",
    "4Scale",
    "otimização de produtos",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="pt-BR"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-black font-sans text-white antialiased">
        {children}
        <TypebotBubble />
      </body>
    </html>
  );
}
