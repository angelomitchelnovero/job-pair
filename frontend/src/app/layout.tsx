import "./globals.css";
import type { Metadata } from "next";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "JobPair.aloe — AI Resume ↔ Job Matching",
  description:
    "Upload a resume, paste a job description, and see explainable match scores from both a scikit-learn baseline and a PyTorch neural matcher.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">
        <Navbar />
        <main className="mx-auto max-w-6xl px-4 sm:px-6 py-8">{children}</main>
        <footer className="border-t border-gray-200 py-6 mt-16">
          <div className="mx-auto max-w-6xl px-6 text-sm text-gray-500 flex flex-col sm:flex-row justify-between gap-2">
            <span>
              JobPair.aloe · Built with FastAPI, scikit-learn, PyTorch, Next.js.
            </span>
            <span>Portfolio project — synthetic training data with real ML.</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
