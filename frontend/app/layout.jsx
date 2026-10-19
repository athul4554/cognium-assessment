import { IBM_Plex_Mono, Manrope } from "next/font/google";
import { cn } from "@/lib/utils";
import { Providers } from "./providers";
import "./globals.css";

const manrope = Manrope({ subsets: ["latin"], variable: "--font-sans" });
const plexMono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-plex-mono" });

export const metadata = { title: "Cognium" };

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={cn("font-sans antialiased", manrope.variable, plexMono.variable)}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
